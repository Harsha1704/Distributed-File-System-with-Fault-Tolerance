# ============================================================
# constants.py — Global constants for the DFS
# ============================================================

# Chunk / replication settings
CHUNK_SIZE        = 1 * 1024 * 1024   # 1 MB per chunk
REPLICATION_FACTOR = 3                 # Each chunk stored on 3 nodes

# Network ports
MASTER_PORT       = 9000
NODE_BASE_PORT    = 9100               # node1=9100, node2=9101, node3=9102

# Heartbeat / fault-tolerance timings (seconds)
HEARTBEAT_INTERVAL = 5                 # Nodes send heartbeat every N seconds
NODE_TIMEOUT       = 15               # Mark node dead after N seconds of silence
REPLICATION_CHECK_INTERVAL = 3       # How often master checks replica health

# Logging
LOG_FORMAT  = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Storage paths
STORAGE_BASE = "nodes/storage"        # Relative root for chunk files
METADATA_FILE = "master/metadata.json"

# Socket / protocol
BUFFER_SIZE   = 65536                 # 64 KB read buffer
ENCODING      = "utf-8"
SOCKET_TIMEOUT = 10                   # seconds
