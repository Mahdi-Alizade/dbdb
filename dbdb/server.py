import asyncio
import logging
import threading
from dbdb.interface import connect

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class DBDBServer:
    def __init__(self, db_path: str, host: str = '127.0.0.1', port: int = 8888):
        self.db_path = db_path
        self.host = host
        self.port = port
        self.db = connect(db_path)
        self.db_lock = threading.Lock()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        logging.info(f"Client connected: {addr}")
        
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                
                message = data.decode().strip()
                if not message:
                    continue
                
                parts = message.split(' ', 2)
                command = parts[0].upper()

                response = await self.process_command(command, parts)
                writer.write((response + "\n").encode())
                await writer.drain()
        except Exception as e:
            logging.error(f"Error handling client {addr}: {e}")
        finally:
            logging.info(f"Client disconnected: {addr}")
            writer.close()
            await writer.wait_closed()

    async def process_command(self, command: str, parts: list) -> str:
        try:
            if command == "GET" and len(parts) == 2:
                key = parts[1]
                value = await asyncio.to_thread(self._db_get, key)
                return f"VALUE {value}"
            
            elif command == "SET" and len(parts) == 3:
                key, value = parts[1], parts[2]
                await asyncio.to_thread(self._db_set, key, value)
                return "OK"
                
            elif command == "DEL" and len(parts) == 2:
                key = parts[1]
                await asyncio.to_thread(self._db_del, key)
                return "OK"
                
            elif command == "COMPACT":
                await asyncio.to_thread(self._db_compact)
                return "OK"
                
            elif command == "PING":
                return "PONG"
                
            else:
                return "ERROR INVALID_COMMAND_FORMAT"
        except KeyError:
            return "NOTFOUND"
        except Exception as e:
            return f"ERROR {str(e)}"

    # Thread-safe synchronous wrappers for Disk I/O
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

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logging.info(f"DBDB Server listening on {self.host}:{self.port}")
        
        async with server:
            await server.serve_forever()


def run_server(db_path: str, host: str = '127.0.0.1', port: int = 8888):
    server = DBDBServer(db_path, host, port)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logging.info("Server shutting down.")
        server.db.close()


if __name__ == "__main__":
    import sys
    db_file = sys.argv[1] if len(sys.argv) > 1 else "network.db"
    run_server(db_file)