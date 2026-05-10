# file core/eve_reader.py
import json
import time
import os
from collections import deque

class EveReader:
    def __init__(self, log_path="/var/log/suricata/eve.json"):
        self.log_path = log_path
        self.last_position = 0
        self.buffer = deque(maxlen=10000)
        self._update_position()  # ✅ تعيين الموضع إلى نهاية الملف عند الإنشاء

    def _update_position(self):
        """تحديث آخر موضع قراءة إلى نهاية الملف."""
        try:
            with open(self.log_path, 'r') as f:
                f.seek(0, os.SEEK_END)
                self.last_position = f.tell()
        except Exception as e:
            print(f"[!] Error updating position: {e}")

    def get_new_alerts(self, since_timestamp=None):
        """
        قراءة السجلات الجديدة منذ آخر مرة.
        إذا تم تحديد since_timestamp، فسيتم إرجاع السجلات التي timestamp > since_timestamp.
        """
        alerts = []
        try:
            with open(self.log_path, 'r') as f:
                f.seek(self.last_position)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        log = json.loads(line)
                        if log.get('event_type') == 'alert':
                            ts = log.get('timestamp')
                            if ts:
                                ts_float = self._iso_to_float(ts)
                                log['_timestamp_float'] = ts_float
                                if since_timestamp is None or ts_float >= since_timestamp:
                                    alerts.append(log)
                    except json.JSONDecodeError:
                        continue
                self.last_position = f.tell()
        except Exception as e:
            print(f"[!] Error reading eve.json: {e}")
        return alerts

    def _iso_to_float(self, iso_str):
        """تحويل ISO timestamp إلى float (ثواني)."""
        if iso_str.endswith('+0000'):
            iso_str = iso_str[:-5]
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str)
        return dt.timestamp()

    def clear(self):
        """مسح المخزن المؤقت وإعادة تعيين الموضع إلى نهاية الملف."""
        self.buffer.clear()
        self._update_position()