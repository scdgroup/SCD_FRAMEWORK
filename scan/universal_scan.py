import glob
import os
import sys
import json
import csv
import argparse
import signal
import subprocess
import time
import numpy as np
from datetime import datetime

# Project-specific imports
from config.env_config import Config
from config.eval_config import EvalConfig
from env.cyber_env import CyberEnv
from agents.dqn_agent import DQNAgent

# Ensure local package directory is on sys.path for script execution from project root
sys.path.insert(0, os.path.dirname(__file__))
try:
    from report_generator import EvaluationReport
except ImportError:
    EvaluationReport = None


class UniversalEvaluator:
    @staticmethod
    def select_model(default_path=None):
        model_dir = os.path.dirname(default_path) if default_path else os.getcwd()
        pattern = os.path.join(model_dir, "*.keras")
        saved_models = sorted(glob.glob(pattern))

        if not saved_models:
            print(f"[!] No saved .keras models found in {model_dir}.")
            return default_path

        print("Select a model file:")
        for idx, model in enumerate(saved_models, start=1):
            print(f"  {idx}. {os.path.basename(model)}")
        print("  0. Keep default model path")

        while True:
            selection = input(
                "Choose model number or press Enter to keep default: "
            ).strip()
            if selection == "" or selection == "0":
                return default_path
            if selection.isdigit() and 1 <= int(selection) <= len(saved_models):
                return saved_models[int(selection) - 1]
            print("Invalid selection. Enter a valid number.")

    def __init__(self, model_path=None, target_ip=None, interface=None):
        # Load Configurations
        self.cfg = Config()
        self.eval_cfg = EvalConfig()
        print(f"\033]0;Universal Scan\a", end="")
        # Priority: Command line args > EvalConfig > EnvConfig
        target = target_ip or self.eval_cfg.TARGET_IP
        iface = interface or self.eval_cfg.INTERFACE
        m_path = model_path or self.eval_cfg.DEFAULT_MODEL_PATH
        if model_path is None:
            m_path = self.select_model(default_path=m_path)

        # Update Network Config
        self.cfg.update_network_config(target_ip=target, interface=iface)

        self.suricata_process = None
        if iface:
            self.suricata_process = self.run_subprocess(iface)
            if self.suricata_process:
                print(f"[+] Suricata started on interface {iface} for scan monitoring.")
        else:
            print("[!] No interface specified. Suricata monitoring disabled for scan.")

        # Load Model and dynamically adjust STATE_SIZE
        self.model_name = os.path.basename(m_path) if m_path else "trained_model"
        self.agent = DQNAgent(state_size=self.cfg.STATE_SIZE, config=self.cfg)
        if m_path and os.path.exists(m_path):
            try:
                if self.agent.load(m_path):
                    actual_state_size = self.agent.model.input_shape[1]
                    if actual_state_size != self.cfg.STATE_SIZE:
                        print(
                            f"[!] Warning: Model state size ({actual_state_size}) differs from current config ({self.cfg.STATE_SIZE}). Adjusting..."
                        )
                        self.cfg.STATE_SIZE = actual_state_size
                else:
                    print(f"[-] Failed to load model from: {m_path}")
            except Exception as e:
                print(f"[-] Error during model loading: {e}")
        else:
            print(
                f"[!] Warning: Model file not found at {m_path}. Running with uninitialized weights."
            )

        # Prompt for episodes and steps after model selection
        self.episodes, self.max_steps = self.prompt_episodes_steps(None, None)

        # Initialize Env with adjusted config
        self.env = CyberEnv(self.cfg)

        # Logging Paths from eval_config
        self.csv_path = self.eval_cfg.csv_path
        self.json_path = self.eval_cfg.json_path

        self._prepare_logs()

    def _prepare_logs(self):
        """Prepares CSV headers if file doesn't exist."""
        if not os.path.exists(self.csv_path):
            headers = [
                "timestamp",
                "model_name",
                "target_ip",
                "episode",
                "step",
                "attack_type",
                "params",
                "success",
                "alerts_count",
                "duration",
                "reward",
                "status_code",
                "payload",
            ]
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

    def log_to_csv(self, data):
        """Appends a single step data to CSV."""
        with open(self.csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(data)

    def log_to_json(self, summary_data):
        """Appends summary data to a JSON list without overwriting."""
        all_summaries = []
        if os.path.exists(self.json_path):
            with open(self.json_path, "r") as f:
                try:
                    all_summaries = json.load(f)
                except json.JSONDecodeError:
                    all_summaries = []

        all_summaries.append(summary_data)
        with open(self.json_path, "w") as f:
            json.dump(all_summaries, f, indent=4)

    def _get_process_name(self, pid):
        try:
            output = subprocess.run(
                ["ps", "-p", str(pid), "-o", "comm="],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            return output
        except Exception:
            return ""

    def _get_parent_pid(self, pid):
        try:
            output = subprocess.run(
                ["ps", "-p", str(pid), "-o", "ppid="],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            return int(output) if output and output.isdigit() else None
        except Exception:
            return None

    def close_terminal_window(self):
        if not sys.stdout.isatty():
            return False

        parent_pid = os.getppid()
        if parent_pid <= 1:
            return False

        parent_name = self._get_process_name(parent_pid)
        known_terminals = {
            "gnome-terminal",
            "gnome-terminal-",
            "xterm",
            "konsole",
            "xfce4-terminal",
            "terminator",
            "mate-terminal",
            "tilix",
            "alacritty",
            "kitty",
            "urxvt",
            "lxterminal",
            "st",
        }
        shells = {"bash", "zsh", "sh", "dash", "ksh", "fish"}

        if parent_name in shells:
            grandparent_pid = self._get_parent_pid(parent_pid)
            grandparent_name = (
                self._get_process_name(grandparent_pid)
                if grandparent_pid
                else ""
            )
            if grandparent_name in known_terminals:
                print("[+] Closing terminal emulator window...")
                try:
                    os.kill(grandparent_pid, signal.SIGTERM)
                    return True
                except Exception as e:
                    print(f"[!] Failed to kill terminal emulator: {e}")
                    return False

        if parent_name in known_terminals:
            print("[+] Closing terminal emulator window...")
            try:
                os.kill(parent_pid, signal.SIGTERM)
                return True
            except Exception as e:
                print(f"[!] Failed to kill terminal emulator: {e}")
                return False

        return False

    def choose_interface(self, interface):
        if interface:
            return interface

        try:
            result = subprocess.run(
                ["ip", "link", "show"], capture_output=True, text=True, check=False
            )
            interfaces = []
            for line in result.stdout.splitlines():
                if ": " in line and "LOOPBACK" not in line.upper():
                    intf = line.split(": ")[1].split("@")[0].strip()
                    interfaces.append(intf)

            if not interfaces:
                print("[!] No network interfaces found.")
                return None

            print("[+] Available interfaces:")
            for idx, intf in enumerate(interfaces, 1):
                print(f"  {idx}. {intf}")

            while True:
                choice = input(
                    "Select interface number for Suricata monitoring or press Enter to skip: "
                ).strip()
                if choice == "":
                    return None
                if choice.isdigit() and 1 <= int(choice) <= len(interfaces):
                    return interfaces[int(choice) - 1]
                print("Invalid choice. Please enter a valid number.")
        except Exception as e:
            print(f"[!] Could not list interfaces: {e}")
            return None

    def get_network_from_interface(self, interface):
        try:
            result = subprocess.run(
                ["ip", "route", "show", "dev", interface],
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stdout.strip()
            if output:
                network = output.split()[0]
                if "/" in network:
                    return network

            result = subprocess.run(
                ["ip", "-o", "-f", "inet", "addr", "show", interface],
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stdout.strip()
            if output:
                # Example: 2: eth0    inet 192.168.1.10/24 brd 192.168.1.255 scope global eth0
                parts = output.split()
                if "inet" in parts:
                    inet_index = parts.index("inet")
                    if inet_index + 1 < len(parts):
                        addr = parts[inet_index + 1]
                        if "/" in addr:
                            return addr

            print(f"[!] Could not determine network CIDR for interface {interface}.")
            return None
        except FileNotFoundError:
            print("Command 'ip' not found. Are you on Linux?")
            return None

    def run_subprocess(self, interface=None):
        interface = self.choose_interface(interface)
        if not interface:
            print("[!] Suricata monitoring skipped: no interface selected.")
            return None

        network = self.get_network_from_interface(interface)
        if not network:
            print(f"ERROR: unable to determine network for interface {interface}.")
            interface = self.choose_interface(None)
            if not interface:
                return None
            network = self.get_network_from_interface(interface)
            if not network:
                print(
                    f"ERROR: still unable to determine network for interface {interface}."
                )
                return None

        self.cfg.INTERFACE = interface

        log_dir = "/var/log/scdlogs"
        os.makedirs(log_dir, exist_ok=True)
        stdout_log = open(os.path.join(log_dir, "suricata_out.log"), "w")
        stderr_log = open(os.path.join(log_dir, "suricata_err.log"), "w")

        try:
            cmd = [
                "suricata",
                "-c",
                "/etc/suricata/suricata.yaml",
                "--set",
                f"vars.address-groups.HOME_NET=[{network}]",
                "-i",
                interface,
            ]
            process = subprocess.Popen(
                cmd,
                stdout=stdout_log,
                stderr=stderr_log,
                start_new_session=True,
            )
            time.sleep(2)
            if process.poll() is not None:
                print(
                    f"Suricata exited immediately with code {process.poll()}. Check logs."
                )
                return None
            return process
        except FileNotFoundError:
            print("ERROR: Suricata command not found. Install it first.")
        except PermissionError:
            print("ERROR: Permission denied. Run with proper capabilities or sudo.")
        except Exception as e:
            print(f"Unexpected error: {e}")
        return None

    def prompt_episodes_steps(self, episodes, max_steps):
        if episodes is None:
            while True:
                value = input(
                    f"Enter number of episodes [{self.eval_cfg.DEFAULT_EPISODES}]: "
                ).strip()
                if value == "":
                    episodes = self.eval_cfg.DEFAULT_EPISODES
                    break
                if value.isdigit() and int(value) > 0:
                    episodes = int(value)
                    break
                print("Invalid number. Please enter a positive integer.")

        if max_steps is None:
            while True:
                value = input(
                    f"Enter max steps per episode [{self.eval_cfg.DEFAULT_MAX_STEPS}]: "
                ).strip()
                if value == "":
                    max_steps = self.eval_cfg.DEFAULT_MAX_STEPS
                    break
                if value.isdigit() and int(value) > 0:
                    max_steps = int(value)
                    break
                print("Invalid number. Please enter a positive integer.")

        return episodes, max_steps

    def run_evaluation(self, episodes=None, max_steps=None):
        episodes = episodes or self.episodes
        max_steps = max_steps or self.max_steps
        # print()
        print(f"[*] Starting Evaluation: {episodes} episodes, {max_steps} steps each.")
        if not self.suricata_process or self.suricata_process.poll() is not None:
            self.suricata_process = self.run_subprocess(self.cfg.INTERFACE)
            if self.suricata_process:
                print(
                    f"[+] Suricata started on interface {self.cfg.INTERFACE} for scan monitoring."
                )
        overall_success = 0
        overall_alerts = 0

        model_name = self.model_name

        for ep in range(episodes):
            state = self.env.reset()
            if len(state) != self.cfg.STATE_SIZE:
                print(
                    f"[!] Error: Environment state size ({len(state)}) does not match model ({self.cfg.STATE_SIZE})"
                )
                break

            ep_reward = 0
            ep_success_count = 0
            ep_alerts = 0

            print(f"\n--- Episode {ep+1}/{episodes} ---")

            for step in range(max_steps):
                # Agent chooses best action
                action_idx = np.argmax(
                    self.agent.model.predict(state.reshape(1, -1), verbose=0)[0]
                )

                next_state, reward, done, info = self.env.step(action_idx)

                # Extract details
                attack_name = info["attack_name"]
                params = info["params"]
                result = info["attack_result"]
                success = result.get("success", False)
                alerts = info["logs_count"]
                duration = result.get("duration", 0)
                status = result.get("status_code", 0)
                payload = result.get("payload", "")

                # Prepare CSV row
                log_row = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    model_name,
                    self.cfg.TARGET_IP,
                    ep + 1,
                    step + 1,
                    attack_name,
                    json.dumps(params),
                    success,
                    alerts,
                    f"{duration:.4f}",
                    f"{reward:.4f}",
                    status,
                    payload,
                ]
                self.log_to_csv(log_row)

                # Update counters
                ep_reward += reward
                if success:
                    ep_success_count += 1
                ep_alerts += alerts

                print(
                    f"Step {step+1}: {attack_name} | Success: {success} | Alerts: {alerts} | Reward: {reward:.2f}"
                )

                state = next_state
                if done:
                    break

            # Episode Summary
            ep_summary = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "episode": ep + 1,
                "total_steps": step + 1,  # type: ignore
                "success_rate": ep_success_count / (step + 1),  # type: ignore
                "total_alerts": ep_alerts,
                "avg_reward": ep_reward / (step + 1),  # type: ignore
            }
            print(
                f"Episode Summary -> Success Rate: {ep_summary['success_rate']:.2%}, Total Alerts: {ep_alerts}"
            )

            overall_success += ep_success_count
            overall_alerts += ep_alerts

        # Final Evaluation Summary
        final_summary = {
            "evaluation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_type": "scan",
            "target_ip": self.cfg.TARGET_IP,
            "interface": self.cfg.INTERFACE,
            "total_episodes": episodes,
            "max_steps": max_steps,
            "overall_success_rate": (
                overall_success / (episodes * max_steps) if episodes > 0 else 0
            ),
            "total_alerts_generated": overall_alerts,
            "suricata_monitoring": bool(
                self.suricata_process and self.suricata_process.poll() is None
            ),
            "results_dir": self.eval_cfg.OUTPUT_DIR,
        }
        self.log_to_json(final_summary)

        print("\n" + "=" * 30)
        print("EVALUATION COMPLETE")
        print(f"Overall Success Rate: {final_summary['overall_success_rate']:.2%}")
        print(f"Total Alerts: {overall_alerts}")
        print(f"Detailed logs saved to: {self.csv_path}")
        print("=" * 30)

        if EvaluationReport:
            try:
                report = EvaluationReport(result_dir=self.eval_cfg.OUTPUT_DIR)
                report.generate_report(open_browser=True)
                print("[+] Scan report generated and opened successfully.")
            except Exception as e:
                print(f"[!] Failed to generate scan report: {e}")

        if self.suricata_process and self.suricata_process.poll() is None:
            print("[+] Stopping Suricata...")
            self.suricata_process.terminate()
            try:
                self.suricata_process.wait(timeout=5)
                print("[+] Suricata stopped.")
            except subprocess.TimeoutExpired:
                self.suricata_process.kill()
                print("[!] Suricata force killed.")

    def __del__(self):
        if (
            hasattr(self, "suricata_process")
            and self.suricata_process
            and self.suricata_process.poll() is None
        ):
            self.suricata_process.terminate()
            try:
                self.suricata_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.suricata_process.kill()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Universal Model Evaluator for RL Cyber Models"
    )
    parser.add_argument(
        "--model", type=str, help="Path to the trained model file (.keras or .h5)"
    )
    parser.add_argument("--target", type=str, help="Target IP address for evaluation")
    parser.add_argument(
        "--interface", type=str, help="Network interface for evaluation"
    )
    parser.add_argument("--episodes", type=int, help="Number of episodes to run")
    parser.add_argument("--steps", type=int, help="Max steps per episode")

    args = parser.parse_args()

    evaluator = UniversalEvaluator(
        model_path=args.model, target_ip=args.target, interface=args.interface
    )
    evaluator.run_evaluation(episodes=args.episodes, max_steps=args.steps)
    evaluator.close_terminal_window()
    # subprocess.run(["pkill", "-f", "universal_scan.py"], check=False)
