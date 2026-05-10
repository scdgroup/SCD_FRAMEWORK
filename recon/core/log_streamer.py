
import socket
import json
import threading
import time
from collections import deque

class LogStreamer:
    def __init__(self, port=2080):
        self.port = port
        self.buffer = deque(maxlen=5000)
        self.running = False
        self.server_thread = None
        self.lock = threading.Lock()
        self.start()

    def start(self):
        """Start the socket server to receive logs."""
        if self.running:
            return
        self.running = True
        self.server_thread = threading.Thread(target=self._listen, daemon=True)
        self.server_thread.start()
        print(f"[*] Log Streamer (Socket Server) started on port {self.port}")

    def _listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('0.0.0.0', self.port))
                s.listen(5)
                s.settimeout(1.0)
            except Exception as e:
                print(f"[!] Log Streamer Bind Error: {e}")
                return
            
            while self.running:
                try:
                    conn, addr = s.accept()
                    with conn:
                        # Use a buffer to handle large log streams
                        data_buffer = ""
                        while self.running:
                            data = conn.recv(4096).decode('utf-8', errors='ignore')
                            if not data:
                                break
                            data_buffer += data
                            # Suricata EVE logs are newline-delimited JSON
                            while "\n" in data_buffer:
                                line, data_buffer = data_buffer.split("\n", 1)
                                if line.strip():
                                    try:
                                        log_entry = json.loads(line)
                                        log_entry['local_time'] = time.time()
                                        with self.lock:
                                            self.buffer.append(log_entry)
                                    except json.JSONDecodeError:
                                        continue
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[!] Log Streamer Error: {e}")
                    time.sleep(1)

    def get_logs_since(self, timestamp):
        """Retrieve logs received after a specific timestamp."""
        with self.lock:
            return [log for log in self.buffer if log.get('local_time', 0) >= timestamp]

    def clear(self):
        with self.lock:
            self.buffer.clear()

    def stop(self):
        self.running = False
        if self.server_thread:
            self.server_thread.join(timeout=2)
        print("[*] Log Streamer stopped.")
