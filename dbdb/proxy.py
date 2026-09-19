import argparse
import asyncio
import logging
from dbdb.hasher import ConsistentHashRing

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [DBDB-Proxy] %(message)s")
logger = logging.getLogger("DBDB-Proxy")


class ShardingProxy:
    def __init__(self, host: str, port: int, shard_endpoints: list):
        self.host = host
        self.port = port
        self.shard_endpoints = shard_endpoints
        self.ring = ConsistentHashRing(nodes=shard_endpoints)

    async def forward_command(self, node: tuple, raw_command: str) -> str:
        """Forwards command to the designated shard node and reads response."""
        node_host, node_port = node
        reader, writer = await asyncio.open_connection(node_host, node_port)
        try:
            writer.write((raw_command.strip() + "\n").encode())
            await writer.drain()
            data = await reader.readline()
            return data.decode().strip()
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        logger.info(f"Client connected to Proxy: {addr}")

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                raw_command = data.decode().strip()
                if not raw_command:
                    continue

                parts = raw_command.split(" ", 2)
                verb = parts[0].upper()

                if verb in ("GET", "SET", "DEL") and len(parts) >= 2:
                    key = parts[1]
                    target_node = self.ring.get_node(key)
                    response = await self.forward_command(target_node, raw_command)
                elif verb == "PING":
                    response = "PONG"
                elif verb == "COMPACT":
                    # Broadcast compact to all shards
                    tasks = [self.forward_command(node, "COMPACT") for node in self.shard_endpoints]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    response = "OK" if all(r == "OK" for r in results) else "ERROR_DURING_COMPACT"
                else:
                    response = "ERROR INVALID_OR_UNSUPPORTED_PROXY_COMMAND"

                writer.write((response + "\n").encode())
                await writer.drain()

        except Exception as e:
            logger.error(f"Error handling proxy client {addr}: {e}")
        finally:
            logger.info(f"Client disconnected from Proxy: {addr}")
            writer.close()
            await writer.wait_closed()

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(f"DBDB Sharding Proxy listening on {self.host}:{self.port}")
        logger.info(f"Managed Shards: {self.shard_endpoints}")
        async with server:
            await server.serve_forever()


def run_proxy():
    parser = argparse.ArgumentParser(description="DBDB Sharding Proxy")
    parser.add_argument("--host", default="0.0.0.0", help="Proxy listen host")
    parser.add_argument("--port", type=int, default=9000, help="Proxy listen port")
    parser.add_argument(
        "--shards",
        nargs="+",
        required=True,
        help="List of shard host:port pairs (e.g. 127.0.0.1:8881 127.0.0.1:8882)",
    )
    args = parser.parse_args()

    endpoints = []
    for s in args.shards:
        h, p = s.split(":")
        endpoints.append((h, int(p)))

    proxy = ShardingProxy(args.host, args.port, endpoints)
    asyncio.run(proxy.start())


if __name__ == "__main__":
    run_proxy()