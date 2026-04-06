#!/usr/bin/env bash
# ============================================================
# run.sh — Start/Stop Distributed File System (Linux/macOS)
# Usage:
#   bash run.sh        → start system
#   bash run.sh stop   → stop system
# ============================================================

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PIDS_FILE="$ROOT/.dfs_pids"

start() {
    echo "=============================="
    echo "  Distributed File System"
    echo "=============================="

    # Create required folders
    mkdir -p logs nodes/storage/node{1,2,3} downloads

    echo "[1/4] Starting master..."

    # Start master in new terminal if possible
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "python3 -m master.master; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -hold -e "python3 -m master.master" &
    else
        # fallback (background)
        python3 -m master.master >> logs/master.log 2>&1 &
        echo $! >> "$PIDS_FILE"
    fi

    sleep 2

    for i in 1 2 3; do
        echo "[$(($i+1))/4] Starting node $i..."

        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "NODE_ID=$i python3 -m nodes.node; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -hold -e "NODE_ID=$i python3 -m nodes.node" &
        else
            NODE_ID=$i python3 -m nodes.node >> logs/node${i}.log 2>&1 &
            echo $! >> "$PIDS_FILE"
        fi

        sleep 1
    done

    echo ""
    echo "✅ All processes started."
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
    echo "Stopping DFS processes..."

    # Kill background processes (if used)
    if [ -f "$PIDS_FILE" ]; then
        while read -r pid; do
            kill "$pid" 2>/dev/null && echo "  Killed PID $pid" || true
        done < "$PIDS_FILE"
        rm -f "$PIDS_FILE"
    fi

    # Kill terminal-based processes (like Windows version)
    pkill -f "master.master" 2>/dev/null || true
    pkill -f "nodes.node" 2>/dev/null || true

    echo "Done."
}

case "${1:-start}" in
    start) start ;;
    stop)  stop ;;
    restart) stop; sleep 1; start ;;
    *) echo "Usage: $0 [start|stop|restart]"; exit 1 ;;
esac