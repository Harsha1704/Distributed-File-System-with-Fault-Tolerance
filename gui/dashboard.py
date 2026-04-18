import socket
from PyQt5.QtCore import QDateTime, QTimer, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout

from client.config import MASTER_HOST, MASTER_PORT
from common.utils import send_message, recv_message
from gui.shared_state import GUI_STATE


class StatCard(QFrame):
    def __init__(self, title: str, icon: str):
        super().__init__()
        self.setObjectName('card')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)
        self.title = QLabel(f'{icon}  {title}')
        self.title.setObjectName('statTitle')
        self.value = QLabel('--')
        self.value.setObjectName('statValue')
        self.meta = QLabel('Waiting for data')
        self.meta.setObjectName('statMeta')
        self.meta.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.meta)

    def set_data(self, value: str, meta: str):
        self.value.setText(value)
        self.meta.setText(meta)


class MiniMetric(QFrame):
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


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.last_health = None
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        hero = QFrame()
        hero.setObjectName('heroPanel')
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        badge = QLabel('LIVE STATUS')
        badge.setObjectName('microLabel')
        title = QLabel('Distributed File System Dashboard')
        title.setObjectName('pageTitle')
        subtitle = QLabel('Operational overview of files, chunks, node health, cluster status, and master connectivity.')
        subtitle.setObjectName('pageSubtitle')
        subtitle.setWordWrap(True)
        hero_layout.addWidget(badge, alignment=Qt.AlignLeft)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        grid = QGridLayout()
        grid.setSpacing(18)
        self.files_card = StatCard('Total Files', '📁')
        self.chunks_card = StatCard('Total Chunks', '🧩')
        self.nodes_card = StatCard('Active Nodes', '🟢')
        self.health_card = StatCard('Cluster Health', '🛡️')
        grid.addWidget(self.files_card, 0, 0)
        grid.addWidget(self.chunks_card, 0, 1)
        grid.addWidget(self.nodes_card, 1, 0)
        grid.addWidget(self.health_card, 1, 1)
        root.addLayout(grid)

        mini = QHBoxLayout()
        mini.setSpacing(18)
        self.avg_card = MiniMetric('Average Chunks / File')
        self.split_card = MiniMetric('Multi-Chunk Files')
        self.master_card = MiniMetric('Master State')
        mini.addWidget(self.avg_card)
        mini.addWidget(self.split_card)
        mini.addWidget(self.master_card)
        root.addLayout(mini)

        bottom = QHBoxLayout()
        bottom.setSpacing(18)
        overview = QFrame()
        overview.setObjectName('panel')
        o_layout = QVBoxLayout(overview)
        o_layout.setContentsMargins(18, 18, 18, 18)
        title = QLabel('Overview')
        title.setObjectName('sectionTitle')
        self.overview_text = QLabel('Waiting for master data...')
        self.overview_text.setWordWrap(True)
        self.overview_text.setObjectName('smallMuted')
        o_layout.addWidget(title)
        o_layout.addWidget(self.overview_text)

        status = QFrame()
        status.setObjectName('panel')
        s_layout = QVBoxLayout(status)
        s_layout.setContentsMargins(18, 18, 18, 18)
        self.last_updated = QLabel('Last updated: --')
        self.last_updated.setObjectName('smallMuted')
        self.connection = QLabel('Connection: Checking')
        self.connection.setObjectName('statusBadge')
        self.connection.setProperty('state', 'warn')
        s_layout.addWidget(self.last_updated)
        s_layout.addWidget(self.connection, alignment=Qt.AlignLeft)
        s_layout.addStretch(1)

        bottom.addWidget(overview, 1)
        bottom.addWidget(status, 1)
        root.addLayout(bottom)
        root.addStretch(1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dashboard)
        self.timer.start(2000)
        self.update_dashboard()

    def _refresh_badge(self, state: str, text: str):
        self.connection.setText(text)
        self.connection.setProperty('state', state)
        self.connection.style().unpolish(self.connection)
        self.connection.style().polish(self.connection)

    def _fetch(self):
        sock = socket.socket(); sock.settimeout(3); sock.connect((MASTER_HOST, MASTER_PORT))
        send_message(sock, {'action': 'LIST_FILES'})
        files = recv_message(sock)
        sock.close()
        sock = socket.socket(); sock.settimeout(3); sock.connect((MASTER_HOST, MASTER_PORT))
        send_message(sock, {'action': 'NODE_STATUS'})
        nodes = recv_message(sock)
        sock.close()
        return files, nodes

    def update_dashboard(self):
        try:
            file_response, node_response = self._fetch()
            files = file_response.get('files', [])
            nodes = node_response.get('nodes', [])
            total_files = len(files)
            total_chunks = sum(f.get('num_chunks', 0) for f in files)
            active_nodes = sum(1 for n in nodes if n.get('alive'))
            total_nodes = len(nodes)
            avg_chunks = round(total_chunks / total_files, 1) if total_files else 0.0
            split_files = sum(1 for f in files if f.get('num_chunks', 0) > 1)
            file_types = len({(f.get('filename', '').split('.')[-1] or 'FILE').upper() for f in files}) if files else 0

            if total_nodes == 0:
                health = 'No Nodes'; badge = 'warn'
            elif active_nodes == total_nodes:
                health = 'Healthy'; badge = 'ok'
            elif active_nodes > 0:
                health = 'Degraded'; badge = 'warn'
            else:
                health = 'Offline'; badge = 'bad'

            self.files_card.set_data(str(total_files), 'Files currently registered in the DFS')
            self.chunks_card.set_data(str(total_chunks), 'Total chunks distributed across storage nodes')
            self.nodes_card.set_data(f'{active_nodes}/{total_nodes}', 'Nodes currently responding to heartbeat checks')
            self.health_card.set_data(health, 'Overall cluster availability based on active nodes')
            self.avg_card.value.setText(str(avg_chunks)); self.avg_card.meta.setText('Average chunk count per stored file')
            self.split_card.value.setText(str(split_files)); self.split_card.meta.setText('Files split into more than one chunk')
            self.master_card.value.setText('Online'); self.master_card.meta.setText('Master service reachable from the GUI')

            if files:
                largest = max(files, key=lambda f: f.get('num_chunks', 0))
                self.overview_text.setText(
                    f'The cluster is tracking {total_files} file(s) across {total_chunks} chunk(s). '
                    f'Most chunked file: {largest.get("filename", "Unknown")} '
                    f'({largest.get("num_chunks", 0)} chunk(s)).'
                )
            else:
                self.overview_text.setText('No files are currently stored in the distributed file system.')

            self.last_updated.setText(f"Last updated: {QDateTime.currentDateTime().toString('dd MMM yyyy  hh:mm:ss AP')}")
            self._refresh_badge(badge, 'Connection: Online')

            GUI_STATE.update_stats(
                total_files=total_files,
                total_chunks=total_chunks,
                active_nodes=active_nodes,
                total_nodes=total_nodes,
                cluster_health=health,
                file_types=file_types,
                avg_chunks=avg_chunks,
                master_online=True,
            )
            if self.last_health != health:
                GUI_STATE.add_log('INFO', 'Dashboard', f'Cluster health is now {health}.')
                self.last_health = health
        except Exception:
            self.files_card.set_data('--', 'Could not reach master')
            self.chunks_card.set_data('--', 'Could not reach master')
            self.nodes_card.set_data('--', 'Could not reach master')
            self.health_card.set_data('Offline', 'Master server not reachable')
            self.avg_card.value.setText('--'); self.avg_card.meta.setText('No data')
            self.split_card.value.setText('--'); self.split_card.meta.setText('No data')
            self.master_card.value.setText('Offline'); self.master_card.meta.setText('Master service not reachable')
            self.overview_text.setText('Live overview unavailable because the master service did not respond.')
            self.last_updated.setText('Last updated: failed')
            self._refresh_badge('bad', 'Connection: Offline')
            GUI_STATE.update_stats(master_online=False, cluster_health='Offline')
            if self.last_health != 'Offline':
                GUI_STATE.add_log('ERROR', 'Dashboard', 'Master service did not respond to dashboard refresh.')
                self.last_health = 'Offline'
