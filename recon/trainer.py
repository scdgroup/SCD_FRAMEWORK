import argparse
import time
import os
import re
import sys
from config.env_config import Config
from env.cyber_env import CyberEnv
from agents.dqn_agent import DQNAgent
from utils.monitor import TrainingMonitor


def list_saved_checkpoints(folder):
    """Return sorted checkpoint episodes available in the folder."""
    if not os.path.exists(folder):
        return []
    episodes = []
    for filename in os.listdir(folder):
        match = re.match(r"^dqn_model_ep(\d+)\.keras$", filename)
        if match:
            episodes.append(int(match.group(1)))
    return sorted(set(episodes))


def train():
    parser = argparse.ArgumentParser()
    # parser.add_argument("--target-ip", required=False, help="Target IP address")
    parser.add_argument(
        "--interface", default=Config.INTERFACE, help="Network interface"
    )
    parser.add_argument(
        "--target-domain",
        default=Config.TARGET_DOMAIN,
        help="Target domain (e.g., example.com)",
    )
    args = parser.parse_args()

    cfg = Config()
    cfg.update_network_config(
        interface=args.interface,
        target_domain=args.target_domain,
        # target_ip=args.target_ip
    )

    # Initialize components
    env = CyberEnv(cfg)
    agent = DQNAgent(state_size=cfg.STATE_SIZE, config=cfg)
    monitor = TrainingMonitor(save_dir=Config.OUTPUT_DIR_MODEL)

    # --- Interactive resume menu ---
    start_ep = 0
    while True:
        print("\n" + "=" * 40)
        print("   Cyber RL Training - Startup Menu")
        print("=" * 40)
        print("1. Start New Training (From Scratch)")
        print("2. Resume Training (From Checkpoint)")
        print("3. Exit")
        try:
            choice = input("\nSelect an option (1-3): ").strip()
        except EOFError:
            choice = "1"
        if choice == "1":
            break
        elif choice == "2":
            available = list_saved_checkpoints(Config.OUTPUT_DIR_MODEL)
            if not available:
                print("[!] No saved checkpoints found in the output directory.")
                continue
            print("\n[+] Saved checkpoints available:")
            for idx, ep_num in enumerate(available, 1):
                print(f"  {idx}. Episode {ep_num}")
            try:
                resume_choice = input(
                    "[?] Select the checkpoint number to resume from: "
                ).strip()
            except EOFError:
                print("[!] Input not available. Returning to main menu.")
                continue
            if not resume_choice.isdigit():
                print("[!] Error: Please enter a valid numeric choice.")
                continue
            selected_index = int(resume_choice) - 1
            if selected_index < 0 or selected_index >= len(available):
                print("[!] Invalid selection. Please choose a listed checkpoint.")
                continue
            ep_num = available[selected_index]
            try:
                agent.load_checkpoint(Config.OUTPUT_DIR_MODEL, ep_num)
                start_ep = ep_num
                print(f"[*] Successfully loaded checkpoint from episode {ep_num}.")
                break
            except Exception as e:
                print(f"[!] Failed to load checkpoint: {e}")
                continue
        elif choice == "3":
            sys.exit(0)
        else:
            print("[!] Invalid choice")

    print(
        f"\n[*] Training against  {cfg.TARGET_DOMAIN} on {cfg.INTERFACE}"
    )  # {cfg.TARGET_IP} /
    print(f"[*] Action space size: {agent.action_size}")
    print(f"[*] State size: {cfg.STATE_SIZE}")
    print(f"[*] Saving every {cfg.SAVE_INTERVAL} episodes")

    os.makedirs(Config.OUTPUT_DIR_MODEL, exist_ok=True)

    for ep in range(start_ep, cfg.EPISODES):
        state = env.reset()
        total_reward = 0
        total_alerts = 0
        success_count = 0
        start_time = time.time()

        for step in range(cfg.MAX_STEPS):
            action_idx = agent.act(state)
            next_state, reward, done, info = env.step(action_idx)

            attack_name = info["attack_name"]
            params = info["params"]
            result = info["attack_result"]

            print(f"\n[Episode {ep+1} Step {step+1}] Attack: {attack_name}")
            print(f"  Params: {params}")
            print(
                f"  Result: success={result.get('success')}, duration={result.get('duration',0):.2f}s, alerts={info['logs_count']}"
            )

            # تسجيل الخطوة في monitor
            monitor.update_step(
                episode=ep + 1,
                step=step + 1,
                reward=reward,
                alerts=info.get("logs_count", 0),
                success=result.get("success", False),
                attack_name=attack_name,
            )

            agent.remember(state, action_idx, reward, next_state, done)
            agent.replay(cfg.BATCH_SIZE)

            state = next_state
            total_reward += reward
            total_alerts += info.get("logs_count", 0)
            if result.get("success"):
                success_count += 1

            if done:
                break

        agent.update_target_model_hard()
        duration = time.time() - start_time

        # تسجيل الحلقة في monitor
        monitor.update(
            episode=ep + 1,
            reward=total_reward,
            epsilon=agent.epsilon,
            alerts=total_alerts,
            success=(success_count > 0),
        )

        print(
            f"Episode {ep+1} finished | Reward: {total_reward:.2f} | Epsilon: {agent.epsilon:.4f} | Time: {duration:.1f}s"
        )

        if (ep + 1) % cfg.SAVE_INTERVAL == 0:
            agent.save_checkpoint(Config.OUTPUT_DIR_MODEL, ep + 1)

    agent.save_checkpoint(Config.OUTPUT_DIR_MODEL, "final")
    print("[*] Training completed.")


if __name__ == "__main__":
    train()
