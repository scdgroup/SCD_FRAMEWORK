import readline, sys, os, subprocess, shutil,random


def _kill_by_pattern(pattern):
    try:
        subprocess.run(
            ["pkill", "-f", pattern],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

def stop_background_processes():
    _kill_by_pattern("train_exploit.py")
    _kill_by_pattern("train_recon.py")
    _kill_by_pattern("train_scan.py")
    _kill_by_pattern("suricata")

def update_this_tool():
    print("Updating the SCD Framework...")


def setup_environment():
    """ستقوم هنا بكتابة دوال اعداد البئة"""
    if is_scd_tool_installed():
        update_this_tool()
        # return
    else:
        subprocess.run(["bash", "setup.sh"])
        print(
            f"SCD framework setup completed. Please restart your terminal or run 'source ~/{os.path.basename(os.environ.get("SHELL", ""))}rc' to apply changes."
        )
        input("Press Enter to continue...")


def run_tree_and_cleanup_pycache():
    """Execute tree and remove all __pycache__ directories."""

    tree_output = ""
    try:
        tree_result = subprocess.run(
            ["tree"], capture_output=True, text=True, check=False
        )
        tree_output = tree_result.stdout or tree_result.stderr
    except FileNotFoundError:
        tree_output = "tree command not found. Skipping tree output."

    removed_dirs = []
    for root, dirs, files in os.walk(".", topdown=False):
        if "__pycache__" in dirs:
            pycache_dir = os.path.join(root, "__pycache__")
            shutil.rmtree(pycache_dir, ignore_errors=True)
            removed_dirs.append(pycache_dir)

    cleanup_output = (
        "Removed __pycache__ directories:\n" + "\n".join(removed_dirs)
        if removed_dirs
        else "No __pycache__ directories found."
    )

    return f"{tree_output}\n{cleanup_output}".strip()


def clear_screen():
    if sys.platform.startswith("win"):
        os.system("cls")
    else:
        os.system("clear")


def get_interfaces():
    try:
        import subprocess

        result = subprocess.run(["ip", "link"], capture_output=True, text=True)
        lines = result.stdout.split("\n")
        interfaces = []
        for line in lines:
            if ": " in line:
                iface = line.split(": ")[1].split(":")[0]
                interfaces.append(iface)
        return interfaces
    except:
        return ["wlan0", "eth0", "lo", "vmnet0", "vmnet1", "vmnet2", "vmnet8"]


def show_monitoring_menu(rad_use):
    tools_zlg("Monitoring", rad_use)
    print("\nMonitoring Menu:")
    print("0. back")
    print("1. scan Monitoring")
    print("2. recon Monitoring")
    print("3. exploite Monitoring")
    print("4. Exit")


completions = {
    "clear": ["clear"],
    "ifconfig": ["ifconfig "] + [f"ifconfig {iface}" for iface in get_interfaces()],
    "nmap": [
        "nmap ",
        "nmap -sV",
        "nmap -A",
        "nmap -p ",
        "nmap -sP",
        "nmap -O",
        "nmap -v",
        "nmap -p- localhost",
    ],
    "python": ["python -V", "python --version"],
    "ping": ["ping ", "ping 8.8.8.8", "ping google.com", "ping -c 4", "ping -t 5"],
    "back": ["back"],
    "pwd": ["pwd"],
    "ls": ["ls"],
    "dir": ["dir"],
    "0": ["back"],
    "exit": ["exit"],
    "localhost": ["localhost"],
    "127.0.0.1": ["127.0.0.1"],
    "1": ["1"],
    "2": ["2"],
    "3": ["3"],
    "4": ["4"],
    "5": ["5"],
}

"""
completions = {
    "clear": ["clear"],
    "ifconfig": ["ifconfig "] + [f"ifconfig {iface}" for iface in get_interfaces()],
    "nmap": [
        "nmap ",
        "nmap -sV",
        "nmap -A",
        "nmap -p ",
        "nmap -sP",
        "nmap -O",
        "nmap -v",
        "nmap -p- localhost",
    ],
    "set": ["set "]+
    [f"set {m}" for m in [
    "target_ip = ",
    "model_description = ",
    "log_file_path = ",
    "model_name = ",
    "nc_port = ",
    ]],
    "target_ip": ["target_ip = "],
    "description": ["model_description = "],
    "log_file_path": ["log_file_path = "],
    "name": ["model_name = "],
    "nc_port": ["nc_port = "],
    "check": ["check"],
    "show": ["show "],
    "run": ["run"],
    "options": ["options"],
    "ping": ["ping ", "ping 8.8.8.8", "ping google.com", "ping -c 4", "ping -t 5"],
    "back": ["back"],
    "pwd": ["pwd"],
    "ls": ["ls"],
    "dir": ["dir"],
    "0": ["back"],
    "help": ["help "],
    "exit": ["exit"],
    "localhost": ["localhost"],
    "127.0.0.1": ["127.0.0.1"],
    # '0': ['0'],
    "1": ["1"],
    "2": ["2"],
    "3": ["3"],
    "4": ["4"],
    "5": ["5"],
}
"""


def run_pipeline_try_option(extra_args=None):
    """
    واجهة تفاعلية لإعداد متغيرات التدريب ثم تشغيل السيناريو.
    """

    # تعريف المتغيرات
    variables = {
        "model_name": {
            "value": None,
            "required": True,
            "default": None,
            "description": "اسم النموذج",
        },
        "model_description": {
            "value": None,
            "required": True,
            "default": None,
            "description": "وصف النموذج",
        },
        "target_ip": {
            "value": None,
            "required": True,
            "default": None,
            "description": "عنوان IP للضحية",
        },
        "log_file_path": {
            "value": "/tmp/attacker_api_output.log",
            "required": False,
            "default": "/tmp/attacker_api_output.log",
            "description": "مسار ملف السجل",
        },
        "nc_port": {
            "value": 2080,
            "required": False,
            "default": 2080,
            "description": "منفذ nc / cloudflared",
        },
    }

    # دالة مساعدة لعرض الجدول
    def show_variables():
        print("\n" + "=" * 60)
        print(f"{'Variable':<20} {'Value':<25} {'Required':<10}")
        print("=" * 60)
        for name, info in variables.items():
            val = info["value"] if info["value"] is not None else "(not set)"
            req = "Yes" if info["required"] else "No"
            print(f"{name:<20} {str(val):<25} {req:<10}")
        print("=" * 60 + "\n")

    def check_required():
        missing = [
            name
            for name, info in variables.items()
            if info["required"] and info["value"] is None
        ]
        if missing:
            print("\n[Missing required variables]:")
            for m in missing:
                print(f"  - {m}: {variables[m]['description']}")
            return False
        else:
            print("\n[OK] All required variables are set.")
            return True

    # الحلقة التفاعلية
    whereme = "train_new_model"
    from core.my_enums import others_choice, clear_screen

    while True:
        # show_variables()
        # cmd = option_choice(whereme)
        cmd = input(f"SCD/{whereme}> ")
        if not cmd:
            continue
        # أمر set
        if cmd.lower().startswith("set "):
            # صيغة: set variable = value
            rest = cmd[4:].strip()
            if "=" not in rest:
                print("Invalid syntax. Use: set variable = value")
                continue
            var_name, value = rest.split("=", 1)
            var_name = var_name.strip()
            value = value.strip()
            if var_name not in variables:
                print(
                    f"Unknown variable: {var_name}. Available: {', '.join(variables.keys())}"
                )
                continue
            # محاولة تحويل القيمة إلى int إذا كان المتغير nc_port
            if var_name == "nc_port":
                try:
                    value = int(value)
                except ValueError:
                    print("Port must be a number. Using default.")
                    value = variables["nc_port"]["default"]
            variables[var_name]["value"] = value
            print(f"{var_name} ==> {value}")
        # أمر check
        elif cmd.lower() == "check":
            check_required()

        # أمر show
        elif cmd.lower() in ("show", "list", "options"):
            show_variables()

        # أمر run
        elif cmd.lower() == "run":
            if not check_required():
                print("Cannot run: missing required variables. Please set them first.")
                continue

            # جمع القيم
            model_name = variables["model_name"]["value"]
            model_description = variables["model_description"]["value"]
            target_ip = variables["target_ip"]["value"]
            log_file_path = variables["log_file_path"]["value"]
            nc_port = variables["nc_port"]["value"]

            # إنشاء ملف الوصف
            txt_file_path = os.path.join(
                os.path.dirname(__file__), "..", "models", f"{model_name}.txt"
            )
            txt_file_path = os.path.abspath(txt_file_path)
            os.makedirs(os.path.dirname(txt_file_path), exist_ok=True)
            with open(txt_file_path, "w", encoding="utf-8") as f:
                f.write(model_description + "\n")
            print(f"Description file created: {txt_file_path}")

            # تشغيل attacker_api مع الوسائط الإضافية
            api_extra_args = []
            if log_file_path:
                api_extra_args.extend(["--log-file", log_file_path])
            if nc_port:
                api_extra_args.extend(["--port", str(nc_port)])

            try:
                cloudflared_url, cloudflared_proc = run_attacker_api_and_extract_url(  # type: ignore
                    extra_args=api_extra_args,
                    log_file_path=log_file_path,  # نحتاج تعديل الدالة لتقبل هذا البارامتر
                )
                print(f"Cloudflared URL: {cloudflared_url}")
            except Exception as e:
                print(f"Failed to start attacker_api: {e}")
                continue

            # تشغيل nc listener
            try:
                run_nc_listener(port=nc_port)  # type: ignore
                print(f"nc listener started on port {nc_port}")
            except Exception as e:
                print(f"Failed to start nc listener: {e}")
                # نكمل رغم ذلك؟

            # نسخ النوت بوك
            new_file_path, _ = copy_notebook_with_name(base_name=model_name)  # type: ignore
            if not new_file_path:
                print("Failed to copy notebook. Aborting.")
                continue

            # تحديث الرابط في النوت بوك
            try:
                update_notebook_link(  # type: ignore
                    new_file_path, cloudflared_url, model_name, target_ip
                )
                print("Notebook updated with LINK_SERVER_ID, MODEL_NAME, TARGET_IP")
            except Exception as e:
                print(f"Failed to update notebook: {e}")

            # رفع ملف الوصف
            success_txt, link_txt, error_txt = upload_to_drive(  # type: ignore
                txt_file_path, folder_id=TXT_FOLDER_ID  # type: ignore
            )
            if success_txt:
                print(f"Description file uploaded: {link_txt}")
            else:
                print(f"Failed to upload description: {error_txt}")

            # رفع النوت بوك
            success, link, error = upload_to_drive(  # type: ignore
                new_file_path, folder_id=FOLDER_UPLOAD_ID  # type: ignore
            )
            if success:
                open_in_colab(link)  # type: ignore
            else:
                print(f"Failed to upload notebook: {error}")

            # بعد التنفيذ، نخرج من الحلقة التفاعلية ونعود إلى القائمة الرئيسية
            print("\nPipeline finished. Returning to main menu.")
            return  # العودة إلى main.py

        # أمر back
        elif cmd.lower() == "back" or cmd == "0":
            # print("Returning to main menu.")
            return "back"

        # أمر exit
        elif cmd.lower() == "exit":
            # print("Exiting SCD Framework.")
            return "exit"
        elif cmd.lower() == "clear" or cmd.lower() == "c":
            # print("Exiting SCD Framework.")
            # return 'exit'
            clear_screen()
        elif cmd.lower() in ["nmap", "ifconfig", "ping", "dir", "ls", "pwd"]:
            others_choice(cmd.lower(), "train_new_model")

        else:
            print("Unknown command. Available: set, show, check, run, back, exit")


def completer(text, state):
    if not text:
        return None

    parts = text.split(" ", 1)
    cmd = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    if cmd in completions:
        options = completions[cmd]
        if text.endswith(" "):
            candidates = options
        elif rest:
            candidates = [o for o in options if o.startswith(text)]
        else:
            candidates = options
        return candidates[state] if state < len(candidates) else None

    cmd_matches = [c for c in completions.keys() if c.startswith(text)]
    return cmd_matches[state] if state < len(cmd_matches) else None


def tools_zlg(what, rad_use):
    clear_screen()
    if what != None:
        print(f"\033]0;{what}\a", end="")
    """طباعة رسالة ترحيب"""
    print("                               You are welcome to use")
    tux_colored = f"""==========================================================================
|             | |  / _|                                           | |    |
|  ___  ___ __| | | |_ _ __ __ _ _ __ ___   _____      _____  _ __| | __ |
| / __|/ __/ _` | |  _| '__/ _` | '_ ` _ \\ / _ \\ \\ /\\ / / _ \\| '__| |/ / |
| \\__ \\ (_| (_| | | | | | | (_| | | | | | |  __/\\ V  V / (_) | |  |   <  |
| |___/\\___\\__,_| |_| |_|  \\__,_|_| |_| |_|\\___| \\_/\\_/ \\___/|_|  |_|\\_\\ |
=========================================================================="""
    txt=f"""==============================================================================================
|   .--.--.      ,----..       ,---,                 ___                             ,--,    |
|  /  /    '.   /   /   \\    .'  .' `\\             ,--.'|_                         ,--.'|    |
| |  :  /`. /  |   :     : ,---.'     \\            |  | :,'     ,---.      ,---.   |  | :    |
| ;  |  |--`   .   |  ;. / |   |  .`\\  |           :  : ' :    '   ,'\\    '   ,'\\  :  : '    |
|    :  ;_     .   ; /--`  :   : |  '  |         .;__,'  /    /   /   |  /   /   | |  ' |    |
|  \\  \\    `.  ;   | ;     |   ' '  ;  :         |  |   |    .   ; ,. : .   ; ,. : '  | |    |
|   `----.   \\ |   : |     '   | ;  .  |         :__,'| :    '   | |: : '   | |: : |  | :    |
|   __ \\  \\  | .   | '___  |   | :  |  '           '  : |__  '   | .; : '   | .; : '  : |__  |
|  /  /`--'  / '   ; : .'| '   : | /  ;            |  | '.'| |   :    | |   :    | |  | '.'| |
| '--'.     /  '   | '/  : |   | '` ,/             ;  :    ;  \\   \\  /   \\   \\  /  ;  :    ; |
|   `--'---'   |   : /  /  ;   :  .'               |  ,   /    `----'     `----'   |  ,   /  |
|               \\______'   |___,.'                  ---`-'                          ---`-'   |
=============================================================================================="""
    
    
    if rad_use == 0:
        print(txt)
    else:
      print(tux_colored)


def is_scd_tool_installed():
    bin_path = "/bin/scdtool"
    hidden_config = "/root/.scdtool"
    if os.path.isfile(bin_path) and os.access(bin_path, os.X_OK):
        return True
    if os.path.exists(hidden_config):
        return True
    return False


def get_setup_menu_label():
    return "Update SCD Framework" if is_scd_tool_installed() else "Setup Environment"


def main_welcome_message(rad_use):
    tools_zlg("SCD Framework",rad_use)
    print("\nMain menu:")
    print("0. Exit")
    print("1. Train Model")
    print("2. Manage Models")
    print("3. use current model")
    print("4. monitoring")
    print(f"5. {get_setup_menu_label()}")


def train(rad_use):
    tools_zlg("Train",rad_use)
    print("\nTYPE Train:")
    print("0. back")
    print("1. scan")
    print("2. recon")
    print("3. exploite")
    # print("3. test")
    print("4. exit")
    while True:
        train_choice = option_choice("train")
        if train_choice == "0" or train_choice == "back" or train_choice == "b":
            return "back"
        elif train_choice == "1":
            return "1"

        elif train_choice == "2":
            return "2"
        elif train_choice == "3":
            return "3"
        elif train_choice == "4" or train_choice == "exit" or train_choice == "e":
            return "exit"
        elif train_choice == "help":
            help_train_rl()
        # elif train_choice not in ["0", "1", "2", "3", "4", "back", "exit", "help"]:
        #     return train_choice
        else:
            others_choice(train_choice, "train")

# def help_menu(m='main'):
def help_menu(n="main"):
    if n == "main":
        print("Help information for the SCD Framework.")
        print("Available commands:")
        print("  help - Show this help message")
        print("  clear - c - Clear the screen")
        print("  ping <ip> - Ping a host")
        print("  ifconfig - Display network interface information")
        print("  nmap <options> - Run nmap scan")
        print("  help - Show this help message")
        print("  python -V - python --version - Show Python version")
        print("  back - b - Go back to the previous menu")
        print("  exit - e - Exit the program")
    elif n == "recon":
        print("Help information for recon commands.")
        # Add recon-specific help here
    elif n == "scan":
        print("Help information for scan commands.")
        # Add scan-specific help here
    elif n == "exploite":
        print("Help information for exploite commands.")
        # Add exploite-specific help here


def menu_attack(rad_use):
    tools_zlg("Attack Menu", rad_use)
    print("\nChoice attack type:")
    print("0. Back step")
    print("1. Scan Attacks")
    print("2. Exploit Attacks")
    print("3. Recon Attacks")
    print("5. Exit")


def welcome_test(rad_use):
    clear_screen()
    tools_zlg("Models Management", rad_use)
    # print("               ")
    print("\nModels management:")
    print("0. Back step")
    print("1. Show all models")
    print("2. Download all models")
    print("3. update")
    print("4. Exit")


def welcome_train_rl():
    clear_screen()
    print("                               You are welcome to use")
    tux_colored = f"""==============================================================================================
|   .--.--.      ,----..       ,---,                 ___                             ,--,    |
|  /  /    '.   /   /   \\    .'  .' `\\             ,--.'|_                         ,--.'|    |
| |  :  /`. /  |   :     : ,---.'     \\            |  | :,'     ,---.      ,---.   |  | :    |
| ;  |  |--`   .   |  ;. / |   |  .`\\  |           :  : ' :    '   ,'\\    '   ,'\\  :  : '    |
|    :  ;_     .   ; /--`  :   : |  '  |         .;__,'  /    /   /   |  /   /   | |  ' |    |
|  \\  \\    `.  ;   | ;     |   ' '  ;  :         |  |   |    .   ; ,. : .   ; ,. : '  | |    |
|   `----.   \\ |   : |     '   | ;  .  |         :__,'| :    '   | |: : '   | |: : |  | :    |
|   __ \\  \\  | .   | '___  |   | :  |  '           '  : |__  '   | .; : '   | .; : '  : |__  |
|  /  /`--'  / '   ; : .'| '   : | /  ;            |  | '.'| |   :    | |   :    | |  | '.'| |
| '--'.     /  '   | '/  : |   | '` ,/             ;  :    ;  \\   \\  /   \\   \\  /  ;  :    ; |
|   `--'---'   |   : /  /  ;   :  .'               |  ,   /    `----'     `----'   |  ,   /  |
|               \\______'   |___,.'                  ---`-'                          ---`-'   |
=============================================================================================="""
    print(tux_colored)


def asd():
    while True:
        choice = input("SCD/option> ")
        if choice == "1":
            return "1"
        elif choice == "2":
            return "2"
        elif choice == "3":
            return "3"
        elif choice != "1" and choice != "2" and choice != "3":
            return choice
        else:
            print("Invalid choice. Please try again.")


def option_choice(whereme):
    if whereme == "main":
        choice = input(f"\nSCD> ")
        return choice
    elif whereme == "maino":
        print(
            "How to use: \n"
            "0- Back\n"
            "1- Start Training JON\n"
            "2- Start Training BF\n"
            "3- Exit\n"
        )
        ch = asd()
        return ch
    else:
        choice = input(f"\nSCD/{whereme}> ")
        return choice


def others_choice(choice, n,rad_use=None):
    if choice == "0" or choice == "exit" or choice == "e":
        try:
            result = run_tree_and_cleanup_pycache()
            # print(result)
        except Exception as e:
            print(f"Error cleaning __pycache__: {e}")
        try:
            stop_background_processes()
            print(f"[َّ~] Background processes stopped.")
        except Exception as e:
            print(f"Error stopping background processes: {e}")
        print("\nThank you for using SCD Framework. Goodbye!")
        sys.exit(0)
    # elif choice == "back" or choice == "0" or choice == "b":
    #     # if n == "train":
    #         # clear_screen()
    #         # main_welcome_message(rad_use)
    elif choice == "clean":
        try:
            result = run_tree_and_cleanup_pycache()
            # print(result)
        except Exception as e:
            print(f"Error cleaning __pycache__: {e}")
    # elif choice == "00" and n == "main":
    #     print(
    #         "\nThank you for using SCD Framework. Goodbye!\nWe Are not close other processes."
    #     )
    #     stop_background_processes_option()
    #     sys.exit(0)
    elif "ping" in choice:
        subprocess.run(["ping", "-c", "3", choice.split()[-1]])
    elif choice == "dir" or choice == "ls":
        subprocess.run(["ls", "-l"])
    elif choice == "pwd":
        subprocess.run(["pwd"])
    elif choice == "python -V" in choice or choice == "python --version":
        subprocess.run(["python", "--version"])
    elif "clear" == choice or choice == "c" or choice == "clear ":
        if n == "main":
            clear_screen()
            main_welcome_message(rad_use)
        elif n == "monitoring":
            clear_screen()
            show_monitoring_menu(rad_use)
        elif n == "test":
            clear_screen()
            welcome_test(rad_use)
    elif "ifconfig" in choice:
        args = choice.split()[1:]
        if args:
            subprocess.run(["ifconfig"] + args)
        else:
            subprocess.run(["ifconfig"])

    elif "nmap" in choice:
        try:
            subprocess.run(["nmap"] + choice.split()[1:])
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while running nmap: {e}")
    elif "help" == choice and n == "main":
        help_menu(n)
    # elif choice =='help' and n == 'recon':
    #     # print("Help for recon")
    #     pass
    # elif choice == 'help' and n == 'scan':
    #     # print("Help for scan")
    #     pass
    # elif choice == 'help' and n == 'exploite':
    #     # print("Help for exploite")
    #     pass
    else:
        print(f"Unknown command: {choice}. Type 'help' for available commands.")


def help_train_rl():
    welcome_train_rl()
    print("This is the help menu for the training environment.")


def setup_readline():
    readline.set_completer(completer)
    # menu-complete يسمح بالتنقّل بين الاقتراحات باستخدام tab
    readline.parse_and_bind("tab: menu-complete")
    readline.parse_and_bind("set show-all-if-unmodified on")
    readline.parse_and_bind("set completion-query-items 5")
    readline.parse_and_bind("set print-completions-horizontally off")
