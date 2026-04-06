from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import QTimer
import socket

from client.config import MASTER_HOST, MASTER_PORT
from common.utils import send_message, recv_message


class NodeMonitor(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()

        self.title = QLabel("📡 Node Monitor")
        self.layout.addWidget(self.title)

        self.node_labels = {}
        for i in range(1, 4):
            lbl = QLabel(f"Node{i}: Checking...")
            self.node_labels[i] = lbl
            self.layout.addWidget(lbl)

        self.setLayout(self.layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_nodes)
        self.timer.start(2000)

    def update_nodes(self):
        try:
            sock = socket.socket()
            sock.connect((MASTER_HOST, MASTER_PORT))

            send_message(sock, {"action": "NODE_STATUS"})
            response = recv_message(sock)
            sock.close()

            for node in response.get("nodes", []):
                status = "🟢 ACTIVE" if node["alive"] else "🔴 DEAD"
                self.node_labels[node["node_id"]].setText(
                    f"Node{node['node_id']}: {status}"
                )

        except Exception:
            for i in self.node_labels:
                self.node_labels[i].setText(f"Node{i}: ❌ ERROR")