class Config:
    import os

    # Network Configuration
    TARGET_IP = "192.168.2.129"
    INTERFACE = "vmnet8"
    STREAM_PORT = 2080

    # Evaluation Run Settings
    DEFAULT_EPISODES = 20
    DEFAULT_MAX_STEPS = 30

    # Output Directory (English Name)
    # OUTPUT_DIR = "/var/log/scdlogs/scan/test_results"
    OUTPUT_DIR = "/var/log/scdlogs/scan"
    OUTPUT_DIR_MODEL = f"{OUTPUT_DIR}/training_results"
    # Files for Universal Evaluator
    DETAILED_LOG_FILE = "detailed_eval_logs.csv"
    SUMMARY_LOG_FILE = "summary_eval_logs.json"

    # Files for Buffer Analyzer
    BUFFER_ANALYSIS_FILE = "buffer_analysis.csv"
    BUFFER_SUMMARY_FILE = "buffer_summary.json"

    # Files for Model Inspector
    MODEL_KNOWLEDGE_FILE = "model_knowledge.json"

    # Default Model and Buffer Paths
    DEFAULT_MODEL_PATH = f"{OUTPUT_DIR_MODEL}/dqn_model_ep60.keras"
    DEFAULT_BUFFER_PATH = f"{OUTPUT_DIR_MODEL}/dqn_memory_ep60.pkl"
    # RL Environment Configuration
    MAX_STEPS = 30
    # STATE_SIZE will be updated dynamically in state_builder if needed
    # Currently 17: Original (14) + 3 (History)
    STATE_SIZE = 17

    # Training Configuration
    EPISODES = 500
    BATCH_SIZE = 64
    SAVE_INTERVAL = 10

    SCAN_PORTS = [22, 80, 443, 3306, 8080]

    # Updated Attack Types: Removed null_scan, xmas_scan. Added window_scan, banner_grabbing.
    ATTACK_TYPES = [
        "stealth_syn_scan",
        "fin_scan",
        "ack_scan",
        "window_scan",
        "banner_grabbing",
    ]

    # Parameter spaces
    ATTACK_PARAM_SPACES = {
        "stealth_syn_scan": {
            "delay": {"values": [0.5, 2.0, 5.0], "type": "float"},
            "window": {"values": [256, 1024, 4096], "type": "int"},
            "ttl": {"values": [32, 64, 128], "type": "int"},
            "fragsize": {"values": [0, 16, 32], "type": "int"},
            "random_sport": {"values": [0, 1], "type": "bool"},
            "distractor": {"values": [0, 1], "type": "bool"},
            "decoy_count": {"values": [0, 1, 2], "type": "int"},
        },
        "fin_scan": {
            "delay": {"values": [0.5, 1.0, 2.0], "type": "float"},
            "ttl": {"values": [32, 64, 128], "type": "int"},
            "fragsize": {"values": [0, 16, 32], "type": "int"},
            "random_sport": {"values": [0, 1], "type": "bool"},
            "decoy_count": {"values": [0, 1, 2], "type": "int"},
        },
        "ack_scan": {
            "delay": {"values": [0.5, 1.0, 2.0], "type": "float"},
            "ttl": {"values": [32, 64, 128], "type": "int"},
            "fragsize": {"values": [0, 16, 32], "type": "int"},
            "random_sport": {"values": [0, 1], "type": "bool"},
            "decoy_count": {"values": [0, 1, 2], "type": "int"},
        },
        "window_scan": {
            "delay": {"values": [0.5, 1.0, 2.0], "type": "float"},
            "ttl": {"values": [32, 64, 128], "type": "int"},
            "fragsize": {"values": [0, 16, 32], "type": "int"},
            "random_sport": {"values": [0, 1], "type": "bool"},
            "decoy_count": {"values": [0, 1, 2], "type": "int"},
        },
        "banner_grabbing": {
            "delay": {"values": [0.5, 1.0, 2.0], "type": "float"},
            "timeout": {"values": [1.0, 3.0, 5.0], "type": "float"},
        },
    }

    def update_network_config(self, target_ip=None, interface=None):
        if target_ip:
            self.TARGET_IP = target_ip
        if interface:
            self.INTERFACE = interface

    @property
    def action_space_sizes(self):
        sizes = {}
        for attack, params in self.ATTACK_PARAM_SPACES.items():
            dim = 1
            for p in params.values():
                dim *= len(p["values"])
            sizes[attack] = dim
        return sizes

    @property
    def total_action_size(self):
        return sum(self.action_space_sizes.values())

    def encode_action(self, attack_name, params_dict):
        base_offset = 0
        for atk_type in self.ATTACK_TYPES:
            if atk_type == attack_name:
                break
            base_offset += self.action_space_sizes[atk_type]

        space = self.ATTACK_PARAM_SPACES[attack_name]
        param_index = 0
        multiplier = 1
        for param_name in reversed(list(space.keys())):
            values = space[param_name]["values"]
            value = params_dict[param_name]
            # Handle both exact matches and closest values
            idx = min(range(len(values)), key=lambda i: abs(values[i] - value))
            param_index += idx * multiplier
            multiplier *= len(values)
        return base_offset + param_index

    def decode_action(self, flat_index):
        current_offset = 0
        for attack_name in self.ATTACK_TYPES:
            attack_size = self.action_space_sizes[attack_name]
            if flat_index < current_offset + attack_size:
                param_flat_index = flat_index - current_offset
                space = self.ATTACK_PARAM_SPACES[attack_name]
                params = {}
                temp = param_flat_index
                for param_name in reversed(list(space.keys())):
                    values = space[param_name]["values"]
                    idx = temp % len(values)
                    temp //= len(values)
                    value = values[idx]
                    if space[param_name]["type"] == "bool":
                        value = bool(value)
                    elif space[param_name]["type"] == "int":
                        value = int(value)
                    else:
                        value = float(value)
                    params[param_name] = value
                return attack_name, params
            current_offset += attack_size
        raise ValueError(f"Invalid flat_index: {flat_index}")
