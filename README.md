# DBDB: Dog Bed Database (Distributed Sharded Edition)

A production-grade, distributed, append-only key-value storage engine written in Python.

Originally conceptualized from the core principles in *500 Lines or Less*, this project has evolved into a horizontally partitioned, containerized, and high-performance distributed database. It incorporates low-level disk append semantics, an in-memory buffer pool, copy-on-write trees, a primary-replica streaming protocol, and a consistent hashing reverse proxy.

---

## 🚀 Key Architectural Features

*   **Append-Only Storage Engine:** Data is never updated in place. Every write appends new bytes to the end of the file, guaranteeing atomicity and crash tolerance without data file corruption.
*   **Immutable Copy-on-Write BST:** Key indexing uses an immutable Binary Search Tree. Modifications spawn a new path from leaf to root while safely sharing untouched subtrees with historical snapshots.
*   **Buffer Pool (LRU Cache):** Integrated Least Recently Used (LRU) memory cache intercepts disk reads, serving frequently referenced nodes and values directly from RAM.
*   **Atomic Vacuuming (Compaction):** The `compact()` operation walks live nodes from the root, writes an unfragmented data file, and atomically hot-swaps the underlying file descriptors without deadlocks.
*   **Consistent Hashing Sharding Proxy:** Transparent network router using virtual nodes ($V=100$) over an MD5 hash ring, achieving uniform key distribution ($O(\log N)$ binary search routing) across independent physical shard instances.
*   **Primary-Replica Asynchronous Sync:** Native TCP replication streaming that broadcasts write operations (`SET`, `DEL`, `COMPACT`) from primaries to read-only replica instances.
*   **Multi-Stage Docker & Compose Orchestration:** Fully containerized setup executing under non-root permissions with named volumes for decoupled data persistence.

---

## 🏗️ Distributed Architecture & Topology

```text
                           +------------------------+
                           |     TCP Client(s)      |
                           +------------------------+
                                       |
                                       | Port 9000
                                       v
                    +--------------------------------------+
                    |         DBDB Sharding Proxy          |
                    |  - MD5 Consistent Hash Ring          |
                    |  - Virtual Nodes (V=100 per shard)   |
                    |  - Transparent TCP Request Routing   |
                    +--------------------------------------+
                         /             |             \
       Hash Range [0..A] /  Hash Range | [A..B]       \ Hash Range [B..2^32-1]
                        v              v               v
               +---------------+ +---------------+ +---------------+
               | dbdb-shard-1  | | dbdb-shard-2  | | dbdb-shard-3  |
               |  (Port 8881)  | |  (Port 8882)  | |  (Port 8883)  |
               +---------------+ +---------------+ +---------------+
               | Physical File | | Physical File | | Physical File |
               | + LRU Cache   | | + LRU Cache   | | + LRU Cache   |
               +---------------+ +---------------+ +---------------+
Storage Node Internal Hierarchy
Plaintext
+-------------------------------------------------------------+
| 1. Async Network Dispatcher (asyncio TCP Server)            |
+-------------------------------------------------------------+
| 2. DBDB Public Interface (Dict Protocol / Atomic Commit)    |
+-------------------------------------------------------------+
| 3. Logical Reference Engine (ValueRef & BinaryNodeRef)      |
+-------------------------------------------------------------+
| 4. Immutable Tree Layer (Path Copying & In-Order Traversal) |
+-------------------------------------------------------------+
| 5. Physical Storage & Buffer Pool (LRU Cache + Superblock)  |
+-------------------------------------------------------------+
🐳 Docker Deployment & Sharded Cluster
The default docker-compose.yml provisions a distributed setup consisting of 3 isolated shard instances and 1 central sharding proxy.

Bash
# Build images and boot the 4-node cluster in background
docker compose up -d --build

# Monitor live routing and query dispatch logs across all nodes
docker compose logs -f

# Inspect proxy routing decisions specifically
docker logs -f dbdb-proxy

# Tear down cluster and remove persistent volumes
docker compose down -v
💻 Local Development Setup
If running directly on the host machine without containerization:

PowerShell
# Clone and setup environment
git clone [https://github.com/](https://github.com/)<your-username>/dbdb.git
cd dbdb
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
🛠️ Usage Examples
1. Interacting via Sharding Proxy
Connect your application to the proxy port (9000). Keys are hashed and dispatched automatically to the designated physical shard.

Python
import asyncio
from dbdb.client import DBDBClient

async def main():
    # Connect directly to the Proxy router
    client = DBDBClient(host="127.0.0.1", port=9000)
    await client.connect()

    # Data is hashed and partitioned across shards
    await client.set("user:1001", "{'name': 'Mahdi', 'role': 'Admin'}")
    await client.set("user:1002", "{'name': 'Alex', 'role': 'Engineer'}")

    val = await client.get("user:1001")
    print(f"Retrieved: {val}")

    # Broadcasts vacuuming across all managed shards
    await client.compact()

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
2. Standalone Embedded Library
Use the database engine directly within local Python applications without running any network servers:

Python
from dbdb import connect

# Open database with custom LRU cache capacity
db = connect("analytics.db", cache_capacity=1024)

db["session_a"] = "active"
db["session_b"] = "idle"
db.commit()

# Sorted key retrieval via In-Order Tree Traversal
for key, value in db.items():
    print(f"{key} => {value}")

# Trigger garbage cleanup
db.compact()
db.close()
🧪 Test Suite Execution
The repository provides unit tests, disk compaction verifications, and multi-node cluster benchmarks:

PowerShell
# Run all unit tests (Storage, BST, LRU Cache, Compaction)
pytest -v

# Validate horizontal sharding distribution across the live cluster
python test_sharding.py

# Validate primary-replica synchronization (when running replication topology)
python test_replication.py
📜 License
This project is open-source under the MIT License.