import os
import sys
import subprocess
import time
from config.env_config import Config
from utils.monitor import TrainingMonitor


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def main():
    monitor = TrainingMonitor(save_dir=Config.OUTPUT_DIR)

    # Initial Mode Selection
    clear_screen()
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "Cyber RL Analysis & Visualization" + " " * 15 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\nSelect Visualization Granularity:")
    print("  [1] Episode Mode - Focus on long-term training trends")
    print("  [2] Step Mode    - Focus on individual action performance")

    while True:
        choice = input("\nChoice (1-2): ").strip()
        if choice in ["1", "2"]:
            mode = "episode" if choice == "1" else "step"
            break
        print("[!] Please enter 1 or 2.")

    while True:
        clear_screen()
        print("\n" + "═" * 60)
        print(f"   ACTIVE MODE: {mode.upper()}")
        print("═" * 60)
        print(f"1. Generate Full Dashboard (All {mode}s)")
        print(f"2. Generate Custom Range Dashboard")
        print(f"3. Launch Live {mode.capitalize()} Monitor")
        print(f"4. SWITCH MODE (Current: {mode})")
        print("5. Exit")
        print("═" * 60)

        try:
            cmd = input("\nSelection (1-5): ").strip()
        except EOFError:
            break

        if cmd == "1":
            out_file = f"full_dashboard_{mode}.png"
            print(f"[*] Processing {mode} data...")
            monitor.plot_custom(output_name=out_file, mode=mode)
            input("\nPress Enter to continue...")

        elif cmd == "2":
            print(f"\n--- Custom {mode.capitalize()} Range ---")
            s_val = input(f"Start {mode} index (blank for 1): ").strip()
            e_val = input(f"End {mode} index (blank for latest): ").strip()

            start = int(s_val) if s_val.isdigit() else None
            end = int(e_val) if e_val.isdigit() else None

            out_file = f"custom_{mode}_{start or 'start'}_to_{end or 'end'}.png"
            monitor.plot_custom(
                start_idx=start, end_idx=end, output_name=out_file, mode=mode
            )
            input("\nPress Enter to continue...")

        elif cmd == "3":
            print(f"[*] Launching Live Monitor in {mode} mode...")
            try:
                # Use subprocess to launch live monitor with the explicit mode
                subprocess.Popen([sys.executable, "live_monitor.py", "--mode", mode])
                print(f"[+] Live monitor started. Check the new window.")
                time.sleep(2)  # Small pause
            except Exception as e:
                print(f"[!] Error: {e}")
            input("\nPress Enter to continue...")

        elif cmd == "4":
            mode = "step" if mode == "episode" else "episode"
            print(f"[*] Mode switched to: {mode.upper()}")

        elif cmd == "5":
            print("[*] Goodbye.")
            break
        else:
            print("[!] Invalid option.")


if __name__ == "__main__":
    main()
