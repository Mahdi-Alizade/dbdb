import asyncio
from dbdb.client import DBDBClient


async def run_integration_test():
    print("🔌 Connecting to DBDB Docker container at 127.0.0.1:8888...")
    client = DBDBClient(host="127.0.0.1", port=8888)
    
    try:
        await client.connect()
        print("✅ Connected successfully!\n")

        # 1. PING test
        pong = await client.ping()
        print(f"📡 PING -> {pong}")

        # 2. SET test
        print("💾 Setting key 'docker_test' to 'containerized_value'...")
        await client.set("docker_test", "containerized_value")

        # 3. GET test
        val = await client.get("docker_test")
        print(f"📖 GET 'docker_test' -> {val}")
        assert val == "containerized_value", "Value mismatch!"

        # 4. COMPACT test
        print("🧹 Triggering database compaction over network...")
        await client.compact()
        print("✅ Compaction successful!")

        # 5. DELETE test
        print("🗑️ Deleting key 'docker_test'...")
        await client.delete("docker_test")

        # 6. Verify Deletion
        try:
            await client.get("docker_test")
            print("❌ Error: Key should have been deleted!")
        except KeyError:
            print("✅ Key successfully deleted (KeyError raised as expected).")

    except ConnectionRefusedError:
        print("❌ Error: Could not connect to server. Is the Docker container running?")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
    finally:
        print("\n🔌 Disconnecting from server...")
        await client.close()
        print("✅ Connection closed. Integration test complete!")


if __name__ == "__main__":
    asyncio.run(run_integration_test())