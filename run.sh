#!/usr/bin/env bash
# ============================================================
# run.sh — Start the entire DFS (master + 3 nodes)
# Usage:  bash run.sh [stop]
# ============================================================

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PIDS_FILE="$ROOT/.dfs_pids"

start() {
    echo "=============================="
    echo "  Distributed File System"
    echo "=============================="

    mkdir -p logs nodes/storage/node{1,2,3} downloads

    echo "[1/4] Starting master …"
    python3 -m master.master >> logs/master.log 2>&1 &
    echo $! >> "$PIDS_FILE"
    sleep 1

    for i in 1 2 3; do
        echo "[$(($i+1))/4] Starting node $i …"
        NODE_ID=$i python3 -m nodes.node >> logs/node${i}.log 2>&1 &
        echo $! >> "$PIDS_FILE"
        sleep 0.5
    done

    echo ""
    echo "✅  All processes started."
    echo "   Master : localhost:9000"
    echo "   Node 1 : localhost:9100"
    echo "   Node 2 : localhost:9101"
    echo "   Node 3 : localhost:9102"
    echo ""
    echo "Client commands:"
    echo "   python3 -m client.client upload   <file>"
    echo "   python3 -m client.client download <file>"
    echo "   python3 -m client.client list"
    echo ""
    echo "Stop with:  bash run.sh stop"
}

stop() {
    if [ ! -f "$PIDS_FILE" ]; then
        echo "No PID file found. Nothing to stop."
        return
    fi
    echo "Stopping DFS processes …"
    while read -r pid; do
        kill "$pid" 2>/dev/null && echo "  Killed PID $pid" || true
    done < "$PIDS_FILE"
    rm -f "$PIDS_FILE"
    echo "Done."
}

case "${1:-start}" in
    start) start ;;
    stop)  stop  ;;
    restart) stop; sleep 1; start ;;
    *) echo "Usage: $0 [start|stop|restart]"; exit 1 ;;
esac
