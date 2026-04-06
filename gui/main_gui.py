import sys
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QTabWidget, QFileDialog, QMessageBox
)


class DFSGui(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Distributed File System Dashboard")
        self.setGeometry(200, 100, 900, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tabs
        self.dashboard_tab = QWidget()
        self.files_tab = QWidget()
        self.nodes_tab = QWidget()

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.files_tab, "File Manager")
        self.tabs.addTab(self.nodes_tab, "Node Monitor")

        self.init_dashboard()
        self.init_files()
        self.init_nodes()

    # ---------------- DASHBOARD ---------------- #
    def init_dashboard(self):
        layout = QVBoxLayout()

        self.status_label = QLabel("DFS Status Overview")
        self.refresh_btn = QPushButton("Refresh")

        self.refresh_btn.clicked.connect(self.load_dashboard)

        layout.addWidget(self.status_label)
        layout.addWidget(self.refresh_btn)

        self.dashboard_tab.setLayout(layout)

    def load_dashboard(self):
        try:
            result = subprocess.check_output(
                ["py", "-m", "client.client", "list"],
                text=True
            )
            self.status_label.setText(f"Files Info:\n{result}")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")

    # ---------------- FILE MANAGER ---------------- #
    def init_files(self):
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Filename", "Chunks", "Hash"])

        upload_btn = QPushButton("Upload File")
        download_btn = QPushButton("Download File")
        delete_btn = QPushButton("Delete File")
        refresh_btn = QPushButton("Refresh")

        upload_btn.clicked.connect(self.upload_file)
        download_btn.clicked.connect(self.download_file)
        delete_btn.clicked.connect(self.delete_file)
        refresh_btn.clicked.connect(self.load_files)

        layout.addWidget(self.table)
        layout.addWidget(upload_btn)
        layout.addWidget(download_btn)
        layout.addWidget(delete_btn)
        layout.addWidget(refresh_btn)

        self.files_tab.setLayout(layout)

    def load_files(self):
        try:
            output = subprocess.check_output(
                ["py", "-m", "client.client", "list"],
                text=True
            )

            lines = output.strip().split("\n")[2:]
            self.table.setRowCount(len(lines))

            for i, line in enumerate(lines):
                parts = line.split()
                if len(parts) >= 3:
                    self.table.setItem(i, 0, QTableWidgetItem(parts[0]))
                    self.table.setItem(i, 1, QTableWidgetItem(parts[1]))
                    self.table.setItem(i, 2, QTableWidgetItem(parts[2]))

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName()
        if file_path:
            subprocess.call(["py", "-m", "client.client", "upload", file_path])
            QMessageBox.information(self, "Success", "File Uploaded")
            self.load_files()

    def download_file(self):
        row = self.table.currentRow()
        if row == -1:
            return

        filename = self.table.item(row, 0).text()
        subprocess.call(["py", "-m", "client.client", "download", filename])
        QMessageBox.information(self, "Success", "File Downloaded")

    def delete_file(self):
        row = self.table.currentRow()
        if row == -1:
            return

        filename = self.table.item(row, 0).text()
        subprocess.call(["py", "-m", "client.client", "delete", filename])
        QMessageBox.information(self, "Deleted", "File Deleted")
        self.load_files()

    # ---------------- NODE MONITOR ---------------- #
    def init_nodes(self):
        layout = QVBoxLayout()

        self.node_label = QLabel("Node Status (Check logs for live info)")
        refresh_btn = QPushButton("Refresh Nodes")

        refresh_btn.clicked.connect(self.load_nodes)

        layout.addWidget(self.node_label)
        layout.addWidget(refresh_btn)

        self.nodes_tab.setLayout(layout)

    def load_nodes(self):
        self.node_label.setText("Check terminal logs for node status.\n(Advanced integration coming soon)")


# ---------------- RUN APP ---------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DFSGui()
    window.show()
    sys.exit(app.exec_())