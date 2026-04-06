from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import QTimer
import socket

from client.config import MASTER_HOST, MASTER_PORT
from common.utils import send_message, recv_message


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()

        self.title = QLabel("📊 Distributed File System Overview")
        self.layout.addWidget(self.title)

        self.files_label = QLabel("Total Files: --")
        self.chunks_label = QLabel("Total Chunks: --")
        self.nodes_label = QLabel("Active Nodes: --")

        self.layout.addWidget(self.files_label)
        self.layout.addWidget(self.chunks_label)
        self.layout.addWidget(self.nodes_label)

        self.setLayout(self.layout)

        # 🔥 Auto refresh every 2 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dashboard)
        self.timer.start(2000)

    # -----------------------------
    # Update Dashboard Data
    # -----------------------------
    def update_dashboard(self):
        try:
            sock = socket.socket()
            sock.connect((MASTER_HOST, MASTER_PORT))

            # Get file list
            send_message(sock, {"action": "LIST_FILES"})
            file_response = recv_message(sock)

            files = file_response.get("files", [])

            total_files = len(files)
            total_chunks = sum(f.get("num_chunks", 0) for f in files)

            sock.close()

            # Get node status
            sock = socket.socket()
            sock.connect((MASTER_HOST, MASTER_PORT))

            send_message(sock, {"action": "NODE_STATUS"})
            node_response = recv_message(sock)

            nodes = node_response.get("nodes", [])
            active_nodes = sum(1 for n in nodes if n["alive"])

            sock.close()

            # ✅ Update UI
            self.files_label.setText(f"Total Files: {total_files}")
            self.chunks_label.setText(f"Total Chunks: {total_chunks}")
            self.nodes_label.setText(f"Active Nodes: {active_nodes}")
            self.title.setText("📊 DFS Live Dashboard 🚀")

        except Exception as e:
            self.files_label.setText("Total Files: ERROR")
            self.chunks_label.setText("Total Chunks: ERROR")
            self.nodes_label.setText("Active Nodes: ERROR")