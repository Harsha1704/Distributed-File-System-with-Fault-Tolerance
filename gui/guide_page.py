from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QGridLayout,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)

from gui.shared_state import GUI_STATE


class InfoCard(QFrame):
    def __init__(self, title: str, value: str, description: str):
        super().__init__()
        self.setObjectName("softPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        lbl = QLabel(title)
        lbl.setObjectName("statTitle")

        self.value = QLabel(value)
        self.value.setObjectName("smallValue")

        self.desc = QLabel(description)
        self.desc.setObjectName("smallMuted")
        self.desc.setWordWrap(True)

        layout.addWidget(lbl)
        layout.addWidget(self.value)
        layout.addWidget(self.desc)


class SectionCard(QFrame):
    def __init__(self, title: str, text: str):
        super().__init__()
        self.setObjectName("panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("sectionTitle")

        body = QLabel(text)
        body.setObjectName("smallMuted")
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(heading)
        layout.addWidget(body)


class LiveOverviewCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("panel")

        layout = QGridLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(12)

        title = QLabel("Live System Context")
        title.setObjectName("sectionTitle")

        subtitle = QLabel(
            "This guide is connected to the running DFS state so you can explain "
            "the architecture and the live system together."
        )
        subtitle.setObjectName("smallMuted")
        subtitle.setWordWrap(True)

        layout.addWidget(title, 0, 0, 1, 4)
        layout.addWidget(subtitle, 1, 0, 1, 4)

        self.master = self._metric("Master", "Online")
        self.nodes = self._metric("Active Nodes", "--")
        self.files = self._metric("Files", "--")
        self.chunks = self._metric("Chunks", "--")

        layout.addWidget(self.master, 2, 0)
        layout.addWidget(self.nodes, 2, 1)
        layout.addWidget(self.files, 2, 2)
        layout.addWidget(self.chunks, 2, 3)

        GUI_STATE.stats_changed.connect(self.refresh)
        self.refresh()

    def _metric(self, title: str, value: str):
        card = QFrame()
        card.setObjectName("softPanel")

        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(4)

        t = QLabel(title)
        t.setObjectName("statTitle")

        val = QLabel(value)
        val.setObjectName("smallValue")

        v.addWidget(t)
        v.addWidget(val)

        card.value_label = val
        return card

    def refresh(self, *_):
        stats = GUI_STATE.current_stats
        total_nodes = int(stats.get("total_nodes", 3) or 3)
        active_nodes = int(stats.get("active_nodes", 0) or 0)

        self.master.value_label.setText("Online" if stats.get("master_online", True) else "Offline")
        self.nodes.value_label.setText(f"{active_nodes}/{total_nodes}")
        self.files.value_label.setText(str(int(stats.get("total_files", 0) or 0)))
        self.chunks.value_label.setText(str(int(stats.get("total_chunks", 0) or 0)))


class AnimatedFlowWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(220)
        self.setMaximumHeight(250)

        self.steps = [
            ("Upload", QColor("#4f8cff")),
            ("Chunking", QColor("#27c4d9")),
            ("Metadata", QColor("#9b5cff")),
            ("Nodes", QColor("#2ecc71")),
            ("Monitoring", QColor("#f5a623")),
            ("Recovery", QColor("#ff7b72")),
        ]

        self.phase = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(40)

        GUI_STATE.theme_changed.connect(self.on_theme_changed)
        self.destroyed.connect(self.cleanup_connections)

    def on_theme_changed(self, *_):
        if self is not None:
            self.update()

    def cleanup_connections(self, *_):
        try:
            GUI_STATE.theme_changed.disconnect(self.on_theme_changed)
        except Exception:
            pass

    def advance(self):
        self.phase += 0.015
        if self.phase > len(self.steps) - 1:
            self.phase = 0.0
        self.update()

    def paintEvent(self, _event):
        is_dark = GUI_STATE.current_theme == "dark"

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(40, 28, -40, -30)

        line_color = QColor("#2f5b96" if is_dark else "#c4d5ef")
        text_color = QColor("#ecf4ff" if is_dark else "#18304c")
        dot_color = QColor("#ffffff" if is_dark else "#18304c")
        glow_color = QColor("#7dd3fc" if is_dark else "#2563eb")

        y = rect.center().y() + 18
        count = len(self.steps)
        points = []

        for i in range(count):
            x = rect.left() + i * rect.width() / max(1, count - 1)
            points.append(QPointF(x, y))

        painter.setPen(QPen(line_color, 3))
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        chip_font = QFont("Segoe UI", 11)
        chip_font.setBold(True)
        painter.setFont(chip_font)

        chip_w = 110
        chip_h = 46

        for (label, color), p in zip(self.steps, points):
            chip = QRectF(p.x() - chip_w / 2, p.y() - 24, chip_w, chip_h)

            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(chip, 14, 14)

            painter.setPen(text_color if color.lightness() > 150 else QColor("#ffffff"))
            painter.drawText(chip, Qt.AlignCenter, label)

        seg = int(self.phase)
        local = self.phase - seg
        if seg >= len(points) - 1:
            seg = len(points) - 2
            local = 1.0

        x = points[seg].x() + (points[seg + 1].x() - points[seg].x()) * local
        active = QPointF(x, y)

        painter.setPen(Qt.NoPen)

        glow = QColor(glow_color)
        glow.setAlpha(90)
        painter.setBrush(glow)
        painter.drawEllipse(active, 12, 12)

        painter.setBrush(dot_color)
        painter.drawEllipse(active, 6, 6)


class ModuleButton(QPushButton):
    def __init__(self, key: str, title: str, subtitle: str, color: str):
        super().__init__(f"{title}\n{subtitle}")
        self.key = key
        self.color = color
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(84)
        self.refresh_style(False)

    def refresh_style(self, active: bool):
        accent = self.color
        if active:
            self.setStyleSheet(
                f"QPushButton {{"
                f"background: rgba(79,140,255,0.10);"
                f"border: 2px solid {accent};"
                f"border-radius: 16px;"
                f"padding: 14px;"
                f"text-align: left;"
                f"font-weight: 800;"
                f"font-size: 15px;"
                f"}}"
            )
        else:
            self.setStyleSheet(
                f"QPushButton {{"
                f"background: transparent;"
                f"border: 1px solid #294364;"
                f"border-radius: 16px;"
                f"padding: 14px;"
                f"text-align: left;"
                f"font-weight: 800;"
                f"font-size: 15px;"
                f"}}"
                f"QPushButton:hover {{"
                f"border: 1px solid {accent};"
                f"background: rgba(79,140,255,0.06);"
                f"}}"
            )


class ModuleDetailsCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Selected Module Details")
        title.setObjectName("sectionTitle")

        self.name = QLabel("GUI Control Center")
        self.name.setObjectName("sectionTitle")

        self.path = QLabel("Location: gui/main_gui.py, dashboard.py, file_manager.py, node_monitor.py")
        self.path.setObjectName("smallMuted")
        self.path.setWordWrap(True)

        self.desc = QLabel(
            "The GUI acts as the user-facing control panel for operating and "
            "explaining the distributed file system."
        )
        self.desc.setObjectName("smallMuted")
        self.desc.setWordWrap(True)

        self.points = QLabel(
            "• Shows dashboard status and file operations\n"
            "• Displays node health and logs\n"
            "• Provides a guided explanation page\n"
            "• Connects user actions to backend services"
        )
        self.points.setObjectName("smallMuted")
        self.points.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.name)
        layout.addWidget(self.path)
        layout.addWidget(self.desc)
        layout.addWidget(self.points)
        layout.addStretch(1)

    def set_data(self, data: dict):
        self.name.setText(data["title"])
        self.path.setText(f"Location: {data['location']}")
        self.desc.setText(data["description"])
        self.points.setText("\n".join(f"• {p}" for p in data["points"]))


class ModuleTable(QTableWidget):
    def __init__(self):
        super().__init__(0, 3)
        self.setHorizontalHeaderLabels(["Module / File", "Location", "Purpose"])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)

        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        rows = [
            ("Master Server", "master/master.py", "Central coordinator that handles upload plans, downloads, listing, delete requests, and node status."),
            ("Metadata Manager", "master/metadata_manager.py", "Stores persistent file metadata, chunk metadata, replica nodes, and upload state."),
            ("Node Manager", "master/node_manager.py", "Tracks heartbeats, node liveness, registration, and live node selection."),
            ("Replication Manager", "master/replication_manager.py", "Detects under-replicated chunks and attempts re-replication after failures."),
            ("Storage Node", "nodes/node.py", "Stores chunk files on disk, serves chunk fetch/store/delete requests, and sends heartbeats."),
            ("Dashboard", "gui/dashboard.py", "Shows files, chunks, active nodes, cluster health, and overview information."),
            ("File Manager", "gui/file_manager.py", "Supports upload, download, delete, search, and selected file inspection."),
            ("Node Monitor", "gui/node_monitor.py", "Displays live node state, heartbeat visibility, and cluster node summary."),
            ("Analytics", "gui/analytics_page.py", "Shows charts, chunk distribution, load balancing, and per-file chunk inspection."),
            ("Logs", "gui/logs_page.py", "Displays recent GUI-side monitoring and user activity logs."),
            ("Shared State", "gui/shared_state.py", "Maintains shared GUI metrics, logs, theme state, history, and analytics data."),
            ("Chunking", "common/chunking.py", "Splits files into chunks and merges chunks back into full files."),
            ("Hashing", "common/hashing.py", "Provides SHA-256 hashing and integrity verification for files and chunks."),
            ("Utilities", "common/utils.py", "Contains messaging, byte transfer helpers, logging, and filesystem utilities."),
            ("Run Script", "run.bat", "Starts master, nodes, and GUI together for the full DFS demo."),
            ("Metadata File", "master/metadata.json", "Persistent record of files, chunks, chunk indexes, hashes, and replica assignments."),
            ("Node Storage", "nodes/storage/node1..3", "Physical storage directories where chunk files are written on each node."),
            ("Logs Folder", "logs/", "Stores runtime logs for master and node processes."),
            ("Downloads Folder", "downloads/", "Stores reconstructed downloaded files on the client side."),
        ]

        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if c != 1 else Qt.AlignCenter))
                self.setItem(r, c, item)


class GuidePage(QWidget):
    MODULES = {
        "master": {
            "title": "Master Server",
            "location": "master/master.py",
            "description": "The master is the coordinator of the distributed file system. It receives client requests, allocates nodes for chunk replicas, answers file listing requests, and provides cluster status.",
            "points": [
                "Coordinates upload, download, delete, and list operations",
                "Tracks live storage nodes through node manager",
                "Reads and updates metadata through metadata manager",
                "Starts replication health monitoring",
            ],
            "color": "#ff7b72",
        },
        "metadata": {
            "title": "Metadata Manager",
            "location": "master/metadata_manager.py",
            "description": "This module persists file metadata, chunk indexes, chunk hashes, and replica node assignments. It is the backbone of file reconstruction and replica awareness.",
            "points": [
                "Stores file records and chunk records",
                "Tracks replica node IDs per chunk",
                "Supports download reconstruction order",
                "Persists metadata to metadata.json",
            ],
            "color": "#9b5cff",
        },
        "nodes": {
            "title": "Storage Nodes",
            "location": "nodes/node.py and nodes/storage/",
            "description": "Storage nodes physically store chunk files and answer chunk fetch, store, and delete requests. They also send heartbeats to the master so failures can be detected.",
            "points": [
                "Stores chunk files on disk",
                "Serves chunk data back to clients",
                "Sends heartbeat messages periodically",
                "Represents the distributed storage layer",
            ],
            "color": "#2ecc71",
        },
        "replication": {
            "title": "Replication Manager",
            "location": "master/replication_manager.py",
            "description": "The replication manager checks whether chunk replicas still satisfy the configured replication factor and attempts repair when spare healthy nodes are available.",
            "points": [
                "Detects under-replicated chunks",
                "Chooses healthy spare nodes when possible",
                "Supports graceful failure handling",
                "Maintains availability policy",
            ],
            "color": "#4f8cff",
        },
        "gui": {
            "title": "GUI Control Center",
            "location": "gui/main_gui.py, dashboard.py, file_manager.py, node_monitor.py",
            "description": "The GUI is the user-facing control panel for monitoring, file operations, analytics, logs, and project explanation. It is also useful in demo and viva.",
            "points": [
                "Shows dashboard status and file operations",
                "Displays node health and logs",
                "Provides a guided explanation page",
                "Connects user actions to backend services",
            ],
            "color": "#27c4d9",
        },
        "analytics": {
            "title": "Analytics",
            "location": "gui/analytics_page.py",
            "description": "Analytics transforms raw DFS state into charts and inspection views so chunk-heavy files, active nodes, and balancing patterns can be explained visually.",
            "points": [
                "Shows current snapshot charts",
                "Displays chunk distribution by file",
                "Shows estimated or actual chunk load view",
                "Provides per-file chunk table",
            ],
            "color": "#f5a623",
        },
    }

    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
        QLabel { font-size: 15px; }
        QPushButton { font-size: 15px; padding: 10px 16px; }
        QTableWidget { font-size: 14px; }
        """)

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

        badge = QLabel("SYSTEM GUIDE")
        badge.setObjectName("microLabel")

        title = QLabel("Interactive Project Guide & Architecture Map")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Explore the architecture of the Distributed File System with Fault "
            "Tolerance. Click modules, follow the animated flow, and inspect "
            "where each file and subsystem belongs."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        hero_layout.addWidget(badge, alignment=Qt.AlignLeft)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        top_metrics = QHBoxLayout()
        top_metrics.setSpacing(18)
        top_metrics.addWidget(
            InfoCard("Project Type", "Distributed System", "A chunk-based distributed file storage and monitoring application.")
        )
        top_metrics.addWidget(
            InfoCard("Core Goal", "Fault Tolerance", "Ensures file availability and integrity across multiple nodes during failures.")
        )
        top_metrics.addWidget(
            InfoCard("Architecture", "Master + Nodes + GUI", "Combines backend services with a modern monitoring and documentation interface.")
        )
        root.addLayout(top_metrics)

        root.addWidget(LiveOverviewCard())

        flow_card = QFrame()
        flow_card.setObjectName("panel")
        flow_layout = QVBoxLayout(flow_card)
        flow_layout.setContentsMargins(18, 18, 18, 18)
        flow_layout.setSpacing(8)

        flow_title = QLabel("Animated System Flow")
        flow_title.setObjectName("sectionTitle")

        flow_sub = QLabel(
            "This animation shows the typical DFS lifecycle: upload, chunking, "
            "metadata registration, node storage, monitoring, and recovery."
        )
        flow_sub.setObjectName("smallMuted")
        flow_sub.setWordWrap(True)

        flow_layout.addWidget(flow_title)
        flow_layout.addWidget(flow_sub)
        flow_layout.addWidget(AnimatedFlowWidget())
        root.addWidget(flow_card)

        arch_row = QHBoxLayout()
        arch_row.setSpacing(18)

        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(12)

        left_title = QLabel("Clickable Architecture Diagram")
        left_title.setObjectName("sectionTitle")

        left_sub = QLabel(
            "Click any module below to view its role, file location, and how it "
            "connects to the rest of the system."
        )
        left_sub.setObjectName("smallMuted")
        left_sub.setWordWrap(True)

        left_layout.addWidget(left_title)
        left_layout.addWidget(left_sub)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self.buttons = {}
        button_specs = [
            ("master", "🧠 Master Server", "Coordinator planning"),
            ("metadata", "🗂 Metadata Manager", "File / chunk records"),
            ("nodes", "🗄 Storage Nodes", "Chunk storage replicas"),
            ("replication", "🔁 Replication Manager", "Replica repair logic"),
            ("gui", "🖥 GUI Control Center", "Dashboard operations"),
            ("analytics", "📈 Analytics", "Charts monitoring"),
        ]
        positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]

        for (key, title_txt, sub_txt), (r, c) in zip(button_specs, positions):
            btn = ModuleButton(key, title_txt, sub_txt, self.MODULES[key]["color"])
            btn.clicked.connect(lambda checked=False, k=key: self.select_module(k))
            self.buttons[key] = btn
            grid.addWidget(btn, r, c)

        left_layout.addLayout(grid)
        arch_row.addWidget(left, 3)

        self.details = ModuleDetailsCard()
        arch_row.addWidget(self.details, 2)
        root.addLayout(arch_row)

        row1 = QHBoxLayout()
        row1.setSpacing(18)
        row1.addWidget(
            SectionCard(
                "What This Project Does",
                "This project implements a Distributed File System with Fault Tolerance. "
                "When a file is uploaded, it is split into chunks and distributed across "
                "multiple storage nodes. Each chunk can be replicated on more than one "
                "node to improve availability. The master server maintains metadata, "
                "tracks node health through heartbeat messages, and coordinates file "
                "upload, download, and monitoring operations.",
            ),
            1,
        )
        row1.addWidget(
            SectionCard(
                "Fault Tolerance Workflow",
                "Each storage node sends heartbeat messages to the master. If a node stops "
                "responding, the node manager marks it as unavailable. The replication "
                "manager checks whether each chunk still satisfies the replication policy. "
                "If enough healthy nodes exist, missing replicas can be recreated. This "
                "allows the system to handle node failures gracefully while preserving availability.",
            ),
            1,
        )
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(18)
        row2.addWidget(
            SectionCard(
                "Data Flow",
                "Upload Flow: User selects a file → file is split into chunks → master assigns replica nodes → nodes store chunk files → metadata is updated.\n\n"
                "Download Flow: User requests a file → master returns ordered chunk locations → client fetches chunks → chunks are merged → file hash can be verified.\n\n"
                "Monitoring Flow: GUI requests file list and node status from the master → dashboard, analytics, and logs update live.",
            ),
            1,
        )
        row2.addWidget(
            SectionCard(
                "Integrity and Availability",
                "Integrity is maintained using SHA-256 hashes for files and chunks. A chunk "
                "is verified before it is stored on a node. Availability is supported by "
                "replication, multiple storage nodes, and node monitoring. Chunk metadata "
                "records which nodes store which chunk, allowing the system to locate "
                "available replicas during reads.",
            ),
            1,
        )
        root.addLayout(row2)

        root.addWidget(
            SectionCard(
                "Failure Simulation Explanation",
                "Example: If one node stops sending heartbeat messages, the master marks it "
                "as unavailable. The GUI then shows fewer active nodes. Chunk availability "
                "is evaluated against the replication policy. If extra healthy nodes exist, "
                "the replication manager can repair missing replicas. If not, the system "
                "enters a degraded but still explainable state depending on remaining replicas.",
            )
        )

        root.addWidget(
            SectionCard(
                "Key Features",
                "✔ Chunk-based file storage\n"
                "✔ Multi-node replication\n"
                "✔ Heartbeat-based node monitoring\n"
                "✔ Fault tolerance and degraded-state handling\n"
                "✔ SHA-256 integrity verification\n"
                "✔ Dashboard, analytics, logs, and system guide in one GUI",
            )
        )

        root.addWidget(
            SectionCard(
                "Why This Project Is Important",
                "This project demonstrates the core ideas behind large-scale distributed "
                "storage systems such as Google File System and HDFS: chunk-based storage, "
                "metadata tracking, redundancy, failure detection, and recovery-oriented design.",
            )
        )

        table_card = QFrame()
        table_card.setObjectName("panel")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(18, 18, 18, 18)
        table_layout.setSpacing(8)

        table_title = QLabel("File and Module Location Map")
        table_title.setObjectName("sectionTitle")

        table_sub = QLabel(
            "This table explains where each major file is located in the project and what role it plays in the DFS."
        )
        table_sub.setObjectName("smallMuted")
        table_sub.setWordWrap(True)

        table_layout.addWidget(table_title)
        table_layout.addWidget(table_sub)

        module_table = ModuleTable()
        module_table.setMinimumHeight(420)
        table_layout.addWidget(module_table)
        root.addWidget(table_card)

        root.addWidget(
            SectionCard(
                "How to Run the Project",
                "Use run.bat to start the full system. It launches the master server, "
                "three storage nodes, and the GUI. Use run.bat stop to close all DFS "
                "windows. The logs folder stores backend logs, and the downloads folder "
                "stores reconstructed downloaded files.",
            )
        )

        root.addWidget(
            SectionCard(
                "How to Explain This Project in Viva",
                "You can explain that this project is a distributed file system that "
                "splits files into chunks, stores replicas across multiple nodes, tracks "
                "node health through heartbeats, and uses metadata to maintain file "
                "availability and integrity. The GUI acts as a control center for "
                "monitoring files, chunks, nodes, trends, logs, and architecture.",
            )
        )

        root.addStretch(1)
        scroll.setWidget(container)
        outer.addWidget(scroll)

        self.select_module("gui")

    def select_module(self, key: str):
        for module_key, button in self.buttons.items():
            active = module_key == key
            button.setChecked(active)
            button.refresh_style(active)
        self.details.set_data(self.MODULES[key])