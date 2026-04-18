
from __future__ import annotations

import re
from collections import deque
from datetime import datetime
from typing import Any, Dict, Iterable, List, Set

from PyQt5.QtCore import QObject, pyqtSignal


class GuiState(QObject):
    log_added = pyqtSignal(dict)
    stats_changed = pyqtSignal(dict)
    theme_changed = pyqtSignal(str)
    files_changed = pyqtSignal(list)
    nodes_changed = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.logs = deque(maxlen=500)
        self.history = deque(maxlen=60)
        self.current_theme = 'dark'
        self.current_files: List[dict] = []
        self.current_nodes: List[dict] = []
        self.current_stats: Dict[str, Any] = {
            'total_files': 0,
            'total_chunks': 0,
            'active_nodes': 0,
            'total_nodes': 3,
            'cluster_health': 'Unknown',
            'selected_file': '--',
            'selected_type': '--',
            'selected_size': '--',
            'selected_chunks': 0,
            'file_types': 0,
            'avg_chunks': 0.0,
            'master_online': False,
            'multi_chunk_files': 0,
            'most_chunked_file': '--',
            'chunk_load_mode': 'estimated',
        }

    def add_log(self, level: str, source: str, message: str):
        entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'level': level.upper(),
            'source': source,
            'message': message,
        }
        self.logs.appendleft(entry)
        self.log_added.emit(entry)

    def clear_logs(self):
        self.logs.clear()
        self.add_log('INFO', 'GUI', 'Cleared on-screen log history.')

    def update_stats(self, **kwargs):
        changed = False
        for key, value in kwargs.items():
            if self.current_stats.get(key) != value:
                self.current_stats[key] = value
                changed = True
        if changed:
            snapshot = dict(self.current_stats)
            snapshot['time'] = datetime.now().strftime('%H:%M:%S')
            self.history.append(snapshot)
            self.stats_changed.emit(snapshot)

    def set_theme(self, theme_name: str):
        if theme_name != self.current_theme:
            self.current_theme = theme_name
            self.theme_changed.emit(theme_name)
            self.add_log('INFO', 'GUI', f'Switched theme to {theme_name.title()} mode.')

    def set_files(self, files: List[dict]):
        self.current_files = list(files or [])
        self.files_changed.emit(self.current_files)

    def set_nodes(self, nodes: List[dict]):
        self.current_nodes = list(nodes or [])
        self.nodes_changed.emit(self.current_nodes)

    @staticmethod
    def _normalize_node_ids(value: Any) -> Set[int]:
        found: Set[int] = set()
        if value is None:
            return found
        if isinstance(value, int):
            if 1 <= value <= 999:
                found.add(value)
            return found
        if isinstance(value, str):
            lower = value.lower()
            if 'node' in lower:
                for num in re.findall(r'(?:node\s*|node_|node-)?(\d+)', lower):
                    try:
                        n = int(num)
                    except ValueError:
                        continue
                    if 1 <= n <= 999:
                        found.add(n)
            return found
        if isinstance(value, dict):
            for nested in value.values():
                found.update(GuiState._normalize_node_ids(nested))
            return found
        if isinstance(value, (list, tuple, set)):
            for nested in value:
                found.update(GuiState._normalize_node_ids(nested))
            return found
        return found

    def compute_node_chunk_loads(self) -> tuple[Dict[int, int], str]:
        counts: Dict[int, int] = {}
        actual_found = False
        for file_obj in self.current_files:
            chunk_count = int(file_obj.get('num_chunks', 0) or 0)
            if chunk_count <= 0:
                continue
            node_ids: Set[int] = set()
            for key in ('chunk_locations', 'locations', 'nodes', 'replicas', 'storage_nodes', 'chunk_distribution'):
                if key in file_obj:
                    node_ids.update(self._normalize_node_ids(file_obj.get(key)))
            chunks = file_obj.get('chunks')
            if isinstance(chunks, list) and chunks:
                local_found = False
                for chunk in chunks:
                    chunk_nodes = self._normalize_node_ids(chunk)
                    if chunk_nodes:
                        local_found = True
                        actual_found = True
                        for node_id in chunk_nodes:
                            counts[node_id] = counts.get(node_id, 0) + 1
                if local_found:
                    continue
            if node_ids:
                actual_found = True
                # We know at least which nodes store the file. Spread file chunks over them.
                node_list = sorted(node_ids)
                for idx in range(chunk_count):
                    node_id = node_list[idx % len(node_list)]
                    counts[node_id] = counts.get(node_id, 0) + 1

        if actual_found and counts:
            return counts, 'actual'

        active = [n for n in self.current_nodes if n.get('alive')]
        if not active:
            active = self.current_nodes
        node_ids = [int(n.get('node_id')) for n in active if n.get('node_id') is not None]
        node_ids = [n for n in node_ids if n > 0]
        if not node_ids:
            node_ids = [1, 2, 3]
        counts = {node_id: 0 for node_id in node_ids}
        total_chunks = sum(int(f.get('num_chunks', 0) or 0) for f in self.current_files)
        for idx in range(total_chunks):
            node_id = node_ids[idx % len(node_ids)]
            counts[node_id] = counts.get(node_id, 0) + 1
        return counts, 'estimated'


GUI_STATE = GuiState()
