from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)

from gui.shared_state import GUI_STATE


class LogsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        hero = QFrame()
        hero.setObjectName('heroPanel')
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        badge = QLabel('SYSTEM LOGS')
        badge.setObjectName('microLabel')
        title = QLabel('Logs')
        title.setObjectName('pageTitle')
        subtitle = QLabel('Recent GUI activity, refresh events, connectivity changes, and node updates.')
        subtitle.setObjectName('pageSubtitle')
        subtitle.setWordWrap(True)
        hero_layout.addWidget(badge, alignment=Qt.AlignLeft)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        toolbar = QFrame()
        toolbar.setObjectName('panel')
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(18, 16, 18, 16)
        toolbar_layout.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search logs by message, source, or level...')
        self.clear_btn = QPushButton('Clear Logs')
        self.clear_btn.setObjectName('dangerButton')
        toolbar_layout.addWidget(self.search, 1)
        toolbar_layout.addWidget(self.clear_btn)
        root.addWidget(toolbar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Time', 'Level', 'Source', 'Message'])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        footer = QFrame()
        footer.setObjectName('panel')
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 12, 18, 12)
        self.summary = QLabel('0 log entry(s) visible')
        self.summary.setObjectName('smallMuted')
        footer_layout.addWidget(self.summary)
        footer_layout.addStretch(1)
        root.addWidget(footer)

        self.search.textChanged.connect(self.refresh_view)
        self.clear_btn.clicked.connect(self.clear_logs)
        GUI_STATE.log_added.connect(lambda _entry: self.refresh_view())
        self.refresh_view()

    def clear_logs(self):
        GUI_STATE.clear_logs()
        self.refresh_view()

    def refresh_view(self):
        query = self.search.text().strip().lower()
        logs = list(GUI_STATE.logs)
        if query:
            logs = [
                entry for entry in logs
                if query in entry['time'].lower()
                or query in entry['level'].lower()
                or query in entry['source'].lower()
                or query in entry['message'].lower()
            ]
        self.table.setRowCount(len(logs))
        for row, entry in enumerate(logs):
            values = [entry['time'], entry['level'], entry['source'], entry['message']]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if col == 3 else Qt.AlignCenter))
                self.table.setItem(row, col, item)
        self.summary.setText(f'{len(logs)} log entry(s) visible')
