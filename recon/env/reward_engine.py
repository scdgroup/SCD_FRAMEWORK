# file env/reward_engine.py
import numpy as np

class RewardEngine:
    def __init__(self):
        self.used_action_signatures = set()

    def compute(self, state, action_info):
        norm_alerts = state[0]
        norm_severity = state[1]
        norm_unique_sigs = state[2]
        success = state[3]
        norm_duration = state[4]
        dns_scan_detect = state[8]
        dns_tunnel_detect = state[9]
        dns_flood_detect = state[10]
        dns_anomaly_detect = state[11]
        norm_discovered = state[12]   # نسبة الساب دومينات المكتشفة

        reward = 0.0

        # مكافأة اكتشاف الساب دومينات (كلما زاد العدد زادت المكافأة)
        reward += norm_discovered * 20.0

        # مكافأة نجاح الاستطلاع (معدل الإجابات)
        reward += success * 10.0

        # عقوبات قوية على الإنذارات
        reward -= norm_alerts * 10.0
        reward -= norm_severity * 12.0
        reward -= norm_unique_sigs * 6.0

        # عقوبات إضافية لأنواع كشف DNS
        reward -= dns_scan_detect * 5.0
        reward -= dns_tunnel_detect * 8.0
        reward -= dns_flood_detect * 7.0
        reward -= dns_anomaly_detect * 6.0

        # مكافأة صغيرة إذا لم يكن هناك إنذارات مع نجاح
        if norm_alerts == 0 and success > 0.5:
            reward += 8.0
        elif norm_alerts == 0:
            reward += 3.0

        # عقوبة الوقت
        reward -= norm_duration * 2.0

        # عقوبة التكرار
        action_sig = (action_info.get("attack_type"),
                      tuple(sorted(action_info.get("params", {}).items())))
        if action_sig in self.used_action_signatures:
            reward -= 12.0
        else:
            self.used_action_signatures.add(action_sig)
            if len(self.used_action_signatures) > 200:
                self.used_action_signatures.clear()

        scaled_reward = np.clip(reward / 40.0, -1.0, 1.0)
        return scaled_reward
    # total reward T = 41
    # total reward F = 68

    def reset(self):
        self.used_action_signatures.clear()