import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget

from gui.file_manager import FileManager
from gui.dashboard import Dashboard
from gui.node_monitor import NodeMonitor
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class DFSGui(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Distributed File System - V2 🚀")
        self.setGeometry(200, 100, 1100, 650)

        tabs = QTabWidget()

        tabs.addTab(Dashboard(), "📊 Dashboard")
        tabs.addTab(FileManager(), "📂 File Manager")
        tabs.addTab(NodeMonitor(), "📡 Nodes")

        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DFSGui()
    window.show()
    sys.exit(app.exec_())