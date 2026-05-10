import glob
import os
import signal
import sys
import json
import csv
import argparse
import subprocess
import time
import numpy as np
from datetime import datetime
from config.env_config import Config
from config.eval_config import EvalConfig
from env.cyber_env import CyberEnv
from agents.dqn_agent import DQNAgent

sys.path.insert(0, os.path.dirname(__file__))
try:
    from report_generator import EvaluationReport
except ImportError:
    EvaluationReport = None


class UniversalEvaluator:
    def __init__(self, model_path=None, target_domain=None, interface=None):
        self.cfg = Config()
        self.eval_cfg = EvalConfig()
        print(f"\033]0;Universal Recon\a", end="")
        # أولوية: الوسائط > eval_config > config
        target_domain = target_domain or self.cfg.TARGET_DOMAIN
        iface = interface or self.eval_cfg.INTERFACE
        self.suricata_process = None
        m_path = model_path or self.select_model()
        self.model_name = os.path.basename(m_path) if m_path else "trained_model"

        self.cfg.update_network_config(interface=iface, target_domain=target_domain)

        # Start Suricata monitoring if interface is available
        if iface:
            self.suricata_process = self.run_subprocess(iface)
            if self.suricata_process:
                print(
                    f"[+] Suricata started on interface {iface} for recon monitoring."
                )
        else:
            print("[!] No interface specified. Suricata monitoring disabled for recon.")

        # تحميل الوكيل
        self.agent = DQNAgent(state_size=self.cfg.STATE_SIZE, config=self.cfg)
        if m_path and os.path.exists(m_path):
            if self.agent.load(m_path):
                actual_state_size = self.agent.model.input_shape[1]
                if actual_state_size != self.cfg.STATE_SIZE:
                    print(
                        f"[!] Adjusting state size from {self.cfg.STATE_SIZE} to {actual_state_size}"
                    )
                    self.cfg.STATE_SIZE = actual_state_size
            else:
                print(f"[-] Failed to load model from {m_path}")
        else:
            print(f"[!] Model not found: {m_path}. Using untrained agent.")

        # Prompt for episodes and steps after model selection
        self.episodes, self.max_steps = self.prompt_episodes_steps(None, None)

        self.env = CyberEnv(self.cfg)
        self.csv_path = self.eval_cfg.csv_path
        self.json_path = self.eval_cfg.json_path
        self._prepare_logs()

    def select_model(self):
        model_dir = (
            self.eval_cfg.OUTPUT_DIR_MODEL
            if hasattr(self.eval_cfg, "OUTPUT_DIR_MODEL")
            else Config.OUTPUT_DIR_MODEL
        )
        model_pattern = os.path.join(model_dir, "dqn_model_ep*.keras")
        model_files = sorted(glob.glob(model_pattern))
        if not model_files:
            print(f"[!] No model files found in {model_dir}.")
            while True:
                manual_path = input(
                    "Enter the full path to the model file (.keras): "
                ).strip()
                if os.path.exists(manual_path) and manual_path.endswith(".keras"):
                    print(f"[+] Using manual model path: {manual_path}")
                    return manual_path
                print("[!] Invalid path or file does not exist. Please try again.")

        print(f"[+] Found {len(model_files)} model files in {model_dir}:")
        for i, model_file in enumerate(model_files, 1):
            print(f"  {i}. {os.path.basename(model_file)}")
        while True:
            choice = input(
                f"Enter model number (1-{len(model_files)}) or model name: "
            ).strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(model_files):
                    selected_model = model_files[idx]
                    print(f"[+] Selected model: {os.path.basename(selected_model)}")
                    return selected_model
                print(f"Invalid number. Please enter 1-{len(model_files)}.")
            else:
                matching = [f for f in model_files if os.path.basename(f) == choice]
                if matching:
                    selected_model = matching[0]
                    print(f"[+] Selected model: {os.path.basename(selected_model)}")
                    return selected_model
                print(f"No model found with name '{choice}'. Please try again.")

    def _prepare_logs(self):
        if not os.path.exists(self.csv_path):
            headers = [
                "timestamp",
                "model_name",
                "target_domain",
                "episode",
                "step",
                "attack_type",
                "params",
                "success",
                "alerts_count",
                "duration",
                "reward",
                "discovered_count",
                "success_rate",
                "discovered_data",
            ]
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

    def log_to_csv(self, data):
        with open(self.csv_path, "a", newline="") as f:
            csv.writer(f).writerow(data)

    def log_to_json(self, summary_data):
        all_summaries = []
        if os.path.exists(self.json_path):
            with open(self.json_path, "r") as f:
                try:
                    all_summaries = json.load(f)
                except json.JSONDecodeError:
                    pass
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

    def prompt_episodes_steps(self, episodes, max_steps):
        if episodes is None:
            episodes = self.eval_cfg.DEFAULT_EPISODES
        if max_steps is None:
            max_steps = self.eval_cfg.DEFAULT_MAX_STEPS

        while True:
            value = input(f"Enter number of episodes [{episodes}]: ").strip()
            if value == "":
                break
            if value.isdigit() and int(value) > 0:
                episodes = int(value)
                break
            print("Invalid number. Please enter a positive integer.")

        while True:
            value = input(f"Enter max steps per episode [{max_steps}]: ").strip()
            if value == "":
                break
            if value.isdigit() and int(value) > 0:
                max_steps = int(value)
                break
            print("Invalid number. Please enter a positive integer.")

        return episodes, max_steps

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
            # تشغيل الأمر ip route show dev <interface>
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
            print("الأمر 'ip' غير موجود. هل أنت على نظام Linux؟")
            return None

    def run_subprocess(self, INTERFACE=None):
        from config.env_config import Config

        config = Config()
        interface = INTERFACE if INTERFACE else getattr(config, "INTERFACE", None)
        interface = self.choose_interface(interface)
        if not interface:
            print(
                "ERROR: No interface specified. Set INTERFACE in config or pass INTERFACE to run_subprocess."
            )
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

        # إعداد ملف لسجل الأخطاء (يمكنك وضع المسار المناسب)
        log_dir = "/var/log/scdlogs"  # أنشئته سابقاً
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
                # إذا أردت فصله عن الجلسة الحالية (اختياري)
                start_new_session=True,
            )
            # print(f"Started Suricata on {interface} (PID {process.pid})")

            # مراقبة سريعة: انتظر ثانيتين وتأكد أنه ما زال حياً
            time.sleep(2)
            poll = process.poll()
            if poll is not None:
                # خرج بالفعل خلال ثانيتين => خطأ
                print(f"Suricata exited immediately with code {poll}. Check logs.")
                stderr_log.flush()
                # يمكن طباعة آخر سطور من log الخطأ لو أردت
            else:
                # ما زال يعمل، الآن سننظفه عندما ينتهي (حتى لا يبقى زومبي)
                # نقوم بذلك في thread خلفي أو نتركه للأبد إذا كان البرنامج الرئيسي سيستمر
                # لكن لتجنب الزومبي ننتظر في نفس الدالة إذا أردتها أن تبقى معلقة
                # بدلاً من ذلك يمكن إرجاع process وترك المتصل الرئيسي يقرر
                return process  # نعيد الكائن ليتولى المستدعي تنظيفه

        except FileNotFoundError:
            print("ERROR: Suricata command not found. Install it first.")
        except PermissionError:
            print("ERROR: Permission denied. Run with proper capabilities or sudo.")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            # لا نغلق الملفات هنا لأن العملية قد تظل تكتب فيها
            pass

    def run_evaluation(self, episodes=None, max_steps=None):
        episodes = episodes or self.episodes
        max_steps = max_steps or self.max_steps
        print(
            f"[*] Evaluating on {self.cfg.TARGET_DOMAIN} | {episodes} eps, {max_steps} steps"
        )
        if not self.suricata_process or self.suricata_process.poll() is not None:
            self.suricata_process = self.run_subprocess(self.cfg.INTERFACE)
            if self.suricata_process:
                print(
                    f"[+] Suricata started on interface {self.cfg.INTERFACE} for recon monitoring."
                )
        overall_success = 0
        overall_alerts = 0
        total_steps = 0

        for ep in range(episodes):
            state = self.env.reset()
            ep_reward = 0
            ep_success_count = 0
            ep_alerts = 0
            print(f"\n--- Episode {ep+1}/{episodes} ---")

            for step in range(max_steps):
                # اختيار أفضل إجراء (استغلال خالص)
                q_vals = self.agent.model.predict(state.reshape(1, -1), verbose=0)[0]
                action_idx = int(np.argmax(q_vals))
                next_state, reward, done, info = self.env.step(action_idx)

                result = info["attack_result"]
                success = result.get("success", False)
                alerts = info["logs_count"]
                duration = result.get("duration", 0)
                metrics = result.get("metrics", {})
                discovered_count = metrics.get("discovered_count", 0)
                success_rate = metrics.get("success_rate", 0.0)
                discovered_data = result.get("discovered", {})
                discovered_json = json.dumps(discovered_data)

                log_row = [
                    datetime.now().isoformat(),
                    self.model_name,
                    self.cfg.TARGET_DOMAIN,
                    ep + 1,
                    step + 1,
                    info["attack_name"],
                    json.dumps(info["params"]),
                    success,
                    alerts,
                    f"{duration:.4f}",
                    f"{reward:.4f}",
                    discovered_count,
                    f"{success_rate:.3f}",
                    discovered_json,
                ]
                self.log_to_csv(log_row)

                ep_reward += reward
                ep_success_count += 1 if success else 0
                ep_alerts += alerts
                print(
                    f"  Step {step+1}: success={success}, alerts={alerts}, reward={reward:.2f}"
                )

                state = next_state
                total_steps += 1
                if done:
                    break

            avg_reward = ep_reward / (step + 1)  # type: ignore
            print(f"Episode {ep+1} summary: success rate = {ep_success_count/(step+1):.2%}, total alerts = {ep_alerts}")  # type: ignore
            overall_success += ep_success_count
            overall_alerts += ep_alerts

        final = {
            "evaluation_date": datetime.now().isoformat(),
            "report_type": "recon",
            "target_domain": self.cfg.TARGET_DOMAIN,
            "interface": self.cfg.INTERFACE,
            "total_episodes": episodes,
            "max_steps": max_steps,
            "overall_success_rate": (
                overall_success / total_steps if total_steps > 0 else 0
            ),
            "total_alerts": overall_alerts,
            "suricata_monitoring": bool(
                self.suricata_process and self.suricata_process.poll() is None
            ),
            "results_dir": self.eval_cfg.OUTPUT_DIR,
        }
        self.log_to_json(final)
        print(
            f"\n=== Evaluation Complete ===\nSuccess Rate: {final['overall_success_rate']:.2%}\nTotal Alerts: {overall_alerts}"
        )
        print(f"Detailed logs saved to: {self.csv_path}")

        if EvaluationReport:
            try:
                report = EvaluationReport(result_dir=self.eval_cfg.OUTPUT_DIR)
                report.generate_report(open_browser=True)
                print("[+] Recon report generated and opened successfully.")
            except Exception as e:
                print(f"[!] Failed to generate recon report: {e}")

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
        description="Universal Evaluator for DNS Recon RL Agent"
    )
    parser.add_argument("--model", help="Path to .keras model file")
    parser.add_argument("--target-domain", help="Target domain (e.g., example.com)")
    parser.add_argument("--interface", help="Network interface")
    parser.add_argument("--episodes", type=int, help="Number of episodes")
    parser.add_argument("--steps", type=int, help="Max steps per episode")
    args = parser.parse_args()

    evaluator = UniversalEvaluator(
        model_path=args.model,
        target_domain=args.target_domain,
        interface=args.interface,
    )
    evaluator.run_evaluation(episodes=args.episodes, max_steps=args.steps)
    evaluator.close_terminal_window()
    # subprocess.run(["pkill", "-f", "universal_recon.py"], check=False)
