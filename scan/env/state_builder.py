import numpy as np
import math
from collections import Counter, deque

class StateBuilder:
    def __init__(self, cfg):
        self.cfg = cfg
        # Use a slightly longer history internally but expose only relevant parts to avoid overfitting
        self.history = deque(maxlen=5) 

    def reset(self):
        self.history.clear()
        # Initialize with neutral values
        for _ in range(5):
            self.history.append(-1.0)

    def build(self, logs, result, step_count, max_steps, params, action_idx=None):
        """
        Builds the state vector with improved history timing to prevent overfitting.
        """
        # 1. Update history with a decay-like logic or simply store normalized indices
        if action_idx is not None:
            norm_action = (action_idx + 1) / (self.cfg.total_action_size + 1)
            self.history.append(norm_action)

        alerts = [log for log in logs if log.get("event_type") == "alert"]
        num_alerts = len(alerts)

        # 2. Extract Alert Features
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

        # 3. Success Metrics
        success = 0.0
        if "metrics" in result:
            m = result["metrics"]
            if "banners_found" in m:
                success = min(1.0, m["banners_found"] / 5.0)
            elif "open_ports" in m:
                success = min(1.0, m["open_ports"] / 5.0)
            elif "open_or_filtered_ports" in m:
                success = min(1.0, m["open_or_filtered_ports"] / 5.0)
            elif "unfiltered_ports" in m:
                success = min(1.0, m["unfiltered_ports"] / 5.0)
            else:
                success = 1.0 if result.get("success", False) else 0.0
        else:
            success = 1.0 if result.get("success", False) else 0.0

        norm_duration = min(1.0, duration / 20.0)

        # 4. Evasion Features
        fragsize_used = 1.0 if params.get("fragsize", 0) > 0 else 0.0
        decoy_count_used = min(1.0, params.get("decoy_count", 0) / 5.0)
        random_sport_used = 1.0 if params.get("random_sport", False) else 0.0

        step_progress = step_count / max_steps if max_steps > 0 else 0.0

        # 5. Advanced Detection Signatures
        scan_detect = recon_detect = 0.0
        for log in alerts:
            sig = log.get("alert", {}).get("signature", "").lower()
            if any(k in sig for k in ["scan", "nmap", "syn scan", "fin scan", "ack scan", "window scan"]):
                scan_detect += 1
            elif any(k in sig for k in ["recon", "enumeration", "snmp", "banner", "service version"]):
                recon_detect += 1

        scan_detect = min(1.0, scan_detect / 5.0)
        recon_detect = min(1.0, recon_detect / 5.0)

        # 6. Construct State Vector (Fixed size to avoid matrix errors)
        # Base state (14 features)
        base_state = [
            norm_alerts,        # 0
            norm_severity,      # 1
            norm_unique_sigs,   # 2
            success,            # 3
            norm_duration,      # 4
            fragsize_used,      # 5
            decoy_count_used,   # 6
            random_sport_used,  # 7
            scan_detect,        # 8
            recon_detect,       # 9
            entropy,            # 10
            alert_rate,         # 11
            step_progress,      # 12
            0.0                 # 13 (padding/future use)
        ]
        
        # 7. Optimized History Integration
        # We take the last 3 actions from our 5-action buffer. 
        # This provides a 'moving window' that is less prone to local overfitting.
        history_to_add = list(self.history)[-3:]
        state = base_state + history_to_add

        return np.array(state[:self.cfg.STATE_SIZE], dtype=np.float32)
