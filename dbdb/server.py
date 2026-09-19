import argparse
import asyncio
import logging
import threading
from dbdb.interface import connect

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("DBDB-Server")


class DBDBServer:
    def __init__(
        self,
        db_path: str,
        host: str = "0.0.0.0",
        port: int = 8888,
        role: str = "primary",
        master_host: str = None,
        master_port: int = None,
    ):
        self.db_path = db_path
        self.host = host
        self.port = port
        self.role = role.lower()
        self.master_host = master_host
        self.master_port = master_port

        self.db = connect(db_path)
        self.db_lock = threading.Lock()
        
        # Track connected replicas on the Primary
        self.replicas = set()
        self.replicas_lock = asyncio.Lock()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        logger.info(f"Client connected: {addr}")
        is_replica = False

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                message = data.decode().strip()
                if not message:
                    continue

                parts = message.split(" ", 2)
                command = parts[0].upper()

                # Handle Replica Handshake
                if command == "SYNC" and self.role == "primary":
                    async with self.replicas_lock:
                        self.replicas.add(writer)
                    is_replica = True
                    logger.info(f"Registered new replica from: {addr}")
                    writer.write(b"SYNC_ACK\n")
                    await writer.drain()
                    continue

                response = await self.process_command(command, parts)
                writer.write((response + "\n").encode())
                await writer.drain()

                # If a mutation command succeeded on Primary, replicate to followers
                if self.role == "primary" and response == "OK" and command in ("SET", "DEL", "COMPACT"):
                    await self._broadcast_to_replicas(message)

        except Exception as e:
            logger.error(f"Connection error with {addr}: {e}")
        finally:
            if is_replica:
                async with self.replicas_lock:
                    self.replicas.discard(writer)
                logger.info(f"Replica unregistered: {addr}")
            logger.info(f"Client disconnected: {addr}")
            writer.close()
            await writer.wait_closed()

    async def _broadcast_to_replicas(self, command_line: str):
        payload = (command_line.strip() + "\n").encode()
        async with self.replicas_lock:
            disconnected = []
            for replica_writer in self.replicas:
                try:
                    replica_writer.write(payload)
                    await replica_writer.drain()
                except Exception as ex:
                    logger.warning(f"Failed to propagate mutation to replica: {ex}")
                    disconnected.append(replica_writer)
            for bad_writer in disconnected:
                self.replicas.discard(bad_writer)

    async def process_command(self, command: str, parts: list) -> str:
        try:
            if command == "GET" and len(parts) == 2:
                key = parts[1]
                value = await asyncio.to_thread(self._db_get, key)
                return f"VALUE {value}"

            elif command == "SET" and len(parts) == 3:
                if self.role == "replica":
                    return "ERROR READONLY_REPLICA_CANNOT_WRITE"
                key, value = parts[1], parts[2]
                await asyncio.to_thread(self._db_set, key, value)
                return "OK"

            elif command == "DEL" and len(parts) == 2:
                if self.role == "replica":
                    return "ERROR READONLY_REPLICA_CANNOT_WRITE"
                key = parts[1]
                await asyncio.to_thread(self._db_del, key)
                return "OK"

            elif command == "COMPACT":
                if self.role == "replica":
                    return "ERROR READONLY_REPLICA_CANNOT_WRITE"
                await asyncio.to_thread(self._db_compact)
                return "OK"

            elif command == "ROLE":
                return f"ROLE {self.role.upper()}"

            elif command == "PING":
                return "PONG"

            else:
                return "ERROR INVALID_COMMAND_FORMAT"
        except KeyError:
            return "NOTFOUND"
        except Exception as e:
            return f"ERROR {str(e)}"

    def _db_get(self, key):
        with self.db_lock:
            return self.db[key]

    def _db_set(self, key, value):
        with self.db_lock:
            self.db[key] = value
            self.db.commit()

    def _db_del(self, key):
        with self.db_lock:
            del self.db[key]
            self.db.commit()

    def _db_compact(self):
        with self.db_lock:
            self.db.compact()

    async def _sync_from_master_loop(self):
        while True:
            logger.info(f"Replica connecting to Primary at {self.master_host}:{self.master_port}...")
            try:
                reader, writer = await asyncio.open_connection(self.master_host, self.master_port)
                writer.write(b"SYNC\n")
                await writer.drain()

                ack = await reader.readline()
                if ack.decode().strip() != "SYNC_ACK":
                    logger.error("Failed handshake with primary. Retrying in 3s...")
                    await asyncio.sleep(3)
                    continue

                logger.info("Replication sync stream established. Listening for updates...")
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    raw_cmd = line.decode().strip()
                    if not raw_cmd:
                        continue

                    parts = raw_cmd.split(" ", 2)
                    cmd = parts[0].upper()

                    if cmd == "SET" and len(parts) == 3:
                        await asyncio.to_thread(self._db_set, parts[1], parts[2])
                        logger.info(f"Replicated SET key: {parts[1]}")
                    elif cmd == "DEL" and len(parts) == 2:
                        await asyncio.to_thread(self._db_del, parts[1])
                        logger.info(f"Replicated DEL key: {parts[1]}")
                    elif cmd == "COMPACT":
                        await asyncio.to_thread(self._db_compact)
                        logger.info("Replicated COMPACT")

            except Exception as e:
                logger.warning(f"Replication connection dropped: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(f"DBDB Server ({self.role.upper()}) running on {self.host}:{self.port}")

        if self.role == "replica" and self.master_host and self.master_port:
            asyncio.create_task(self._sync_from_master_loop())

        async with server:
            await server.serve_forever()


def run_server():
    parser = argparse.ArgumentParser(description="DBDB Network Server")
    parser.add_argument("db_path", nargs="?", default="network.db", help="Path to database file")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--port", type=int, default=8888, help="Port to bind")
    parser.add_argument("--role", default="primary", choices=["primary", "replica"], help="Node replication role")
    parser.add_argument("--master-host", default=None, help="Primary host address (if role=replica)")
    parser.add_argument("--master-port", type=int, default=None, help="Primary port (if role=replica)")
    args = parser.parse_args()

    server = DBDBServer(
        db_path=args.db_path,
        host=args.host,
        port=args.port,
        role=args.role,
        master_host=args.master_host,
        master_port=args.master_port,
    )

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Shutting down database...")
        server.db.close()


if __name__ == "__main__":
    run_server()