# file run_attack.py
import argparse
import time
import os
import numpy as np
from config.env_config import Config
from agents.dqn_agent import DQNAgent
from core.attack_engine import AttackEngine
from core.eve_reader import EveReader
from env.state_builder import StateBuilder


def find_models(output_dir):
    """البحث عن ملفات .keras في مجلد التدريب الخاص بـ scan"""
    import glob

    models = glob.glob(os.path.join(output_dir, "training_results", "*.keras"))
    if not models:
        models = glob.glob(os.path.join(output_dir, "*.keras"))
    if not models:
        models = glob.glob("*.keras")
    return models


def interactive_model_selection(output_dir):
    models = find_models(output_dir)
    if not models:
        print(f"[!] No .keras model files found in {output_dir} or current directory.")
        model_path = input("Enter full path to model: ").strip()
        if not os.path.exists(model_path):
            print(f"[!] File not found: {model_path}")
            return None
        return model_path
    print("\nAvailable models:")
    for i, m in enumerate(models, 1):
        print(f"  {i}. {m}")
    print("  q. Quit")
    choice = input("Select model number (or path): ").strip()
    if choice.lower() == "q":
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            return models[idx]
    except:
        if os.path.exists(choice):
            return choice
    print("[!] Invalid selection.")
    return None


def main():
    parser = argparse.ArgumentParser(description="Run attack using trained DQN model")
    parser.add_argument(
        "--target-ip",
        default=Config.TARGET_IP,
        help="Target IP address (overrides config)",
    )
    parser.add_argument(
        "--interface",
        default=Config.INTERFACE,
        help="Network interface (overrides config)",
    )
    parser.add_argument("--model", help="Path to DQN model (.keras)")
    parser.add_argument(
        "--iterations", type=int, default=2, help="Number of attack iterations"
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    cfg = Config()

    # تحديث الإعدادات من arguments أو تفاعلي
    if args.target_ip:
        target_ip = args.target_ip
    else:
        default_ip = cfg.TARGET_IP
        inp = input(f"Enter target IP [{default_ip}]: ").strip()
        target_ip = inp if inp else default_ip

    if args.interface:
        interface = args.interface
    else:
        default_iface = cfg.INTERFACE
        inp = input(f"Enter network interface [{default_iface}]: ").strip()
        interface = inp if inp else default_iface

    cfg.update_network_config(target_ip=target_ip, interface=interface)

    # اختيار النموذج
    if args.model:
        model_path = args.model
        if not os.path.exists(model_path):
            print(f"[!] Model not found: {model_path}")
            return
    else:
        model_path = interactive_model_selection(cfg.OUTPUT_DIR)
        if not model_path:
            return

    print(f"[+] Loading model: {model_path}")
    agent = DQNAgent(state_size=cfg.STATE_SIZE, config=cfg)
    agent.load(model_path)

    attack_engine = AttackEngine(cfg)
    eve_reader = EveReader()
    state_builder = StateBuilder(cfg)
    state_builder.reset()
    current_state = state_builder.build(
        [], {"duration": 0.0}, 0, cfg.MAX_STEPS, {}, action_idx=None
    )

    for i in range(args.iterations):
        print(f"\n[*] Iteration {i+1}/{args.iterations}")
        action_idx = agent.act(current_state, epsilon=0.0)
        attack_type, best_params = cfg.decode_action(action_idx)

        print(f"[*] Selected attack: {attack_type}")
        print("[*] Selected parameters:")
        for k, v in best_params.items():
            print(f"    {k}: {v}")

        start_time = time.time()
        result = attack_engine.execute_attack(attack_type, best_params)
        wait_time = max(1.0, result.get("duration", 1.0)) + 1.0
        time.sleep(wait_time)

        alerts = eve_reader.get_new_alerts(since_timestamp=start_time)

        print(f"\n[+] Attack completed in {result.get('duration',0):.2f}s")
        print(f"[+] Alerts: {len(alerts)}")
        if "metrics" in result:
            print(f"[+] Metrics: {result['metrics']}")

        discovered = result.get("discovered", {})
        if discovered:
            print("\n[+] Information extracted from target:")
            if discovered.get("subdomains"):
                print(f"    Discovered subdomains ({len(discovered['subdomains'])}):")
                for sub in discovered["subdomains"]:
                    print(f"        - {sub}")
            if discovered.get("ip_addresses"):
                print(f"    IP Addresses: {', '.join(discovered['ip_addresses'])}")
            if discovered.get("mx_servers"):
                print(f"    MX Servers: {', '.join(discovered['mx_servers'])}")
            if discovered.get("ns_servers"):
                print(f"    NS Servers: {', '.join(discovered['ns_servers'])}")
            if discovered.get("cnames"):
                print(f"    CNAMEs: {', '.join(discovered['cnames'])}")
            print(f"    Total DNS answers: {discovered.get('total_answers', 0)}")
        else:
            print("[!] No information extracted (no DNS responses)")

        if args.verbose:
            print(f"[DEBUG] Full result: {result}")

        current_state = state_builder.build(
            alerts, result, i, cfg.MAX_STEPS, best_params, action_idx=action_idx
        )

    print("[*] Done.")


if __name__ == "__main__":
    main()
