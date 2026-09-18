import asyncio


class DBDBClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 8888):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def _send_command(self, command: str) -> str:
        if not self.writer:
            await self.connect()
        
        self.writer.write((command + "\n").encode())
        await self.writer.drain()
        
        data = await self.reader.readline()
        return data.decode().strip()

    async def get(self, key: str) -> str:
        response = await self._send_command(f"GET {key}")
        if response == "NOTFOUND":
            raise KeyError(key)
        if response.startswith("VALUE "):
            return response[6:]
        raise RuntimeError(f"Server error: {response}")

    async def set(self, key: str, value: str):
        response = await self._send_command(f"SET {key} {value}")
        if response != "OK":
            raise RuntimeError(f"Server error: {response}")

    async def delete(self, key: str):
        response = await self._send_command(f"DEL {key}")
        if response == "NOTFOUND":
            raise KeyError(key)
        if response != "OK":
            raise RuntimeError(f"Server error: {response}")

    async def compact(self):
        response = await self._send_command("COMPACT")
        if response != "OK":
            raise RuntimeError(f"Server error: {response}")

    async def ping(self):
        return await self._send_command("PING")


# Example interactive execution
async def main():
    client = DBDBClient()
    await client.connect()
    print("[*] Connected to DBDB Server")
    
    pong = await client.ping()
    print(f"[*] PING -> {pong}")
    
    await client.set("framework", "FastAPI")
    print("[*] SET framework FastAPI -> OK")
    
    val = await client.get("framework")
    print(f"[*] GET framework -> {val}")
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())