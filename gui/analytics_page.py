from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame

from gui.shared_state import GUI_STATE


class ChartCard(QFrame):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        self.setObjectName('panel')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName('sectionTitle')
        sub = QLabel(subtitle)
        sub.setObjectName('smallMuted')
        sub.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(sub)


class SnapshotBarChart(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(240)
        GUI_STATE.stats_changed.connect(self.update)
        GUI_STATE.theme_changed.connect(lambda _: self.update())

    def paintEvent(self, _event):
        stats = GUI_STATE.current_stats
        is_dark = GUI_STATE.current_theme == 'dark'
        bars = [
            ('Files', stats.get('total_files', 0), QColor('#4f8cff')),
            ('Chunks', stats.get('total_chunks', 0), QColor('#27c4d9')),
            ('Active', stats.get('active_nodes', 0), QColor('#2ecc71')),
            ('Types', stats.get('file_types', 0), QColor('#f5a623')),
        ]
        max_value = max(1, max(v for _, v, _ in bars))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        grid = QColor('#1e3553' if is_dark else '#d7e2f2')
        text = QColor('#d9e4f2' if is_dark else '#314056')
        value_text = QColor('#ffffff' if is_dark else '#16253a')

        rect = self.rect().adjusted(22, 20, -22, -36)
        painter.setPen(QPen(grid, 1))
        for i in range(1, 5):
            y = rect.bottom() - rect.height() * i / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        slot_w = rect.width() / len(bars)
        bar_w = min(64, slot_w * 0.34)

        label_font = QFont('Segoe UI', 9)
        value_font = QFont('Segoe UI', 11)
        value_font.setBold(True)

        for idx, (label, value, color) in enumerate(bars):
            center_x = rect.left() + slot_w * idx + slot_w / 2
            usable_h = rect.height() - 12
            bar_h = max(14, (value / max_value) * usable_h)
            x = center_x - bar_w / 2
            y = rect.bottom() - bar_h
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 12, 12)
            painter.setPen(value_text)
            painter.setFont(value_font)
            painter.drawText(QRectF(x - 12, y - 28, bar_w + 24, 24), Qt.AlignCenter, str(value))
            painter.setPen(text)
            painter.setFont(label_font)
            painter.drawText(QRectF(x - 20, rect.bottom() + 8, bar_w + 40, 20), Qt.AlignCenter, label)


class TrendLineChart(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(240)
        GUI_STATE.stats_changed.connect(self.update)
        GUI_STATE.theme_changed.connect(lambda _: self.update())

    def paintEvent(self, _event):
        history = list(GUI_STATE.history)[-12:]
        is_dark = GUI_STATE.current_theme == 'dark'
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        rect = self.rect().adjusted(22, 20, -22, -44)
        grid = QColor('#1e3553' if is_dark else '#d7e2f2')
        muted = QColor('#d9e4f2' if is_dark else '#314056')
        painter.setPen(QPen(grid, 1))
        for i in range(1, 5):
            y = rect.bottom() - rect.height() * i / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        if len(history) < 2:
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignCenter, 'Waiting for more refresh history...')
            return

        max_y = max(1, max(max(item.get('total_files', 0), item.get('total_chunks', 0), item.get('active_nodes', 0)) for item in history))

        def line_path(key: str):
            path = QPainterPath()
            for i, item in enumerate(history):
                x = rect.left() + rect.width() * i / max(1, len(history) - 1)
                y = rect.bottom() - rect.height() * item.get(key, 0) / max_y
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            return path

        series = [
            ('total_files', QColor('#4f8cff'), 'Files'),
            ('total_chunks', QColor('#27c4d9'), 'Chunks'),
            ('active_nodes', QColor('#2ecc71'), 'Active Nodes'),
        ]
        for key, color, _ in series:
            painter.setPen(QPen(color, 3))
            painter.drawPath(line_path(key))

        painter.setFont(QFont('Segoe UI', 9))
        x = rect.left()
        for _, color, label in series:
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, rect.bottom() + 12, 12, 12), 4, 4)
            painter.setPen(muted)
            painter.drawText(QRectF(x + 18, rect.bottom() + 5, 92, 24), Qt.AlignVCenter, label)
            x += 120


class AnalyticsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        hero = QFrame()
        hero.setObjectName('heroPanel')
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        badge = QLabel('ANALYTICS & CHARTS')
        badge.setObjectName('microLabel')
        title = QLabel('Analytics')
        title.setObjectName('pageTitle')
        subtitle = QLabel('Visual metrics for files, chunks, node availability, and short rolling trends.')
        subtitle.setObjectName('pageSubtitle')
        subtitle.setWordWrap(True)
        hero_layout.addWidget(badge, alignment=Qt.AlignLeft)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        row = QHBoxLayout()
        row.setSpacing(18)
        left = ChartCard('Current Snapshot', 'Live values built from the most recent GUI refresh data.')
        left.layout().addWidget(SnapshotBarChart())
        right = ChartCard('Recent Trend', 'Short history of recent refresh cycles captured in the GUI.')
        right.layout().addWidget(TrendLineChart())
        row.addWidget(left, 1)
        row.addWidget(right, 1)
        root.addLayout(row)
        root.addStretch(1)
