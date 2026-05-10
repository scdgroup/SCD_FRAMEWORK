# file analysis_tool.py
import os
import sys
import subprocess
from utils.monitor import TrainingMonitor  
from config.env_config import Config
def main():
    # استخدام مجلد logs الذي ينتجه trainer.py
    monitor = TrainingMonitor(save_dir=Config.OUTPUT_DIR_MODEL)     
    print("\n" + "="*50)
    print("   Cyber RL Analysis Mode Selection")
    print("="*50)
    print("Do you want to visualize by Episode or by Step?")
    print("1. Episode Mode (Summarized per episode)")
    print("2. Step Mode (Detailed per individual action)")
    
    mode_choice = input("\nSelect mode (1-2): ").strip()
    mode = "episode" if mode_choice != '2' else "step"
    print(f"[*] Mode set to: {mode.upper()}")

    while True:
        print("\n" + "="*50)
        print(f"   Cyber RL Training Analysis & Visualization Tool ({mode.upper()})")
        print("="*50)
        print(f"1. Generate Full Training Dashboard (All {mode.capitalize()}s)")
        print(f"2. Generate Custom Range Dashboard (Start to End {mode.capitalize()})")
        print("3. Launch Live Training Monitor (Real-time Plotting)")
        print("4. Switch Mode (Episode/Step)")
        print("5. Exit")
        
        try:
            choice = input("\nSelect an option (1-5): ").strip()
        except EOFError:
            break
            
        if choice == '1':
            print(f"[*] Generating full dashboard in {mode} mode...")
            monitor.plot_custom(output_name=f"full_dashboard_{mode}.png", mode=mode)
            
        elif choice == '2':
            print(f"\n--- Custom Range Selection ({mode.capitalize()}s) ---")
            print(f"(Leave blank for default: Start=Beginning, End=Latest)")
            
            try:
                start_input = input(f"Enter Start {mode.capitalize()}: ").strip()
                end_input = input(f"Enter End {mode.capitalize()}: ").strip()
            except EOFError:
                break
                
            start_idx = int(start_input) if start_input.isdigit() else None
            end_idx = int(end_input) if end_input.isdigit() else None
            
            output_name = f"custom_{mode}_{start_idx or 'start'}_to_{end_idx or 'end'}.png"
            print(f"[*] Generating dashboard for range {start_idx or 'start'} to {end_idx or 'end'}...")
            monitor.plot_custom(start_idx=start_idx, end_idx=end_idx, output_name=output_name, mode=mode)
            
        elif choice == '3':
            print(f"[*] Launching Live Monitor in {mode} mode...")
            try:
                subprocess.Popen([sys.executable, "live_monitor.py", "--mode", mode])
                print(f"[+] Live monitor ({mode}) launched in a new window.")
            except Exception as e:
                print(f"[!] Failed to launch live monitor: {e}")
                
        elif choice == '4':
            mode = "step" if mode == "episode" else "episode"
            print(f"[*] Switched to: {mode.upper()}")
            
        elif choice == '5':
            print("[*]Goodby.")
            break
        else:
            print("[!] Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    main()
    
