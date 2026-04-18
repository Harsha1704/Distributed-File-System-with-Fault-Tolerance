
import os
import socket
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit
)

from client.client import upload, download, delete_file
from client.config import MASTER_HOST, MASTER_PORT
from common.utils import send_message, recv_message
from gui.shared_state import GUI_STATE


class MetricCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName('softPanel')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(4)
        lbl = QLabel(title)
        lbl.setObjectName('statTitle')
        self.value = QLabel('--')
        self.value.setObjectName('smallValue')
        self.meta = QLabel('Waiting for data')
        self.meta.setObjectName('smallMuted')
        self.meta.setWordWrap(True)
        layout.addWidget(lbl)
        layout.addWidget(self.value)
        layout.addWidget(self.meta)


class FileManager(QWidget):
    def __init__(self):
        super().__init__()
        self.all_files = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        hero = QFrame(); hero.setObjectName('heroPanel')
        h_layout = QVBoxLayout(hero); h_layout.setContentsMargins(24, 24, 24, 24)
        badge = QLabel('FILE OPERATIONS'); badge.setObjectName('microLabel')
        title = QLabel('File Manager'); title.setObjectName('pageTitle')
        subtitle = QLabel('Search, upload, download, refresh, and inspect distributed files with a cleaner desktop workflow.')
        subtitle.setObjectName('pageSubtitle'); subtitle.setWordWrap(True)
        h_layout.addWidget(badge, alignment=Qt.AlignLeft); h_layout.addWidget(title); h_layout.addWidget(subtitle)
        root.addWidget(hero)

        metrics = QHBoxLayout(); metrics.setSpacing(16)
        self.files_card = MetricCard('Files')
        self.types_card = MetricCard('File Types')
        self.chunks_card = MetricCard('Chunks')
        self.selected_card = MetricCard('Selected')
        metrics.addWidget(self.files_card); metrics.addWidget(self.types_card); metrics.addWidget(self.chunks_card); metrics.addWidget(self.selected_card)
        root.addLayout(metrics)

        toolbar = QFrame(); toolbar.setObjectName('panel')
        t_layout = QHBoxLayout(toolbar); t_layout.setContentsMargins(16, 14, 16, 14); t_layout.setSpacing(10)
        self.search_box = QLineEdit(); self.search_box.setPlaceholderText('Search files by name...')
        self.upload_btn = QPushButton('Upload File'); self.upload_btn.setObjectName('primaryButton')
        self.download_btn = QPushButton('Download Selected')
        self.delete_btn = QPushButton('Delete Selected'); self.delete_btn.setObjectName('dangerButton')
        self.refresh_btn = QPushButton('Refresh')
        t_layout.addWidget(self.search_box, 1); t_layout.addWidget(self.upload_btn); t_layout.addWidget(self.download_btn); t_layout.addWidget(self.delete_btn); t_layout.addWidget(self.refresh_btn)
        root.addWidget(toolbar)

        body = QHBoxLayout(); body.setSpacing(18)

        table_panel = QFrame(); table_panel.setObjectName('panel')
        table_layout = QVBoxLayout(table_panel); table_layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Filename', 'Type', 'Size'])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table_layout.addWidget(self.table)
        body.addWidget(table_panel, 4)

        details = QFrame(); details.setObjectName('panel')
        d_layout = QVBoxLayout(details)
        d_layout.setContentsMargins(18, 18, 18, 18)
        d_layout.setSpacing(8)
        d_title = QLabel('File Details'); d_title.setObjectName('sectionTitle')
        self.d_name = QLabel('No file selected'); self.d_name.setObjectName('sectionTitle')
        self.d_type = QLabel('Type: --'); self.d_type.setObjectName('smallMuted')
        self.d_size = QLabel('Size / Chunks: --'); self.d_size.setObjectName('smallMuted')
        self.d_profile = QLabel('Chunk Profile: --'); self.d_profile.setObjectName('smallMuted')
        self.d_desc = QLabel('Select a file from the table to inspect its metadata. You can also open Analytics for the full per-file chunk view and chunk distribution graph.')
        self.d_desc.setObjectName('smallMuted'); self.d_desc.setWordWrap(True)
        d_layout.addWidget(d_title); d_layout.addWidget(self.d_name); d_layout.addWidget(self.d_type); d_layout.addWidget(self.d_size); d_layout.addWidget(self.d_profile); d_layout.addWidget(self.d_desc); d_layout.addStretch(1)
        body.addWidget(details, 1)

        root.addLayout(body, 1)

        footer = QFrame(); footer.setObjectName('panel')
        f_layout = QHBoxLayout(footer); f_layout.setContentsMargins(18, 12, 18, 12)
        self.summary = QLabel('0 file(s) visible in the table')
        self.summary.setObjectName('smallMuted')
        f_layout.addWidget(self.summary); f_layout.addStretch(1)
        root.addWidget(footer)

        self.search_box.textChanged.connect(self.apply_filter)
        self.upload_btn.clicked.connect(self.upload_file)
        self.download_btn.clicked.connect(self.download_file)
        self.delete_btn.clicked.connect(self.delete_selected_file)
        self.refresh_btn.clicked.connect(self.refresh_files)
        self.table.itemSelectionChanged.connect(self.update_selection_details)
        self.refresh_files()

    def _infer_type(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        return ext[1:].upper() if ext else 'FILE'

    def _format_size(self, file_obj: dict) -> str:
        size = file_obj.get('size')
        if isinstance(size, (int, float)):
            return f'{size:,} B'
        chunks = file_obj.get('num_chunks')
        return f'{chunks} chunk(s)' if chunks is not None else '--'

    def selected_filename(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.text() if item else None

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select a file to upload')
        if not file_path:
            return
        try:
            upload(file_path)
            GUI_STATE.add_log('INFO', 'Files', f'Uploaded file {os.path.basename(file_path)}.')
            QMessageBox.information(self, 'Upload Complete', f'Uploaded: {os.path.basename(file_path)}')
            self.refresh_files()
        except Exception as e:
            GUI_STATE.add_log('ERROR', 'Files', f'Upload failed: {e}')
            QMessageBox.critical(self, 'Upload Failed', str(e))

    def download_file(self):
        filename = self.selected_filename()
        if not filename:
            QMessageBox.warning(self, 'No File Selected', 'Please select a file from the table.')
            return
        try:
            download(filename)
            GUI_STATE.add_log('INFO', 'Files', f'Downloaded file {filename}.')
            QMessageBox.information(self, 'Download Complete', f'Downloaded: {filename}')
        except Exception as e:
            GUI_STATE.add_log('ERROR', 'Files', f'Download failed for {filename}: {e}')
            QMessageBox.critical(self, 'Download Failed', str(e))

    def delete_selected_file(self):
        filename = self.selected_filename()
        if not filename:
            QMessageBox.warning(self, 'No File Selected', 'Please select a file from the table.')
            return
        confirm = QMessageBox.question(self, 'Confirm Delete', f"Delete '{filename}' from the distributed file system?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        try:
            delete_file(filename)
            GUI_STATE.add_log('WARN', 'Files', f'Deleted file {filename}.')
            QMessageBox.information(self, 'Delete Complete', f'Deleted: {filename}')
            self.refresh_files()
        except Exception as e:
            GUI_STATE.add_log('ERROR', 'Files', f'Delete failed for {filename}: {e}')
            QMessageBox.critical(self, 'Delete Failed', str(e))

    def populate_table(self, files):
        self.table.setRowCount(len(files))
        for row, f in enumerate(files):
            filename = f.get('filename', 'Unknown')
            values = [filename, self._infer_type(filename), self._format_size(f)]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if col == 0 else Qt.AlignCenter))
                self.table.setItem(row, col, item)
        self.summary.setText(f'{len(files)} file(s) visible in the table')

    def apply_filter(self):
        query = self.search_box.text().strip().lower()
        filtered = self.all_files if not query else [f for f in self.all_files if query in f.get('filename', '').lower()]
        self.populate_table(filtered)
        self.update_selection_details()

    def update_selection_details(self):
        filename = self.selected_filename()
        if not filename:
            self.selected_card.value.setText('--'); self.selected_card.meta.setText('Select a row to inspect details')
            self.d_name.setText('No file selected'); self.d_type.setText('Type: --'); self.d_size.setText('Size / Chunks: --'); self.d_profile.setText('Chunk Profile: --')
            self.d_desc.setText('Select a file from the table to inspect its metadata. You can also open Analytics for the full per-file chunk view and chunk distribution graph.')
            GUI_STATE.update_stats(selected_file='--', selected_type='--', selected_size='--', selected_chunks=0)
            return
        file_obj = next((f for f in self.all_files if f.get('filename') == filename), None)
        ftype = self._infer_type(filename)
        ssize = self._format_size(file_obj or {})
        chunks = int((file_obj or {}).get('num_chunks', 0) or 0)
        profile = 'Multi-chunk file' if chunks > 1 else 'Single chunk file'
        self.selected_card.value.setText(filename); self.selected_card.meta.setText('Current row selected in the table')
        self.d_name.setText(filename); self.d_type.setText(f'Type: {ftype}'); self.d_size.setText(f'Size / Chunks: {ssize}'); self.d_profile.setText(f'Chunk Profile: {profile}')
        self.d_desc.setText(f'Selected file is stored in the distributed system metadata as {filename}. It currently uses {chunks} chunk(s).')
        GUI_STATE.update_stats(selected_file=filename, selected_type=ftype, selected_size=ssize, selected_chunks=chunks)

    def refresh_files(self):
        try:
            sock = socket.socket(); sock.settimeout(3); sock.connect((MASTER_HOST, MASTER_PORT))
            send_message(sock, {'action': 'LIST_FILES'})
            response = recv_message(sock)
            sock.close()
            self.all_files = response.get('files', [])
            file_types = {self._infer_type(f.get('filename', '')) for f in self.all_files}
            total_chunks = sum(int(f.get('num_chunks', 0) or 0) for f in self.all_files)
            multi_chunk = sum(1 for f in self.all_files if int(f.get('num_chunks', 0) or 0) > 1)
            most_chunked = max(self.all_files, key=lambda f: int(f.get('num_chunks', 0) or 0)).get('filename', '--') if self.all_files else '--'
            self.files_card.value.setText(str(len(self.all_files))); self.files_card.meta.setText('Total file entries in the DFS')
            self.types_card.value.setText(str(len(file_types))); self.types_card.meta.setText('Unique extensions currently stored')
            self.chunks_card.value.setText(str(total_chunks)); self.chunks_card.meta.setText('Distributed chunk count across all files')
            self.apply_filter()
            GUI_STATE.set_files(self.all_files)
            GUI_STATE.update_stats(total_files=len(self.all_files),total_chunks=total_chunks,file_types=len(file_types),multi_chunk_files=multi_chunk,most_chunked_file=most_chunked,)
            GUI_STATE.add_log('INFO', 'Files', f'Refreshed file list with {len(self.all_files)} file(s).')
        except Exception as e:
            GUI_STATE.add_log('ERROR', 'Files', f'Refresh failed: {e}')
            QMessageBox.critical(self, 'Refresh Failed', str(e))
