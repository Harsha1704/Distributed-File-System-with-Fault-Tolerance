
import socket
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame, QHBoxLayout

from client.config import MASTER_HOST, MASTER_PORT
from common.utils import send_message, recv_message
from gui.shared_state import GUI_STATE


class NodeCard(QFrame):
    def __init__(self, node_id: int, port: int):
        super().__init__()
        self.setObjectName('nodeCard')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)
        top = QHBoxLayout()
        title = QLabel(f'Node {node_id}')
        title.setObjectName('sectionTitle')
        chip = QLabel(f'Port {port}')
        chip.setObjectName('microLabel')
        top.addWidget(title); top.addStretch(1); top.addWidget(chip)
        self.state = QLabel('Checking...'); self.state.setObjectName('nodeState'); self.state.setProperty('state', 'warn')
        self.meta = QLabel('Waiting for heartbeat data'); self.meta.setObjectName('smallMuted')
        self.role = QLabel('Storage node'); self.role.setObjectName('smallMuted')
        layout.addLayout(top)
        layout.addWidget(self.state)
        layout.addWidget(self.meta)
        layout.addWidget(self.role)

    def set_state(self, text: str, state: str, meta: str):
        self.state.setText(text)
        self.state.setProperty('state', state)
        self.meta.setText(meta)
        self.state.style().unpolish(self.state)
        self.state.style().polish(self.state)


class NodeMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.last_states = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        hero = QFrame(); hero.setObjectName('heroPanel')
        h_layout = QVBoxLayout(hero); h_layout.setContentsMargins(24, 24, 24, 24)
        badge = QLabel('NODE HEARTBEAT'); badge.setObjectName('microLabel')
        title = QLabel('Node Monitor'); title.setObjectName('pageTitle')
        subtitle = QLabel('Real-time visibility into node heartbeat, role, and cluster availability.')
        subtitle.setObjectName('pageSubtitle'); subtitle.setWordWrap(True)
        h_layout.addWidget(badge); h_layout.addWidget(title); h_layout.addWidget(subtitle)
        root.addWidget(hero)

        summary_row = QHBoxLayout(); summary_row.setSpacing(18)
        summary = QFrame(); summary.setObjectName('panel')
        s_layout = QVBoxLayout(summary); s_layout.setContentsMargins(18, 18, 18, 18)
        s_title = QLabel('Cluster Summary'); s_title.setObjectName('sectionTitle')
        self.summary_meta = QLabel('Waiting for node health data...'); self.summary_meta.setObjectName('smallMuted')
        s_layout.addWidget(s_title); s_layout.addWidget(self.summary_meta)
        chip = QFrame(); chip.setObjectName('softPanel')
        c_layout = QVBoxLayout(chip); c_layout.setContentsMargins(14, 14, 14, 14)
        c_title = QLabel('Active Nodes'); c_title.setObjectName('statTitle')
        self.active_value = QLabel('--'); self.active_value.setObjectName('smallValue')
        self.active_meta = QLabel('Waiting for data'); self.active_meta.setObjectName('smallMuted')
        c_layout.addWidget(c_title); c_layout.addWidget(self.active_value); c_layout.addWidget(self.active_meta)
        summary_row.addWidget(summary, 3); summary_row.addWidget(chip, 1)
        root.addLayout(summary_row)

        grid = QGridLayout(); grid.setSpacing(18)
        self.cards = {}
        ports = {1: 9100, 2: 9101, 3: 9102}
        for idx, node_id in enumerate([1, 2, 3]):
            card = NodeCard(node_id, ports[node_id])
            self.cards[node_id] = card
            grid.addWidget(card, idx // 2, idx % 2)
        root.addLayout(grid)
        root.addStretch(1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_nodes)
        self.timer.start(2000)
        self.update_nodes()

    def update_nodes(self):
        try:
            sock = socket.socket(); sock.settimeout(3); sock.connect((MASTER_HOST, MASTER_PORT))
            send_message(sock, {'action': 'NODE_STATUS'})
            response = recv_message(sock)
            sock.close()
            nodes = response.get('nodes', [])
            seen = set(); active = 0
            for node in nodes:
                node_id = node.get('node_id')
                if node_id in self.cards:
                    alive = node.get('alive', False)
                    self.cards[node_id].set_state('● ACTIVE' if alive else '● DEAD', 'ok' if alive else 'bad', 'Heartbeat received successfully' if alive else 'Node not responding to heartbeat')
                    active += 1 if alive else 0
                    seen.add(node_id)
                    prev = self.last_states.get(node_id)
                    if prev is None or prev != alive:
                        state_text = 'ACTIVE' if alive else 'DEAD'
                        GUI_STATE.add_log('INFO' if alive else 'WARN', 'Nodes', f'Node {node_id} changed state to {state_text}.')
                    self.last_states[node_id] = alive
            for node_id, card in self.cards.items():
                if node_id not in seen:
                    card.set_state('● ERROR', 'bad', 'Could not read state from master')
            total = len(self.cards)
            self.active_value.setText(f'{active}/{total}')
            self.active_meta.setText('Nodes responding now')
            if active == total:
                self.summary_meta.setText(f'All {total} nodes are healthy and responding to heartbeat checks.')
            elif active > 0:
                self.summary_meta.setText(f'{active}/{total} node(s) are active. Cluster is partially available.')
            else:
                self.summary_meta.setText('No nodes are active. Cluster is unavailable.')
            GUI_STATE.set_nodes(nodes)
            GUI_STATE.update_stats(active_nodes=active, total_nodes=total)
        except Exception:
            for card in self.cards.values():
                card.set_state('● ERROR', 'bad', 'Could not connect to master')
            self.active_value.setText('0/3'); self.active_meta.setText('Master unavailable')
            self.summary_meta.setText('Could not read node heartbeat data from the master service.')
            GUI_STATE.add_log('ERROR', 'Nodes', 'Could not read node heartbeat data from master.')
