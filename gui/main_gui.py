import os
import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QListWidget,
    QListWidgetItem, QStackedWidget, QLabel, QFrame, QPushButton,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QColor

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from gui.dashboard import Dashboard
from gui.file_manager import FileManager
from gui.node_monitor import NodeMonitor
from gui.analytics_page import AnalyticsPage
from gui.logs_page import LogsPage
from gui.shared_state import GUI_STATE


DARK_THEME = """
QWidget {
    background: #09111f;
    color: #e7eef8;
    font-family: 'Segoe UI';
    font-size: 14px;
}
QFrame#rootFrame {
    background: #081120;
}
QFrame#sidebar {
    background: #0f1b30;
    border: 1px solid #1d3050;
    border-radius: 24px;
}
QFrame#topBar, QFrame#panel, QFrame#card, QFrame#nodeCard, QFrame#softPanel, QFrame#heroPanel {
    background: #0d1a2e;
    border: 1px solid #1f3150;
    border-radius: 20px;
}
QFrame#heroPanel {
    background: #10203a;
}
QLabel#brandTitle { font-size: 22px; font-weight: 900; color: #ffffff; }
QLabel#brandSub { font-size: 12px; color: #98abc4; }
QLabel#pageTitle { font-size: 30px; font-weight: 900; color: #f8fbff; }
QLabel#pageSubtitle, QLabel#smallMuted, QLabel#statMeta { font-size: 12px; color: #9bb0cb; }
QLabel#sectionTitle { font-size: 18px; font-weight: 800; color: #f8fbff; }
QLabel#statTitle { font-size: 13px; font-weight: 700; color: #b7c6d9; }
QLabel#statValue { font-size: 38px; font-weight: 900; color: #ffffff; }
QLabel#smallValue { font-size: 18px; font-weight: 800; color: #ffffff; }
QLabel#microLabel {
    font-size: 11px; font-weight: 700; color: #66e2b4;
    padding: 4px 10px; border-radius: 10px;
    background: rgba(22, 163, 74, 0.10); border: 1px solid rgba(34, 197, 94, 0.30);
}
QLabel#statusBadge {
    padding: 8px 14px; border-radius: 14px; font-weight: 800;
    background: #0a1323; border: 1px solid #30435f;
}
QLabel#statusBadge[state='ok'] { color: #87efac; border-color: #14532d; background: rgba(34,197,94,0.08); }
QLabel#statusBadge[state='warn'] { color: #fde68a; border-color: #854d0e; background: rgba(234,179,8,0.08); }
QLabel#statusBadge[state='bad'] { color: #fca5a5; border-color: #7f1d1d; background: rgba(239,68,68,0.08); }
QLabel#nodeState { font-size: 24px; font-weight: 900; }
QLabel#nodeState[state='ok'] { color: #22c55e; }
QLabel#nodeState[state='warn'] { color: #f59e0b; }
QLabel#nodeState[state='bad'] { color: #ef4444; }
QPushButton {
    background: #182946; color: #e8eef8; border: 1px solid #2f486e;
    border-radius: 13px; padding: 11px 16px; font-weight: 800;
}
QPushButton:hover { background: #22385b; }
QPushButton#primaryButton { background: #3b82f6; border: 1px solid #5b98ff; color: white; }
QPushButton#primaryButton:hover { background: #2f72e0; }
QPushButton#dangerButton { background: #dc2626; border: 1px solid #ef4444; color: white; }
QPushButton#dangerButton:hover { background: #c91f1f; }
QPushButton#ghostButton { background: transparent; border: 1px solid #294364; }
QLineEdit {
    background: #0a1527; color: #f8fbff; border: 1px solid #29415f;
    border-radius: 12px; padding: 10px 14px;
}
QLineEdit:focus { border: 1px solid #4f8cff; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item {
    color: #d2dff0; border: 1px solid transparent; border-radius: 14px;
    padding: 14px 16px; margin-bottom: 7px; font-weight: 800;
}
QListWidget::item:hover { background: #12213a; }
QListWidget::item:selected { background: #17305a; color: white; border: 1px solid #2d5ca0; }
QTableWidget {
    background: #091325; border: 1px solid #1d2d47; border-radius: 18px;
    gridline-color: #1b2940; selection-background-color: #316be6; selection-color: white;
    alternate-background-color: #0c182b;
}
QHeaderView::section {
    background: #15243d; color: #f8fbff; padding: 12px; font-weight: 900;
    border: none; border-bottom: 1px solid #243752;
}
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #3a5273; min-height: 30px; border-radius: 5px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #3a5273; min-width: 30px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { height: 0px; width: 0px; }
QStatusBar { background: #081120; color: #94a8c2; border-top: 1px solid #16263f; }
QLabel {
    background: transparent;
    border: none;
}
QLabel#brandTitle,
QLabel#brandSub,
QLabel#pageTitle,
QLabel#pageSubtitle,
QLabel#sectionTitle,
QLabel#statTitle,
QLabel#statValue,
QLabel#statMeta,
QLabel#smallMuted,
QLabel#nodeState,
QLabel#microLabel,
QLabel#statusBadge {
    background: transparent;
    border: none;
}
"""

LIGHT_THEME = """
QWidget {
    background: #f3f6fb;
    color: #1d2a3b;
    font-family: 'Segoe UI';
    font-size: 14px;
}
QFrame#rootFrame { background: #eef3fa; }
QFrame#sidebar { background: #ffffff; border: 1px solid #dce5f2; border-radius: 24px; }
QFrame#topBar, QFrame#panel, QFrame#card, QFrame#nodeCard, QFrame#softPanel, QFrame#heroPanel {
    background: #ffffff; border: 1px solid #dce5f2; border-radius: 20px;
}
QFrame#heroPanel { background: #f7faff; }
QLabel#brandTitle { font-size: 22px; font-weight: 900; color: #10233d; }
QLabel#brandSub { font-size: 12px; color: #64748b; }
QLabel#pageTitle { font-size: 30px; font-weight: 900; color: #10233d; }
QLabel#pageSubtitle, QLabel#smallMuted, QLabel#statMeta { font-size: 12px; color: #64748b; }
QLabel#sectionTitle { font-size: 18px; font-weight: 800; color: #10233d; }
QLabel#statTitle { font-size: 13px; font-weight: 700; color: #475569; }
QLabel#statValue { font-size: 38px; font-weight: 900; color: #10233d; }
QLabel#smallValue { font-size: 18px; font-weight: 800; color: #10233d; }
QLabel#microLabel {
    font-size: 11px; font-weight: 700; color: #0f766e;
    padding: 4px 10px; border-radius: 10px;
    background: #e6fffb; border: 1px solid #8ee4d6;
}
QLabel#statusBadge {
    padding: 8px 14px; border-radius: 14px; font-weight: 800;
    background: #f8fbff; border: 1px solid #cfd8e7;
}
QLabel#statusBadge[state='ok'] { color: #15803d; border-color: #86efac; background: #effcf3; }
QLabel#statusBadge[state='warn'] { color: #a16207; border-color: #fde68a; background: #fff9e8; }
QLabel#statusBadge[state='bad'] { color: #b91c1c; border-color: #fecaca; background: #fff1f2; }
QLabel#nodeState { font-size: 24px; font-weight: 900; }
QLabel#nodeState[state='ok'] { color: #16a34a; }
QLabel#nodeState[state='warn'] { color: #d97706; }
QLabel#nodeState[state='bad'] { color: #dc2626; }
QPushButton {
    background: #f8fbff; color: #1d2a3b; border: 1px solid #cfd8e7;
    border-radius: 13px; padding: 11px 16px; font-weight: 800;
}
QPushButton:hover { background: #edf3fb; }
QPushButton#primaryButton { background: #2563eb; border: 1px solid #3b82f6; color: white; }
QPushButton#primaryButton:hover { background: #1d4ed8; }
QPushButton#dangerButton { background: #dc2626; border: 1px solid #ef4444; color: white; }
QPushButton#dangerButton:hover { background: #b91c1c; }
QPushButton#ghostButton { background: transparent; border: 1px solid #cfd8e7; }
QLineEdit {
    background: #ffffff; color: #10233d; border: 1px solid #d1d9e6;
    border-radius: 12px; padding: 10px 14px;
}
QLineEdit:focus { border: 1px solid #3b82f6; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item {
    color: #334155; border: 1px solid transparent; border-radius: 14px;
    padding: 14px 16px; margin-bottom: 7px; font-weight: 800;
}
QListWidget::item:hover { background: #edf3fb; }
QListWidget::item:selected { background: #e8f0ff; color: #10233d; border: 1px solid #9ab6ef; }
QTableWidget {
    background: #ffffff; border: 1px solid #dce5f2; border-radius: 18px;
    gridline-color: #edf2f8; selection-background-color: #dbeafe; selection-color: #10233d;
    alternate-background-color: #f8fbff;
}
QHeaderView::section {
    background: #f7faff; color: #10233d; padding: 12px; font-weight: 900;
    border: none; border-bottom: 1px solid #e2e8f0;
}
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #c5d2e5; min-height: 30px; border-radius: 5px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #c5d2e5; min-width: 30px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { height: 0px; width: 0px; }
QStatusBar { background: #eef3fa; color: #64748b; border-top: 1px solid #dce5f2; }
QLabel {
    background: transparent;
    border: none;
}
QLabel#brandTitle,
QLabel#brandSub,
QLabel#pageTitle,
QLabel#pageSubtitle,
QLabel#sectionTitle,
QLabel#statTitle,
QLabel#statValue,
QLabel#statMeta,
QLabel#smallMuted,
QLabel#nodeState,
QLabel#microLabel,
QLabel#statusBadge {
    background: transparent;
    border: none;
}

"""


def apply_shadow(widget, blur=24, alpha=55):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


class DFSGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Distributed File System Control Center')
        self.resize(1450, 880)
        self.setMinimumSize(QSize(1240, 780))
        self.current_theme = 'dark'

        root = QFrame(); root.setObjectName('rootFrame')
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        sidebar = QFrame(); sidebar.setObjectName('sidebar'); sidebar.setFixedWidth(250)
        apply_shadow(sidebar)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(18, 20, 18, 20)
        side_layout.setSpacing(14)

        brand = QFrame()
        b_layout = QVBoxLayout(brand); b_layout.setContentsMargins(0, 0, 0, 8)
        title = QLabel('🚀 DFS Control Center'); title.setObjectName('brandTitle')
        sub = QLabel('Modern desktop admin panel for your distributed file system'); sub.setObjectName('brandSub'); sub.setWordWrap(True)
        b_layout.addWidget(title); b_layout.addWidget(sub)

        self.nav = QListWidget()
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.nav.setFixedHeight(360)
        for text in ['📊 Dashboard', '📁 File Manager', '🖧 Nodes', '📈 Analytics', '🧾 Logs']:
            QListWidgetItem(text, self.nav)
        self.nav.setCurrentRow(0)

        footer = QFrame(); footer.setObjectName('softPanel')
        f_layout = QVBoxLayout(footer); f_layout.setContentsMargins(16, 16, 16, 16)
        f_title = QLabel('System'); f_title.setObjectName('sectionTitle')
        f_text = QLabel('Monitor files, chunks, health, charts, and activity logs from one clean desktop panel.')
        f_text.setObjectName('smallMuted'); f_text.setWordWrap(True)
        f_chip = QLabel('Ready for demo'); f_chip.setObjectName('microLabel')
        f_layout.addWidget(f_title); f_layout.addWidget(f_text); f_layout.addWidget(f_chip, alignment=Qt.AlignLeft)

        side_layout.addWidget(brand)
        side_layout.addWidget(self.nav)
        side_layout.addStretch(1)
        side_layout.addWidget(footer)

        content = QFrame(); content.setObjectName('contentArea')
        content_layout = QVBoxLayout(content); content_layout.setContentsMargins(0, 0, 0, 0); content_layout.setSpacing(16)

        top = QFrame(); top.setObjectName('topBar')
        t_layout = QHBoxLayout(top); t_layout.setContentsMargins(16, 12, 16, 12); t_layout.setSpacing(12)
        self.section_title = QLabel('DFS Control Center • Dashboard'); self.section_title.setObjectName('sectionTitle')
        self.section_subtitle = QLabel('Cluster overview, health, and live metrics'); self.section_subtitle.setObjectName('smallMuted')
        title_box = QVBoxLayout(); title_box.setSpacing(2); title_box.addWidget(self.section_title); title_box.addWidget(self.section_subtitle)
        self.theme_btn = QPushButton('☀ Light Mode'); self.theme_btn.setObjectName('ghostButton')
        self.framework_chip = QLabel('PyQt5 + QSS'); self.framework_chip.setObjectName('statusBadge'); self.framework_chip.setProperty('state', 'ok')
        self.clock_chip = QLabel('--'); self.clock_chip.setObjectName('statusBadge'); self.clock_chip.setProperty('state', 'warn')
        t_layout.addLayout(title_box); t_layout.addStretch(1); t_layout.addWidget(self.theme_btn); t_layout.addWidget(self.framework_chip); t_layout.addWidget(self.clock_chip)

        self.stack = QStackedWidget()
        self.stack.addWidget(Dashboard())
        self.stack.addWidget(FileManager())
        self.stack.addWidget(NodeMonitor())
        self.stack.addWidget(AnalyticsPage())
        self.stack.addWidget(LogsPage())

        content_layout.addWidget(top)
        content_layout.addWidget(self.stack, 1)
        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)

        self.nav.currentRowChanged.connect(self.on_nav_changed)
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.statusBar().showMessage('DFS UI ready')

        self.clock = QTimer(self)
        self.clock.timeout.connect(self.update_clock)
        self.clock.start(1000)
        self.update_clock()
        self.on_nav_changed(0)

    def update_clock(self):
        self.clock_chip.setText(datetime.now().strftime('%d %b %Y  |  %I:%M:%S %p'))

    def toggle_theme(self):
        self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        app = QApplication.instance()
        app.setStyleSheet(LIGHT_THEME if self.current_theme == 'light' else DARK_THEME)
        self.theme_btn.setText('🌙 Dark Mode' if self.current_theme == 'light' else '☀ Light Mode')
        GUI_STATE.set_theme(self.current_theme)

    def on_nav_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        labels = [
            ('Dashboard', 'Cluster overview, health, and live metrics'),
            ('File Manager', 'Search, upload, download, and inspect files'),
            ('Nodes', 'Heartbeat monitoring and cluster node availability'),
            ('Analytics', 'Charts and short rolling trend analysis'),
            ('Logs', 'Recent GUI activity and cluster events'),
        ]
        title, subtitle = labels[index]
        self.section_title.setText(f'DFS Control Center • {title}')
        self.section_subtitle.setText(subtitle)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(DARK_THEME)
    window = DFSGui()
    window.show()
    sys.exit(app.exec_())
