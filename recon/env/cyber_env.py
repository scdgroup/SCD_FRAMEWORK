import time
import numpy as np
from core.attack_engine import AttackEngine
from core.eve_reader import EveReader
from env.state_builder import StateBuilder
from env.reward_engine import RewardEngine

class CyberEnv:
    def __init__(self, cfg):
        self.cfg = cfg
        self.attack_name = cfg.DEFAULT_ATTACK
        self.engine = AttackEngine(cfg)
        self.eve_reader = EveReader(log_path="/var/log/suricata/eve.json")
        self.builder = StateBuilder()
        self.rewarder = RewardEngine()
        self.step_count = 0

    def reset(self):
        self.step_count = 0
        self.eve_reader.clear()
        self.builder.reset()
        self.rewarder.reset()
        return np.zeros(self.cfg.STATE_SIZE, dtype=np.float32)

    def step(self, action_idx):
        """
        إصدار جديد من step يأخذ action_idx (رقم الإجراء) بدلاً من params.
        يقوم بفك ترميز المعاملات من config ثم تنفيذ الهجوم.
        """
        params = self.cfg.decode_params(self.attack_name, action_idx)
        start_time = time.time()
        result = self.engine.execute_attack(self.attack_name, params)

        wait_time = max(1.0, result.get("duration", 1.0)) + 1.0
        time.sleep(wait_time)

        alerts = self.eve_reader.get_new_alerts(since_timestamp=start_time)

        state = self.builder.build(alerts, result, self.step_count, self.cfg.MAX_STEPS)

        action_info = {
            "attack_type": self.attack_name,
            "params": params,
            "result": result
        }
        reward = self.rewarder.compute(state, action_info)

        self.step_count += 1
        done = self.step_count >= self.cfg.MAX_STEPS

        info = {
            "attack_result": result,
            "logs_count": len(alerts),
            "step": self.step_count,
            "attack_name": self.attack_name,
            "params": params
        }
        return state, reward, done, info