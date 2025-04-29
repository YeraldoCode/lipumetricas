import json
from datetime import datetime
import os

class AuditLogger:
    def __init__(self, log_file):
        self.log_file = log_file
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                json.dump([], f)
    
    def ensure_log_file_exists(self):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f)

    def log_action(self, action, filename, user_ip=None, details=None):
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        except:
            logs = []

        logs.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'filename': filename,
            'ip': user_ip,
            'details': details
        })

        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def get_logs(self, limit=50):
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
            return logs[-limit:]
        except:
            return []
