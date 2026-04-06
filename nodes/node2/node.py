"""node2/node.py — Sets NODE_ID=2 and delegates to shared node logic."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
os.environ["NODE_ID"] = "2"
from nodes.node import main
if __name__ == "__main__":
    main()
