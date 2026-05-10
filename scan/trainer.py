import argparse
import time
import os
import re
import sys
from config.env_config import Config
from env.cyber_env import CyberEnv
from agents.dqn_agent import DQNAgent
from utils.monitor import TrainingMonitor


def check_checkpoint_files(folder, ep):
    """Check if all required checkpoint files exist for a given episode."""
    model = os.path.join(folder, f"dqn_model_ep{ep}.keras")
    memory = os.path.join(folder, f"dqn_memory_ep{ep}.pkl")
    epsilon = os.path.join(folder, f"dqn_epsilon_ep{ep}.json")

    missing = []
    if not os.path.exists(model):
        missing.append("Full Model (.keras)")
    if not os.path.exists(memory):
        missing.append("Memory (.pkl)")
    if not os.path.exists(epsilon):
        missing.append("Epsilon (.json)")

    return len(missing) == 0, missing


def list_saved_checkpoints(folder):
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
    parser.add_argument(
        "--target-ip", default=Config.TARGET_IP, help="Target IP address"
    )
    parser.add_argument(
        "--interface", default=Config.INTERFACE, help="Network interface"
    )
    args = parser.parse_args()

    cfg = Config()
    cfg.update_network_config(target_ip=args.target_ip, interface=args.interface)

    # Initialize Environment, Agent, and Monitor
    env = CyberEnv(cfg)
    agent = DQNAgent(state_size=cfg.STATE_SIZE, config=cfg)
    monitor = TrainingMonitor(save_dir=Config.OUTPUT_DIR)

    # --- Interactive Startup Menu ---
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
            print("[*] Starting fresh training session...")
            # If starting fresh, we might want to archive old logs, but for now we append as requested
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
            exists, missing = check_checkpoint_files(Config.OUTPUT_DIR_MODEL, ep_num)
            if exists:
                model_path = os.path.join(
                    Config.OUTPUT_DIR_MODEL, f"dqn_model_ep{ep_num}.keras"
                )
                memory_path = os.path.join(
                    Config.OUTPUT_DIR_MODEL, f"dqn_memory_ep{ep_num}.pkl"
                )
                epsilon_path = os.path.join(
                    Config.OUTPUT_DIR_MODEL, f"dqn_epsilon_ep{ep_num}.json"
                )
                agent.load_checkpoint(model_path, memory_path, epsilon_path)
                start_ep = ep_num
                print(f"[*] Successfully loaded checkpoint from episode {ep_num}.")
                break
            else:
                print(
                    f"[!] Error: Missing files for episode {ep_num}: {', '.join(missing)}"
                )
                print("[*] Returning to main menu...")
        elif choice == "3":
            print("[*] Exiting...")
            sys.exit(0)
        else:
            print("[!] Invalid choice. Please select 1, 2, or 3.")

    print(f"[*] Training all scan attacks against {cfg.TARGET_IP} on {cfg.INTERFACE}")
    print(f"[*] Total action space size: {agent.action_size}")
    print(f"[*] State size: {cfg.STATE_SIZE}")
    print(f"[*] Saving model every {cfg.SAVE_INTERVAL} episodes")

    os.makedirs(Config.OUTPUT_DIR_MODEL, exist_ok=True)

    for ep in range(start_ep, cfg.EPISODES):
        state = env.reset()
        total_reward = 0
        total_alerts = 0
        success_count = 0
        start_time = time.time()

        for step in range(cfg.MAX_STEPS):
            # Agent chooses an action index
            action_idx = agent.act(state)

            # Environment executes the action
            next_state, reward, done, info = env.step(action_idx)

            attack_name = info["attack_name"]
            params = info["params"]
            result = info["attack_result"]

            print(
                f"\n[Episode {ep+1} Step {step+1}] Attack: {attack_name}, Params: {params}"
            )
            print(
                f"  Result: success={result.get('success')}, duration={result.get('duration',0):.2f}s, alerts={info['logs_count']}"
            )

            if "port_results" in result:
                open_ports = [
                    p
                    for p in result["port_results"]
                    if p["state"] in ["open", "open_or_filtered", "unfiltered"]
                ]
                if open_ports:
                    print(f"  Detected ports: {open_ports}")

            # Store experience and train
            agent.remember(state, action_idx, reward, next_state, done)
            agent.replay(cfg.BATCH_SIZE)

            # Update step monitor (New)
            monitor.update_step(
                episode=ep + 1,
                step=step + 1,
                reward=reward,
                alerts=info.get("logs_count", 0),
                success=result.get("success", False),
                attack_name=attack_name,
            )

            state = next_state
            total_reward += reward
            total_alerts += info.get("logs_count", 0)
            if result.get("success"):
                success_count += 1

            if done:
                break

        agent.update_target_model_hard()
        duration = time.time() - start_time

        # Update monitor (Appends to CSV)
        monitor.update(
            episode=ep + 1,
            reward=total_reward,
            epsilon=agent.epsilon,
            alerts=total_alerts,
            success=(success_count > 0),
        )

        # Note: Automatic plotting removed as requested.
        # Use analysis_tool.py or live_monitor.py for visualization.

        print(
            f"Episode {ep+1} finished, total reward: {total_reward:.2f}, epsilon: {agent.epsilon:.4f}, time: {duration:.1f}s"
        )

        if (ep + 1) % cfg.SAVE_INTERVAL == 0:
            agent.save_checkpoint(Config.OUTPUT_DIR_MODEL, ep + 1)

    agent.save_checkpoint(Config.OUTPUT_DIR_MODEL, "final")
    print(f"[*] Training completed.")


if __name__ == "__main__":
    train()
