# Distributed File System with Fault Tolerance

A fully functional distributed file system built in pure Python that stores files across multiple nodes with automatic replication and fault tolerance.

---

## Architecture Overview

```
┌─────────────┐        TCP (port 9000)       ┌──────────────────────┐
│   Client    │ ◄──────────────────────────► │    Master Server     │
│ (upload /   │                              │  • Metadata store    │
│  download)  │                              │  • Upload/Download   │
└─────────────┘                              │    planning          │
                                             │  • Node registry     │
                                             │  • Replication mgr   │
                                             └──────┬───────────────┘
                                                    │ TCP + UDP heartbeat
                              ┌─────────────────────┼─────────────────────┐
                              ▼                     ▼                     ▼
                     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
                     │   Node 1     │    │   Node 2     │    │   Node 3     │
                     │  port 9100   │    │  port 9101   │    │  port 9102   │
                     │ /storage/    │    │ /storage/    │    │ /storage/    │
                     │  node1/      │    │  node2/      │    │  node3/      │
                     └──────────────┘    └──────────────┘    └──────────────┘
```

### Key Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **Master** | `master/master.py` | Central coordinator — handles all client requests, delegates to sub-managers |
| **MetadataManager** | `master/metadata_manager.py` | Persists file/chunk locations in JSON; thread-safe with atomic writes |
| **NodeManager** | `master/node_manager.py` | Tracks live nodes via heartbeat; detects failures with a watchdog thread |
| **ReplicationManager** | `master/replication_manager.py` | Monitors replica health; auto-heals under-replicated chunks |
| **Node** | `nodes/node.py` | TCP server that stores/serves/deletes chunk files; sends heartbeats |
| **Client** | `client/client.py` | CLI for upload, download, list, delete |
| **Chunking** | `common/chunking.py` | Splits files into 1 MB chunks; reassembles in order |
| **Hashing** | `common/hashing.py` | SHA-256 integrity checks for every chunk and whole-file verification |

---

## Fault Tolerance Mechanisms

### 1. Replication (RF = 3)
Every chunk is stored on **3 independent nodes**. A client download succeeds as long as at least 1 replica is alive.

### 2. Heartbeat-Based Failure Detection
- Nodes send a heartbeat every **5 seconds** (TCP + UDP).
- The master's watchdog marks a node **DEAD** after **15 seconds** of silence.
- An `on_failure` callback immediately triggers re-replication.

### 3. Automatic Re-Replication
When a node dies:
1. The `ReplicationManager` removes the dead node from all chunk metadata.
2. For each under-replicated chunk, it fetches a copy from a surviving replica.
3. It pushes the chunk to a new healthy node.
4. Metadata is updated atomically.

### 4. SHA-256 Integrity Checks
- Each chunk has a SHA-256 hash computed before upload.
- On store: the node verifies the received data matches the hash before writing.
- On download: the client re-verifies each chunk and the final reassembled file.
- Corrupted chunks are detected immediately and an error is raised.

### 5. Atomic Metadata Persistence
- Metadata is written via write-to-temp + atomic rename, preventing corruption on crash.

### 6. Periodic Health Audits
- Every 30 seconds the `ReplicationManager` scans all chunks and repairs any that are under-replicated (handles silent data loss / disk failures).

---

## Quick Start

### Prerequisites
- Python 3.10 or higher
- No third-party packages required for core functionality

```bash
pip install -r requirements.txt   # optional extras (colorama, tqdm)
```

### Start the System

**Linux / macOS:**
```bash
bash run.sh
```

**Windows:**
```bat
run.bat
```

This starts the master on port 9000 and nodes on ports 9100–9102.

### Stop the System
```bash
bash run.sh stop      # Linux/macOS
run.bat stop          # Windows
```

---

## Client Usage

All commands are run from the **project root** directory.

### Upload a file
```bash
python3 -m client.client upload test_files/sample1.txt
```

### Download a file
```bash
python3 -m client.client download sample1.txt
# Saved to: downloads/sample1.txt
```

### List stored files
```bash
python3 -m client.client list
```

Output:
```
Filename                                 Chunks  Hash (prefix)
-----------------------------------------------------------------
sample1.txt                                   1  a3f9d2e81c04
sample2.jpg                                   1  7b2c4f90e1d3
```

### Delete a file
```bash
python3 -m client.client delete sample1.txt
```

---

## Manual Start (for development / debugging)

Open 4 separate terminals from the project root:

```bash
# Terminal 1 — Master
python3 -m master.master

# Terminal 2 — Node 1
NODE_ID=1 python3 -m nodes.node

# Terminal 3 — Node 2
NODE_ID=2 python3 -m nodes.node

# Terminal 4 — Node 3
NODE_ID=3 python3 -m nodes.node
```

---

## Simulating a Node Failure

1. Start the full system.
2. Upload a file:  `python3 -m client.client upload test_files/sample1.txt`
3. Kill Node 2 (Ctrl-C in its terminal, or `kill <pid>`).
4. Wait ~15 seconds for the master to detect the failure.
5. The master log (`logs/master.log`) will show re-replication activity.
6. Download still succeeds:  `python3 -m client.client download sample1.txt`

---

## Project Structure

```
DFS_Project/
├── client/
│   ├── client.py          CLI: upload / download / list / delete
│   ├── client_utils.py    prepare_upload(), assemble_download()
│   └── config.py          MASTER_HOST, MASTER_PORT, DOWNLOAD_DIR
│
├── master/
│   ├── master.py          TCP server + request dispatcher
│   ├── metadata_manager.py  Thread-safe JSON metadata store
│   ├── node_manager.py    Heartbeat registry + watchdog thread
│   └── replication_manager.py  Auto-heal under-replicated chunks
│
├── nodes/
│   ├── node.py            Shared storage node logic
│   ├── node1/node.py      NODE_ID=1 launcher
│   ├── node2/node.py      NODE_ID=2 launcher
│   ├── node3/node.py      NODE_ID=3 launcher
│   └── storage/           Chunk files (auto-created)
│
├── common/
│   ├── constants.py       CHUNK_SIZE, REPLICATION_FACTOR, ports, timeouts
│   ├── chunking.py        split_file(), merge_chunks()
│   ├── hashing.py         hash_bytes(), verify_chunk(), verify_file()
│   └── utils.py           TCP framing, logging, JSON helpers
│
├── logs/                  Per-component log files
├── test_files/            Sample upload targets
├── downloads/             Client download destination (auto-created)
├── README.md
├── requirements.txt
├── run.sh
└── run.bat
```

---

## Configuration

Edit `common/constants.py` to tune:

| Constant | Default | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | 1 MB | Size of each file chunk |
| `REPLICATION_FACTOR` | 3 | Number of node replicas per chunk |
| `HEARTBEAT_INTERVAL` | 5 s | How often nodes ping the master |
| `NODE_TIMEOUT` | 15 s | Silence before a node is marked dead |
| `REPLICATION_CHECK_INTERVAL` | 30 s | Periodic audit frequency |

Edit `client/config.py` to change the master address for remote deployments.

---

## Protocol (TCP Message Framing)

All messages use a **4-byte big-endian length prefix + UTF-8 JSON payload**.  
Chunk data uses the same framing but carries raw bytes instead of JSON.

```
┌────────────┬──────────────────────────────┐
│  4 bytes   │  N bytes                     │
│  (length)  │  (JSON or binary payload)    │
└────────────┴──────────────────────────────┘
```

### Message Types

| Action | Direction | Description |
|--------|-----------|-------------|
| `UPLOAD_PLAN` | Client → Master | Request node assignments for new upload |
| `UPLOAD_COMPLETE` | Client → Master | Signal all chunks are transferred |
| `DOWNLOAD_PLAN` | Client → Master | Request chunk locations for a file |
| `LIST_FILES` | Client → Master | Get all stored filenames |
| `DELETE_FILE` | Client → Master | Remove file from all nodes |
| `STORE_CHUNK` | Client/Master → Node | Write a chunk to disk |
| `FETCH_CHUNK` | Client/Master → Node | Read a chunk from disk |
| `DELETE_CHUNK` | Master → Node | Remove a chunk from disk |
| `HEARTBEAT` | Node → Master | Liveness signal (TCP + UDP) |

---

## OS Concepts Demonstrated

- **Distributed Systems**: Separation of master (coordinator) and storage nodes
- **Fault Tolerance**: Replication, failure detection, automatic recovery
- **Concurrency**: Each connection handled in a dedicated thread; RLock for shared state
- **IPC / Networking**: TCP sockets with custom framing protocol; UDP heartbeats
- **Data Integrity**: SHA-256 checksums at chunk and file level
- **Persistence**: Atomic JSON metadata store survives master restarts
- **File I/O**: Binary chunking, streaming reads, atomic file writes
