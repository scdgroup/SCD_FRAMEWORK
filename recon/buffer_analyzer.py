import pickle
import os
import json
import pandas as pd
import argparse
from config.env_config import Config
from config.eval_config import EvalConfig

class BufferAnalyzer:
    def __init__(self, buffer_path=None):
        self.cfg = Config()
        self.eval_cfg = EvalConfig()
        self.buffer_path = buffer_path or self.eval_cfg.DEFAULT_BUFFER_PATH
        self.data = []

    def load_and_parse(self):
        if not os.path.exists(self.buffer_path):
            print(f"[-] Buffer file not found: {self.buffer_path}")
            return False

        print(f"[*] Loading buffer: {self.buffer_path}")
        with open(self.buffer_path, 'rb') as f:
            memory = pickle.load(f)

        print(f"[*] Analyzing {len(memory)} transitions...")
        
        for i, transition in enumerate(memory):
            # Transition structure: (state, action, reward, next_state, done)
            state, action_idx, reward, next_state, done = transition
            
            # استخدام decode_action الموحدة
            attack_name, params = self.cfg.decode_action(action_idx)
            
            self.data.append({
                "transition_id": i,
                "attack_type": attack_name,
                "params": json.dumps(params),
                "reward": float(reward),
                "is_terminal": bool(done),
                "probable_success": reward > 0.5 
            })
        return True

    def export_analysis(self):
        if not self.data:
            print("[-] No data to export.")
            return
            
        df = pd.DataFrame(self.data)
        csv_out = self.eval_cfg.buffer_csv_path
        json_out = self.eval_cfg.buffer_json_path
        
        df.to_csv(csv_out, index=False)
        
        # Generate summary
        summary = {
            "total_experiences": len(df),
            "attack_distribution": df['attack_type'].value_counts().to_dict(),
            "avg_reward": float(df['reward'].mean()),
            "success_estimate_count": int(df['probable_success'].sum())
        }
        
        with open(json_out, 'w') as f:
            json.dump(summary, f, indent=4)
            
        print(f"[+] Analysis exported to: {csv_out}")
        print(f"[+] Summary saved to: {json_out}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Replay Buffer (.pkl) files")
    parser.add_argument("--buffer", type=str, help="Path to the .pkl buffer file")
    args = parser.parse_args()
    
    analyzer = BufferAnalyzer(buffer_path=args.buffer)
    if analyzer.load_and_parse():
        analyzer.export_analysis()