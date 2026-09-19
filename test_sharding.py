import asyncio
from dbdb.client import DBDBClient


async def test_cluster_sharding():
    print("🚀 Running DBDB Consistent Hashing Shard Test...\n")

    proxy_client = DBDBClient(host="127.0.0.1", port=9000)
    await proxy_client.connect()

    shard_clients = {
        8881: DBDBClient(host="127.0.0.1", port=8881),
        8882: DBDBClient(host="127.0.0.1", port=8882),
        8883: DBDBClient(host="127.0.0.1", port=8883),
    }
    for client in shard_clients.values():
        await client.connect()

    try:
        total_keys = 60
        print(f"📦 Writing {total_keys} keys through Proxy on port 9000...")
        for i in range(total_keys):
            key = f"user_{i}"
            val = f"payload_{i}"
            await proxy_client.set(key, val)

        print("🔍 Verifying that data was routed and distributed among shards...")
        shard_counts = {8881: 0, 8882: 0, 8883: 0}

        for i in range(total_keys):
            key = f"user_{i}"
            expected_val = f"payload_{i}"

            # Verify proxy retrieval
            assert await proxy_client.get(key) == expected_val

            # Find which physical shard actually holds this key
            for port, client in shard_clients.items():
                try:
                    if await client.get(key) == expected_val:
                        shard_counts[port] += 1
                        break
                except KeyError:
                    continue

        print("\n📊 Key Distribution Across Physical Shards:")
        for port, count in shard_counts.items():
            print(f"  - Shard :{port} holds {count} keys ({count/total_keys*100:.1f}%)")

        assert all(count > 0 for count in shard_counts.values()), "A shard received zero keys! Ring unbalanced."
        print("\n✅ Perfect! Consistent Hashing successfully distributed keys horizontally across all shards.")

    finally:
        await proxy_client.close()
        for client in shard_clients.values():
            await client.close()


if __name__ == "__main__":
    asyncio.run(test_cluster_sharding())