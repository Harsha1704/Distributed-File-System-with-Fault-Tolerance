from __future__ import annotations

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QScrollArea,
)

from gui.shared_state import GUI_STATE


class ChartCard(QFrame):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        self.setObjectName("panel")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(18, 18, 18, 18)
        self.main_layout.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("sectionTitle")

        sub = QLabel(subtitle)
        sub.setObjectName("smallMuted")
        sub.setWordWrap(True)

        self.main_layout.addWidget(heading)
        self.main_layout.addWidget(sub)

    def add_content(self, widget: QWidget, stretch: int = 0):
        self.main_layout.addWidget(widget, stretch)


class SnapshotBarChart(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(280)
        self.setMaximumHeight(340)
        GUI_STATE.stats_changed.connect(self.update)
        GUI_STATE.theme_changed.connect(lambda _: self.update())

    def paintEvent(self, _event):
        stats = GUI_STATE.current_stats
        is_dark = GUI_STATE.current_theme == "dark"

        bars = [
            ("Files", stats.get("total_files", 0), QColor("#4f8cff")),
            ("Chunks", stats.get("total_chunks", 0), QColor("#27c4d9")),
            ("Active", stats.get("active_nodes", 0), QColor("#2ecc71")),
            ("Types", stats.get("file_types", 0), QColor("#f5a623")),
        ]

        max_value = max(1, max(v for _, v, _ in bars))

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        grid = QColor("#1e3553" if is_dark else "#d7e2f2")
        text = QColor("#d9e4f2" if is_dark else "#314056")
        value_text = QColor("#ffffff" if is_dark else "#16253a")

        rect = self.rect().adjusted(26, 20, -26, -48)

        painter.setPen(QPen(grid, 1))
        for i in range(1, 5):
            y = rect.bottom() - rect.height() * i / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        slot_w = rect.width() / len(bars)
        bar_w = min(72, slot_w * 0.34)

        label_font = QFont("Segoe UI", 10)
        value_font = QFont("Segoe UI", 12)
        value_font.setBold(True)

        for idx, (label, value, color) in enumerate(bars):
            center_x = rect.left() + slot_w * idx + slot_w / 2
            usable_h = rect.height() - 20
            bar_h = max(16, (value / max_value) * usable_h)
            x = center_x - bar_w / 2
            y = rect.bottom() - bar_h

            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 12, 12)

            painter.setPen(value_text)
            painter.setFont(value_font)
            painter.drawText(QRectF(x - 16, y - 30, bar_w + 32, 24), Qt.AlignCenter, str(value))

            painter.setPen(text)
            painter.setFont(label_font)
            painter.drawText(QRectF(x - 24, rect.bottom() + 10, bar_w + 48, 24), Qt.AlignCenter, label)


class TrendLineChart(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(280)
        self.setMaximumHeight(340)
        GUI_STATE.stats_changed.connect(self.update)
        GUI_STATE.theme_changed.connect(lambda _: self.update())

    def _build_path(self, rect: QRectF, history: list[dict], key: str, max_y: int):
        points = []
        for i, item in enumerate(history):
            x = rect.left() + rect.width() * i / max(1, len(history) - 1)
            y = rect.bottom() - rect.height() * item.get(key, 0) / max_y
            points.append(QPointF(x, y))

        path = QPainterPath()
        if points:
            path.moveTo(points[0])
            for p in points[1:]:
                path.lineTo(p)
        return path, points

    def paintEvent(self, _event):
        history = list(GUI_STATE.history)[-20:]
        is_dark = GUI_STATE.current_theme == "dark"

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        rect = self.rect().adjusted(26, 20, -26, -54)
        grid = QColor("#1e3553" if is_dark else "#d7e2f2")
        muted = QColor("#d9e4f2" if is_dark else "#314056")

        painter.setPen(QPen(grid, 1))
        for i in range(1, 5):
            y = rect.bottom() - rect.height() * i / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        if len(history) < 2:
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignCenter, "Waiting for more refresh history...")
            return

        max_y = max(
            1,
            max(
                max(
                    item.get("total_files", 0),
                    item.get("total_chunks", 0),
                    item.get("active_nodes", 0),
                )
                for item in history
            ),
        )

        series = [
            ("total_files", QColor("#4f8cff"), "Files"),
            ("total_chunks", QColor("#27c4d9"), "Chunks"),
            ("active_nodes", QColor("#2ecc71"), "Active Nodes"),
        ]

        for key, color, _ in series:
            path, points = self._build_path(rect, history, key, max_y)

            fill_path = QPainterPath(path)
            if points:
                fill_path.lineTo(points[-1].x(), rect.bottom())
                fill_path.lineTo(points[0].x(), rect.bottom())
                fill_path.closeSubpath()

                soft = QColor(color)
                soft.setAlpha(35)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(soft))
                painter.drawPath(fill_path)

            painter.setPen(QPen(color, 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            for p in points:
                painter.drawEllipse(p, 3.5, 3.5)

        painter.setFont(QFont("Segoe UI", 9))
        x = rect.left()
        legend_y = rect.bottom() + 12
        for _, color, label in series:
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, legend_y, 12, 12), 4, 4)
            painter.setPen(muted)
            painter.drawText(QRectF(x + 18, legend_y - 4, 100, 22), Qt.AlignVCenter, label)
            x += 126


class FileChunkDistributionChart(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(280)
        self.setMaximumHeight(350)
        GUI_STATE.files_changed.connect(lambda _: self.update())
        GUI_STATE.theme_changed.connect(lambda _: self.update())

    def paintEvent(self, _event):
        files = list(GUI_STATE.current_files)
        is_dark = GUI_STATE.current_theme == "dark"

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        rect = self.rect().adjusted(26, 20, -26, -54)
        grid = QColor("#1e3553" if is_dark else "#d7e2f2")
        text = QColor("#d9e4f2" if is_dark else "#314056")
        value_text = QColor("#ffffff" if is_dark else "#16253a")

        painter.setPen(QPen(grid, 1))
        for i in range(1, 5):
            y = rect.bottom() - rect.height() * i / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        if not files:
            painter.setPen(text)
            painter.drawText(rect, Qt.AlignCenter, "Upload files to visualize chunk distribution.")
            return

        files = sorted(files, key=lambda f: int(f.get("num_chunks", 0) or 0), reverse=True)[:6]
        counts = [(f.get("filename", "Unknown"), int(f.get("num_chunks", 0) or 0)) for f in files]
        max_value = max(1, max(v for _, v in counts))

        slot_w = rect.width() / len(counts)
        bar_w = min(62, slot_w * 0.46)
        colors = ["#4f8cff", "#27c4d9", "#2ecc71", "#f5a623", "#ff7b72", "#9b5cff"]

        label_font = QFont("Segoe UI", 8)
        value_font = QFont("Segoe UI", 10)
        value_font.setBold(True)

        for idx, (label, value) in enumerate(counts):
            center_x = rect.left() + slot_w * idx + slot_w / 2
            usable_h = rect.height() - 16
            bar_h = max(14, (value / max_value) * usable_h)
            x = center_x - bar_w / 2
            y = rect.bottom() - bar_h

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(colors[idx % len(colors)]))
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 10, 10)

            painter.setPen(value_text)
            painter.setFont(value_font)
            painter.drawText(QRectF(x - 12, y - 24, bar_w + 24, 20), Qt.AlignCenter, str(value))

            short = label if len(label) <= 12 else label[:9] + "..."
            painter.setPen(text)
            painter.setFont(label_font)
            painter.drawText(QRectF(x - 28, rect.bottom() + 10, bar_w + 56, 26), Qt.AlignCenter, short)


class NodeLoadBalanceChart(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(300)
        self.setMaximumHeight(380)
        GUI_STATE.files_changed.connect(lambda _: self.update())
        GUI_STATE.nodes_changed.connect(lambda _: self.update())
        GUI_STATE.theme_changed.connect(lambda _: self.update())

    def paintEvent(self, _event):
        counts, mode = GUI_STATE.compute_node_chunk_loads()
        is_dark = GUI_STATE.current_theme == "dark"

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        rect = self.rect().adjusted(26, 22, -26, -26)
        text = QColor("#d9e4f2" if is_dark else "#314056")
        value_text = QColor("#ffffff" if is_dark else "#16253a")
        track = QColor("#18304c" if is_dark else "#dfe8f5")
        fill = QColor("#27c4d9")

        if not counts:
            painter.setPen(text)
            painter.drawText(rect, Qt.AlignCenter, "No node load data available.")
            return

        if mode == "actual":
            mode_text = "Actual chunk placement from metadata"
        else:
            mode_text = "Estimated balanced spread from visible chunks"

        painter.setPen(text)
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(QRectF(rect.left(), rect.top(), rect.width(), 24), Qt.AlignLeft, mode_text)

        max_value = max(1, max(counts.values()))
        start_y = rect.top() + 50
        row_gap = 56

        for idx, node_id in enumerate(sorted(counts)):
            y = start_y + idx * row_gap

            painter.setPen(text)
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(QRectF(rect.left(), y, 96, 24), Qt.AlignLeft, f"Node {node_id}")

            bar_x = rect.left() + 100
            bar_y = y + 4
            bar_w = rect.width() - 170
            bar_h = 20

            painter.setPen(Qt.NoPen)
            painter.setBrush(track)
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 10, 10)

            fill_w = 0 if counts[node_id] <= 0 else max(14, bar_w * counts[node_id] / max_value)
            painter.setBrush(fill)
            painter.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 10, 10)

            painter.setPen(value_text)
            painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
            painter.drawText(QRectF(bar_x + bar_w + 10, y, 46, 24), Qt.AlignLeft, str(counts[node_id]))


class PerFileChunkTable(QTableWidget):
    def __init__(self):
        super().__init__(0, 4)
        self.setHorizontalHeaderLabels(["Filename", "Chunks", "Chunk Profile", "Type"])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)

        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumHeight(300)

        GUI_STATE.files_changed.connect(self.refresh_data)
        self.refresh_data()

    @staticmethod
    def _infer_type(filename: str) -> str:
        parts = filename.rsplit(".", 1)
        return parts[-1].upper() if len(parts) == 2 else "FILE"

    def refresh_data(self, _files=None):
        files = sorted(
            list(GUI_STATE.current_files),
            key=lambda f: int(f.get("num_chunks", 0) or 0),
            reverse=True,
        )

        self.setRowCount(len(files))
        for row, file_obj in enumerate(files):
            name = file_obj.get("filename", "Unknown")
            chunks = int(file_obj.get("num_chunks", 0) or 0)
            profile = "Multi-chunk" if chunks > 1 else "Single chunk"
            values = [name, str(chunks), profile, self._infer_type(name)]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if col == 0 else Qt.AlignCenter))
                self.setItem(row, col, item)


class AnalyticsPage(QWidget):
    def __init__(self):
        super().__init__()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(8)

        badge = QLabel("ANALYTICS & CHARTS")
        badge.setObjectName("microLabel")

        title = QLabel("Analytics")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Visual metrics for files, chunks, chunk distribution, node balancing, and short rolling trends.")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        hero_layout.addWidget(badge, alignment=Qt.AlignLeft)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        row1 = QHBoxLayout()
        row1.setSpacing(18)

        snapshot_card = ChartCard("Current Snapshot", "Live values built from the most recent GUI refresh data.")
        snapshot_card.add_content(SnapshotBarChart())

        trend_card = ChartCard("Recent Trend", "Short history of recent refresh cycles captured in the GUI.")
        trend_card.add_content(TrendLineChart())

        row1.addWidget(snapshot_card, 1)
        row1.addWidget(trend_card, 1)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(18)

        distribution_card = ChartCard("Chunk Distribution by File", "Bar chart showing how many chunks each visible file uses.")
        distribution_card.add_content(FileChunkDistributionChart())

        load_card = ChartCard("Real-Time Chunk Load Balancing", "Node chunk load view using actual placement when available or an estimated balanced spread otherwise.")
        load_card.add_content(NodeLoadBalanceChart())

        row2.addWidget(distribution_card, 1)
        row2.addWidget(load_card, 1)
        root.addLayout(row2)

        table_card = ChartCard("Per-File Chunk View", "Inspection view for chunk-heavy files, single-chunk files, and file types.")
        table_card.add_content(PerFileChunkTable(), 1)
        root.addWidget(table_card)

        root.addStretch(1)

        scroll.setWidget(container)
        outer.addWidget(scroll)