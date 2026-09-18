# DBDB: Dog Bed Database (Advanced Edition)

A production-grade, persistent, append-only key-value storage engine built in Python. 

Originally inspired by the foundational architecture in *500 Lines or Less*, this project has been extensively engineered into a standalone, network-accessible, and containerized database service. It serves as a comprehensive implementation of low-level database concepts including storage engines, buffer pools, and concurrency control.

---

## 🚀 Key Architectural Features

*   **Append-Only Disk I/O:** Data is never overwritten in place. This ensures crash resilience, preventing database corruption even during abrupt power failures.
*   **Immutable Binary Search Tree:** Updates utilize strict copy-on-write semantics. Only the path from the modified node up to the root is written to disk, securely sharing untouched subtrees with historical states.
*   **Buffer Pool (LRU Cache):** An integrated Least Recently Used (LRU) memory cache intercepts disk reads, serving frequently accessed tree nodes and values directly from RAM to maximize throughput.
*   **Atomic Compaction (Vacuuming):** A seamless `compact()` mechanism traverses the live tree and rewrites only active data to a new file, atomically replacing the bloated file to reclaim disk space without corrupting the database lock.
*   **Asynchronous TCP Server:** A custom network layer built on `asyncio` handles multiple concurrent client connections. Disk I/O operations are offloaded to thread pools (`asyncio.to_thread`) with strict locking to prevent event-loop blocking.
*   **Multi-Stage Docker Deployment:** Containerized for production using a minimal `python:3.13-slim` image, executing under a secure non-root user with persistent volume mapping.

---

## 🏗️ System Architecture

```text
+-------------------------------------------------------------+
|                     Async TCP Clients                       |
+-------------------------------------------------------------+
                              | (TCP / 8888)
+-------------------------------------------------------------+
| 1. Network Layer (asyncio Server)                           |
|    - Command Parsing (GET, SET, DEL, COMPACT, PING)         |
|    - Thread-safe I/O dispatching                            |
+-------------------------------------------------------------+
| 2. Interface Layer (DBDB API)                               |
|    - Dictionary protocol (__getitem__, __setitem__, __iter__)|
+-------------------------------------------------------------+
| 3. Logical Layer (ValueRef / BinaryNodeRef)                 |
|    - Lazy serialization, pointer resolution, iteration      |
+-------------------------------------------------------------+
| 4. Binary Tree Layer (Immutable BST)                        |
|    - Copy-on-write path replacement, in-order traversal     |
+-------------------------------------------------------------+
| 5. Physical Storage Layer (Append-Only File + LRU Cache)    |
|    - In-memory Buffer Pool                                  |
|    - Append-only disk writes, Superblock, OS file locking   |
+-------------------------------------------------------------+
🐳 Docker Deployment (Recommended)
The easiest way to run the DBDB network server is via Docker Compose. This ensures the database runs in an isolated environment while persisting your data.

Bash
# Start the server in detached mode
docker compose up -d --build

# View server logs
docker compose logs -f

# Shut down the server (data remains safe in the volume)
docker compose down
💻 Local Installation
If you prefer to run it locally without Docker:

Bash
git clone [https://github.com/](https://github.com/)<your-username>/dbdb.git
cd dbdb
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
🛠️ Usage Guide
1. Connecting via Async TCP Client
You can interact with the running server (Docker or local) using the provided asynchronous client.

Python
import asyncio
from dbdb.client import DBDBClient

async def main():
    client = DBDBClient(host="127.0.0.1", port=8888)
    await client.connect()

    # Set and Get values
    await client.set("architecture", "append-only")
    value = await client.get("architecture")
    print(value)  # Output: append-only

    # Reclaim disk space over the network
    await client.compact()
    
    await client.close()

asyncio.run(main())
2. Embedded Python Library
Use DBDB directly inside your Python applications as a persistent dictionary.

Python
from dbdb import connect

# Connect with a custom LRU cache capacity
db = connect("local.db", cache_capacity=512)

db["system"] = "distributed"
db.commit()

# Iterate through sorted keys (In-Order Traversal)
for key, value in db.items():
    print(f"{key} -> {value}")

db.close()
3. Command Line Interface (CLI)
Interact with local database files directly from the terminal.

Bash
python -m dbdb.tool local.db set host "127.0.0.1"
python -m dbdb.tool local.db get host
python -m dbdb.tool local.db delete host
🧪 Testing
The project includes a comprehensive test suite covering edge cases, I/O locks, caching eviction policies, and network integration.

Bash
# Run unit and integration tests
pytest -v

# Run the network integration test against the live server
python test_network.py
📜 License
This project is open-source and available under the MIT License.