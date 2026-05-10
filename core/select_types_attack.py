import os
import shlex
import subprocess
import sys
from core.my_enums import setup_readline, option_choice, menu_attack

setup_readline()


def launch_Attack_terminal(type_of_attack="exploit", file_name="run_attack_exploit.py"):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir and not os.path.exists(os.path.join(current_dir, type_of_attack)):
        current_dir = os.path.dirname(current_dir)

    if not current_dir:
        print("Could not locate project root.")
        return

    attack_dir = os.path.join(current_dir, type_of_attack)
    script_path = os.path.join(attack_dir, file_name)

    if not os.path.isdir(attack_dir):
        print(f"Error: attack folder not found at {attack_dir}")
        return

    if not os.path.isfile(script_path):
        print(f"Error: file not found at {script_path}")
        return

    python_cmd = shlex.join([sys.executable, script_path])
    command = f"cd {shlex.quote(attack_dir)} && {python_cmd}; exec bash"

    cols = 100
    rows = 30
    geometry = f"{cols}x{rows}+0+0"

    terminals = [
        ["gnome-terminal", "--geometry", geometry, "--", "bash", "-c", command],
        ["xterm", "-geometry", geometry, "-e", "bash", "-c", command],
        ["konsole", "--geometry", geometry, "-e", "bash", "-c", command],
        ["xfce4-terminal", "--geometry", geometry, "-e", "bash", "-c", command],
    ]
    launched = False
    for term_cmd in terminals:
        try:
            subprocess.Popen(term_cmd)
            launched = True
            break
        except FileNotFoundError:
            continue
    if not launched:
        print("No suitable terminal emulator found. Please run manually:")
        print(f"  cd {attack_dir} && python {script_path}")


# Helper
def clear_screen():
    if sys.platform.startswith("win"):
        os.system("cls")
    else:
        os.system("clear")

    # print("=" * 50)


def show_attack_menu(rad_use):
    clear_screen()
    menu_attack(rad_use)
    whereme = "typesAttack"
    while True:
        choice = option_choice(whereme)
        if choice == "0":
            return "back"
        elif choice == "1":
            print("Start Scan Attacks...")
            return '1'
            # input("Press Enter to continue...")
        elif choice == "2":
            print("Start Exploit Attacks...")
            return '2'
            # input("Press Enter to continue...")
        elif choice == "3":
            print("Start Service Exploitation...")
            return '3'
            # input("Press Enter to continue...")
        elif choice == "4":
            print("Start Network Reconnaissance...")

            # input("Press Enter to continue...")
        elif choice == "5" or choice == "exit" or choice == "e":
            # print("\nThank you for using SCD Framework. Goodbye!")
            return "exit"
            # sys.exit(0)
        elif (
            choice != "1"
            and choice != "2"
            and choice != "3"
            and choice != "4"
            and choice != "5"
        ):
            from core.my_enums import others_choice

            others_choice(choice, "types")
        else:
            print("\nInvalid choice. Please try again.")
