import os
import random
import sys
import signal
import subprocess
from core.select_types_attack import show_attack_menu, launch_Attack_terminal
from core.my_enums import train
from core.train_main import launch_moitor_terminal, launch_training_terminal as run_train
from core.monitoring import monitoring_menu

#  🐒  🐧
try:
    from core.my_enums import (
        setup_readline,
        option_choice,
        others_choice,  # type: ignore
        clear_screen,
        setup_environment,
        main_welcome_message as welcome_message,
    )
except Exception as exc:
    print("Warning: some dependencies failed to load.")
    print("This tool can still run setup and show the main menu.")
    print(f"Missing package error: {exc.__class__.__name__}: {exc}")

    def setup_readline():
        pass

    def option_choice(whereme):
        print("\nAvailable choices:")
        print("5. setup")
        print("0. exit")
        return input("SCD/main> ").strip()

    def others_choice(choice, whereme):
        if choice in ("exit", "0"):
            sys.exit(0)
        print("Invalid choice.")

    def clear_screen():
        pass

    def setup_environment():
        pass

    def welcome_message(rad_use):
        print("SCD Framework - Main Menu")
        print("1. train (unavailable)")
        print("2. test model (unavailable)")
        print("3. attack (unavailable)")
        print("4. monitoring (unavailable)")
        print("5. setup")
        print("0. exit")


if callable(setup_readline):
    setup_readline()


def signal_handler(sig, frame):
    print("\nYou pressed Ctrl+C. Exiting gracefully...")
    others_choice("exit", "main")


def main():
    if os.geteuid() != 0:
        print("(sudo) recommended for full operation. Continuing in user mode...")
        print("Enter (sudo su) and try use python main")
        sys.exit(1)
    signal.signal(signal.SIGINT, signal_handler)
    rad_use=random.randint(0, 1)
    welcome_message(rad_use)

    whereme = "main"
    try:
        while True:
            choice = option_choice(whereme)
            if choice == "1":  # train
                result_train = train(rad_use)
                if result_train == "back":
                    clear_screen()
                    welcome_message(rad_use)
                elif result_train == "1": # scan

                    run_train(type_of_attack="scan", file_name="train_scan.py")
                    print('press Enter if you want to monitor ')
                    d = option_choice('Train/option')
                    if d.lower() == "back" or d.lower() == "b" or d.lower() == "0":
                        clear_screen()
                        welcome_message(rad_use)
                    elif d.lower() == "exit":
                        others_choice(d, 'main')
                    else:

                        print("Launching monitoring terminal...")
                        launch_moitor_terminal(
                            type_of_attack="scan", file_name="analysis_tool.py"
                        )

                elif result_train == "2": # recon
                    run_train(type_of_attack="recon", file_name="train_recon.py")
                    print('press Enter if you want to monitor ')
                    d = option_choice('Train/option')
                    if d.lower() == "back" or d.lower() == "b" or d.lower() == "0":
                        clear_screen()
                        welcome_message(rad_use)
                    elif d.lower() == "exit":
                        others_choice(d, 'main')
                    else:

                        print("Launching monitoring terminal...")
                        launch_moitor_terminal(
                            type_of_attack="recon", file_name="analysis_tool.py"
                        )
                
                elif result_train == "3": # exploitr
                    run_train(type_of_attack="exploit", file_name="train_exploit.py")
                    print('press Enter if you want to monitor ')
                    d = option_choice('Train/option')
                    if d.lower() == "back" or d.lower() == "b" or d.lower() == "0":
                        clear_screen()
                        welcome_message(rad_use)
                    elif d.lower() == "exit":
                        others_choice(d, 'main')
                    else:

                        print("Launching monitoring terminal...")
                        launch_moitor_terminal(
                            type_of_attack="exploit", file_name="analysis_tool.py"
                        )
                
                elif result_train == "exit":
                    others_choice(result_train, whereme)
            elif choice == "2":
                from core.test_current_model import show_models_menu

                result_show_models = show_models_menu(rad_use)
                if result_show_models == "back":
                    clear_screen()
                    welcome_message(rad_use)
                elif result_show_models == "exit":
                    others_choice(result_show_models, whereme)
            elif choice == "3":

                result_show_attack = show_attack_menu(rad_use)
                if result_show_attack == "exit":
                    others_choice(result_show_attack, whereme)
                elif result_show_attack == "back":
                    clear_screen()
                    welcome_message(rad_use)
                elif result_show_attack == "1":
                    launch_Attack_terminal(
                        type_of_attack="scan", file_name="universal_scan.py"
                    )
                elif result_show_attack == "2":

                    launch_Attack_terminal(
                        type_of_attack="exploit", file_name="universal_exploit.py"
                    )
                elif result_show_attack == "3":
                    launch_Attack_terminal(
                        type_of_attack="recon", file_name="universal_recon.py"
                    )
                welcome_message(rad_use)
            elif choice == "4":  # MUSTEDITING

                result_monitoring_menu = monitoring_menu(rad_use)
                if result_monitoring_menu == "exit":
                    others_choice("exit", "main")
                elif result_monitoring_menu == "back":
                    clear_screen()
                    welcome_message(rad_use)
                elif result_monitoring_menu == "1":

                    launch_moitor_terminal(
                        type_of_attack="scan", file_name="analysis_tool.py"
                    )
                    clear_screen()
                    welcome_message(rad_use)
                elif result_monitoring_menu == "2":

                    launch_moitor_terminal(
                        type_of_attack="recon", file_name="analysis_tool.py"
                    )
                    clear_screen()
                    welcome_message(rad_use)
                elif result_monitoring_menu == "3":

                    launch_moitor_terminal(
                        type_of_attack="exploit", file_name="analysis_tool.py"
                    )
                    clear_screen()
                    welcome_message(rad_use)
            elif choice == "5":
                setup_environment()
            elif (
                choice != "1"
                and choice != "2"
                and choice != "3"
                and choice != "4"
                and choice != "5"
            ):
                others_choice(choice, "main")
            else:
                print("Invalid choice.")
    except KeyboardInterrupt:
        others_choice("exit", "main")


if __name__ == "__main__":
    main()
    # asd
