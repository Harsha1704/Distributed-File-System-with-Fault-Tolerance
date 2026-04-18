from collections import deque
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal


class GuiState(QObject):
    log_added = pyqtSignal(dict)
    stats_changed = pyqtSignal(dict)
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.logs = deque(maxlen=400)
        self.history = deque(maxlen=48)
        self.current_theme = 'dark'
        self.current_stats = {
            'total_files': 0,
            'total_chunks': 0,
            'active_nodes': 0,
            'total_nodes': 3,
            'cluster_health': 'Unknown',
            'selected_file': '--',
            'selected_type': '--',
            'selected_size': '--',
            'file_types': 0,
            'avg_chunks': 0.0,
            'master_online': False,
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


GUI_STATE = GuiState()
