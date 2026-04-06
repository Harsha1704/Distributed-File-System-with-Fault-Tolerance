from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QHBoxLayout
)

from client.client import upload, download, delete_file
import socket
from client.config import MASTER_HOST, MASTER_PORT
from common.utils import send_message, recv_message


class FileManager(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["Filename"])
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()

        upload_btn = QPushButton("Upload")
        download_btn = QPushButton("Download")
        delete_btn = QPushButton("Delete")
        refresh_btn = QPushButton("Refresh")

        upload_btn.clicked.connect(self.upload_file)
        download_btn.clicked.connect(self.download_file)
        delete_btn.clicked.connect(self.delete_selected_file)
        refresh_btn.clicked.connect(self.refresh_files)

        btn_layout.addWidget(upload_btn)
        btn_layout.addWidget(download_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(refresh_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.refresh_files()

    # ------------------------
    # Upload
    # ------------------------
    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")

        if file_path:
            try:
                upload(file_path)
                QMessageBox.information(self, "Success", "File uploaded!")
                self.refresh_files()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ------------------------
    # Download
    # ------------------------
    def download_file(self):
        row = self.table.currentRow()

        if row == -1:
            QMessageBox.warning(self, "Warning", "Select a file")
            return

        filename = self.table.item(row, 0).text()

        try:
            download(filename)
            QMessageBox.information(self, "Success", f"{filename} downloaded!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ------------------------
    # Delete
    # ------------------------
    def delete_selected_file(self):
        row = self.table.currentRow()

        if row == -1:
            QMessageBox.warning(self, "Warning", "Select a file")
            return

        filename = self.table.item(row, 0).text()

        try:
            delete_file(filename)
            QMessageBox.information(self, "Deleted", f"{filename} deleted!")
            self.refresh_files()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ------------------------
    # Refresh
    # ------------------------
    def refresh_files(self):
        try:
            sock = socket.socket()
            sock.connect((MASTER_HOST, MASTER_PORT))

            send_message(sock, {"action": "LIST_FILES"})
            response = recv_message(sock)

            files = response.get("files", [])

            self.table.setRowCount(len(files))

            for i, f in enumerate(files):
                self.table.setItem(i, 0, QTableWidgetItem(f["filename"]))

            sock.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))