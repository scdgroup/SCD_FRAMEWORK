import os
import numpy as np


class Config:
    # Network Configuration
    INTERFACE = "wlan0"
    TARGET_DOMAIN = "google.com"
    OUTPUT_DIR = "/var/log/scdlogs/recon"
    OUTPUT_DIR_MODEL = os.path.join(OUTPUT_DIR, "training_results")
    DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "208.67.222.222"]
    LEGITIMATE_DOMAINS = ["google.com", "microsoft.com", "cloudflare.com", "amazon.com"]
    csv_path = os.path.join(OUTPUT_DIR, "detailed_eval_logs.csv")
    json_path = os.path.join(OUTPUT_DIR, "summary_eval_logs.json")
    COMMON_SUBDOMAINS = [
        "www",
        "mail",
        "ftp",
        "webmail",
        "vpn",
        "remote",
        "exchange",
        "autodiscover",
        "ns1",
        "ns2",
        "mx1",
        "mx2",
        "api",
        "dev",
        "test",
        "blog",
        "shop",
        "support",
        "portal",
        "admin",
        "secure",
    ]

    MAX_STEPS = 30
    STATE_SIZE = 20

    # Training hyperparameters (جديد)
    EPISODES = 100
    BATCH_SIZE = 64
    SAVE_INTERVAL = 5
    DEFAULT_EPISODES = 20
    DEFAULT_MAX_STEPS = 30
    # نوع الهجوم الوحيد المدعوم حالياً
    DEFAULT_ATTACK = "dns_recon"

    # Parameter spaces لـ DNS Recon
    ATTACK_PARAM_SPACES = {
        "dns_recon": {
            "delay": {"values": [1.0, 3.0, 5.2, 7.0], "type": "float"},
            "source_port_random": {"values": [0, 1], "type": "bool"},
            "random_txn_id": {"values": [0, 1], "type": "bool"},
            "query_type": {"values": ["A", "AAAA", "MX"], "type": "str"},
            "rotate_dns": {"values": [0, 1], "type": "bool"},
            "jitter": {"values": [0.0, 0.2, 0.5], "type": "float"},
            "decoy": {"values": [0, 1], "type": "bool"},
            "fragmentation": {"values": [0, 1], "type": "bool"},
            "num_subdomains": {"values": [5, 10, 20], "type": "int"},
        }
    }

    QUERY_TYPES = ["A", "AAAA", "MX", "TXT", "NS"]

    def update_network_config(
        self, interface=None, target_domain=None
    ):  # , target_ip=None
        if interface:
            self.INTERFACE = interface
        if target_domain:
            self.TARGET_DOMAIN = target_domain
        # if target_ip:
        #     self.TARGET_IP = target_ip

    @property
    def action_size_per_attack(self):
        sizes = {}
        for attack, params in self.ATTACK_PARAM_SPACES.items():
            dim = 1
            for p in params.values():
                dim *= len(p["values"])
            sizes[attack] = dim
        return sizes

    @property
    def total_action_size(self):
        """إجمالي حجم فضاء الإجراءات (للهجوم الوحيد)"""
        return self.action_size_per_attack[self.DEFAULT_ATTACK]

    def encode_params(self, attack_name, params_dict):
        space = self.ATTACK_PARAM_SPACES[attack_name]
        index = 0
        multiplier = 1
        for param_name in reversed(list(space.keys())):
            values = space[param_name]["values"]
            value = params_dict[param_name]
            if space[param_name]["type"] == "bool":
                idx = values.index(int(value))
            elif space[param_name]["type"] == "str":
                idx = values.index(value)
            else:
                idx = min(range(len(values)), key=lambda i: abs(values[i] - value))
            index += idx * multiplier
            multiplier *= len(values)
        return index

    def decode_params(self, attack_name, flat_index):
        space = self.ATTACK_PARAM_SPACES[attack_name]
        params = {}
        temp = flat_index
        for param_name in space.keys():
            values = space[param_name]["values"]
            idx = temp % len(values)
            temp //= len(values)
            value = values[idx]
            if space[param_name]["type"] == "bool":
                value = bool(value)
            elif space[param_name]["type"] == "str":
                value = str(value)
            else:
                value = float(value)
            params[param_name] = value
        return params

    # ========== التوافق مع واجهة الإجراءات الموحدة (لأدوات التقييم) ==========
    def encode_action(self, attack_name, params_dict):
        """
        تحويل (اسم الهجوم، المعاملات) إلى رقم إجراء موحد.
        بما أن الهجوم واحد فقط، نتحقق من الاسم ثم نرمز المعاملات.
        """
        if attack_name != self.DEFAULT_ATTACK:
            raise ValueError(f"Unsupported attack: {attack_name}")
        return self.encode_params(attack_name, params_dict)

    def decode_action(self, flat_index):
        """
        تحويل رقم الإجراء الموحد إلى (اسم الهجوم، المعاملات).
        """
        params = self.decode_params(self.DEFAULT_ATTACK, flat_index)
        return self.DEFAULT_ATTACK, params
