import os
import numpy as np
import json
import argparse
from config.env_config import Config
from config.eval_config import EvalConfig
from agents.dqn_agent import DQNAgent

class ModelInspector:
    def __init__(self, model_path=None):
        self.cfg = Config()
        self.eval_cfg = EvalConfig()
        m_path = model_path or self.eval_cfg.DEFAULT_MODEL_PATH
        
        self.agent = DQNAgent(state_size=self.cfg.STATE_SIZE, config=self.cfg)
        # محاولة تحميل checkpoint (نموذج + ذاكرة + epsilon)
        m_dir = os.path.dirname(m_path)
        m_base = os.path.basename(m_path).replace(".keras", "").replace("dqn_model_ep", "")
        mem_path = os.path.join(m_dir, f"dqn_memory_ep{m_base}.pkl")
        eps_path = os.path.join(m_dir, f"dqn_epsilon_ep{m_base}.json")
        
        if os.path.exists(m_path) and os.path.exists(mem_path) and os.path.exists(eps_path):
            self.agent.load_checkpoint(m_dir, m_base)  # load_checkpoint expects folder and episode
        elif os.path.exists(m_path):
            self.agent.load(m_path)
        else:
            raise FileNotFoundError(f"Model file not found: {m_path}")
        
        # ضبط حجم الحالة إذا اختلف
        actual_state_size = self.agent.model.input_shape[1]
        if actual_state_size != self.cfg.STATE_SIZE:
            print(f"[!] Adjusting state size to {actual_state_size} to match model.")
            self.cfg.STATE_SIZE = actual_state_size
            
        print(f"[+] Model loaded for inspection: {m_path}")

    def predict_best_actions_for_scenarios(self):
        scenarios = {
            "initial_state": np.zeros(self.cfg.STATE_SIZE),
            "high_alert_state": np.array([0.9] + [0.0]*(self.cfg.STATE_SIZE-1)),
            "high_success_history": np.array([0.0, 1.0, 0.0, 0.0, 1.0] + [0.0]*(self.cfg.STATE_SIZE-5))
        }
        
        results = []
        for name, state in scenarios.items():
            q_values = self.agent.model.predict(state.reshape(1, -1), verbose=0)[0]
            best_action_idx = np.argmax(q_values)
            # استخدام decode_action الموحدة
            attack_name, params = self.cfg.decode_action(best_action_idx)
            results.append({
                "scenario": name,
                "preferred_attack": attack_name,
                "params": params,
                "confidence_score": float(np.max(q_values))
            })
        return results

    def export_knowledge(self):
        knowledge = self.predict_best_actions_for_scenarios()
        out_path = self.eval_cfg.model_knowledge_path
        with open(out_path, 'w') as f:
            json.dump(knowledge, f, indent=4)
        print(f"[+] Model knowledge exported to: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect DNS Recon RL Model")
    parser.add_argument("--model", type=str, help="Path to the .keras model file")
    args = parser.parse_args()
    
    inspector = ModelInspector(model_path=args.model)
    inspector.export_knowledge()