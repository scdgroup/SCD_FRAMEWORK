# file env/state_builder.py
import numpy as np
import math
from collections import Counter

class StateBuilder:
    def __init__(self):
        self.alert_history = []

    def reset(self):
        self.alert_history.clear()

    def build(self, logs, result, step_count, max_steps):
        alerts = []
        for log in logs:
            if log.get("event_type") != "alert":
                continue
            sig = log.get("alert", {}).get("signature", "").lower()
            if "dns" in sig:
                alerts.append(log)

        num_alerts = len(alerts)

        if num_alerts > 0:
            severities = [log.get("alert", {}).get("severity", 1) for log in alerts]
            max_severity = max(severities)
            signatures = [log.get("alert", {}).get("signature", "") for log in alerts]
            unique_sigs = len(set(signatures))
            sig_counts = Counter(signatures)
            probs = [c / num_alerts for c in sig_counts.values()]
            entropy = -sum(p * math.log2(p) for p in probs) if probs else 0.0
            entropy = min(1.0, entropy / 5.0)
        else:
            max_severity = 0
            unique_sigs = 0
            entropy = 0.0

        duration = result.get("duration", 0.0)
        alert_rate = min(1.0, num_alerts / (duration * 5.0)) if duration > 0 else 0.0

        norm_alerts = min(1.0, num_alerts / 20.0)
        norm_severity = min(1.0, max_severity / 5.0)
        norm_unique_sigs = min(1.0, unique_sigs / 10.0)

        metrics = result.get("metrics", {})
        success_rate = metrics.get("success_rate", 0.0)
        discovered_count = metrics.get("discovered_count", 0)
        num_requested = metrics.get("num_subdomains", 1)
        # تصحيح: نسبة المكتشفة إلى المطلوب استعلامها
        norm_discovered = min(1.0, discovered_count / num_requested) if num_requested > 0 else 0.0
        success = success_rate * 0.5 + norm_discovered * 0.5

        norm_duration = min(1.0, duration / 30.0)

        dns_scan_detect = 0.0
        dns_tunnel_detect = 0.0
        dns_flood_detect = 0.0
        dns_anomaly_detect = 0.0

        for log in alerts:
            sig = log.get("alert", {}).get("signature", "").lower()
            if any(k in sig for k in ["scan", "enum", "sweep"]):
                dns_scan_detect += 1
            if any(k in sig for k in ["tunnel", "high entropy", "random domain"]):
                dns_tunnel_detect += 1
            if any(k in sig for k in ["flood", "rate limit", "dos"]):
                dns_flood_detect += 1
            if any(k in sig for k in ["malformed", "invalid", "tcp", "fragment"]):
                dns_anomaly_detect += 1

        dns_scan_detect = min(1.0, dns_scan_detect / 3.0)
        dns_tunnel_detect = min(1.0, dns_tunnel_detect / 3.0)
        dns_flood_detect = min(1.0, dns_flood_detect / 3.0)
        dns_anomaly_detect = min(1.0, dns_anomaly_detect / 3.0)

        self.alert_history.append(norm_alerts)
        if len(self.alert_history) > 10:
            self.alert_history.pop(0)
        avg_alerts = np.mean(self.alert_history) if self.alert_history else 0.0

        step_progress = step_count / max_steps if max_steps > 0 else 0.0

        state = [
            norm_alerts, #  1
            norm_severity, #  2
            norm_unique_sigs, #  3
            success, #  4
            norm_duration, #  5
            0.0, #  6
            entropy, #  7
            alert_rate, #  8
            dns_scan_detect, #  9
            dns_tunnel_detect, #  10
            dns_flood_detect, #  11
            dns_anomaly_detect, #  12
            norm_discovered, #  13
            step_progress, #  14
            avg_alerts, #  15
            0.0, 0.0, 0.0, 0.0, 0.0
        ]
        return np.array(state[:20], dtype=np.float32)