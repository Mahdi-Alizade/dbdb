import asyncio
from dbdb.client import DBDBClient


async def test_cluster_replication():
    print("🚀 Starting DBDB Multi-Node Replication Test...\n")

    primary = DBDBClient(host="127.0.0.1", port=8888)
    replica1 = DBDBClient(host="127.0.0.1", port=8889)
    replica2 = DBDBClient(host="127.0.0.1", port=8890)

    await primary.connect()
    await replica1.connect()
    await replica2.connect()

    try:
        # 1. Verify Node Roles
        assert await primary.role() == "PRIMARY", "Node 8888 is not PRIMARY"
        assert await replica1.role() == "REPLICA", "Node 8889 is not REPLICA"
        assert await replica2.role() == "REPLICA", "Node 8890 is not REPLICA"
        print("✅ Cluster roles verified: 1 Primary, 2 Replicas.")

        # 2. Write key to Primary
        print("✍️  Writing 'cluster_state=synchronized' to Primary (port 8888)...")
        await primary.set("cluster_state", "synchronized")

        # Allow network propagation window
        await asyncio.sleep(0.5)

        # 3. Read key from Replica 1 and Replica 2
        val1 = await replica1.get("cluster_state")
        val2 = await replica2.get("cluster_state")
        print(f"📖 Read from Replica-1 (8889): {val1}")
        print(f"📖 Read from Replica-2 (8890): {val2}")

        assert val1 == "synchronized", "Replica-1 did not receive the replicated write!"
        assert val2 == "synchronized", "Replica-2 did not receive the replicated write!"
        print("✅ Replication validated: All followers synced with Primary.")

        # 4. Verify Replica Read-Only enforcement
        print("🛡️  Verifying Replica rejection on mutation...")
        try:
            await replica1.set("illegal_key", "fail")
            print("❌ Failure: Replica accepted a write operation!")
        except RuntimeError as err:
            assert "READONLY_REPLICA_CANNOT_WRITE" in str(err)
            print("✅ Replica correctly rejected write (READONLY_REPLICA_CANNOT_WRITE).")

    finally:
        await primary.close()
        await replica1.close()
        await replica2.close()
        print("\n🎉 Multi-node replication cluster test passed successfully!")


if __name__ == "__main__":
    asyncio.run(test_cluster_replication())