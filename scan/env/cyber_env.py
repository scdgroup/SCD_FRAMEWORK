import time
import numpy as np
from core.attack_engine import AttackEngine
from env.state_builder import StateBuilder
from env.reward_engine import RewardEngine
from core.eve_reader import EveReader

class CyberEnv:
    def __init__(self, cfg):
        self.cfg = cfg
        self.engine = AttackEngine(cfg)
        self.eve_reader = EveReader(log_path="/var/log/suricata/eve.json")
        self.builder = StateBuilder(cfg)
        self.rewarder = RewardEngine()
        self.step_count = 0
    def reset(self):
        self.step_count = 0
        self.eve_reader.clear()
        self.builder.reset()
        self.rewarder.reset()
        return self.builder.build([], {"duration": 0.0}, 0, self.cfg.MAX_STEPS, {})

    def step(self, action_idx):
        """
        Takes an action index, decodes it, executes the attack, and returns the new state.
        """
        attack_name, params = self.cfg.decode_action(action_idx)
        start_time = time.time()
        
        # Execute the attack
        result = self.engine.execute_attack(attack_name, params)

        # Wait for logs to be generated and processed by Suricata
        wait_time = max(2.0, result.get("duration", 1.0) * 1.2)
        time.sleep(wait_time)

        # Read new alerts from Suricata
        alerts = self.eve_reader.get_new_alerts(since_timestamp=start_time)

        # Build the new state (passing action_idx to update history)
        state = self.builder.build(alerts, result, self.step_count, self.cfg.MAX_STEPS, params, action_idx=action_idx)

        action_info = {
            "attack_type": attack_name,
            "params": params,
            "result": result
        }
        
        # Calculate reward
        reward = self.rewarder.compute(state, action_info)

        self.step_count += 1
        done = self.step_count >= self.cfg.MAX_STEPS

        info = {
            "attack_name": attack_name,
            "params": params,
            "attack_result": result,
            "logs_count": len(alerts),
            "step": self.step_count
        }
        return state, reward, done, info
