import os
import subprocess
import sys


def rl_new_train():
    # welcome_train_rl()
    # help_train_rl()
    # whereme = 'main'
    print("Enter target IP or default(192.168.12.229) press enter")
    # TARGET_IP = option_choice(whereme)
    TARGET_IP = input("SCD> ")

    if TARGET_IP == "exit":
        sys.exit(0)
    print("Enter NC port or default(2080) press enter")
    Port_NC = input("SCD> ")

    if Port_NC == "exit":
        sys.exit(0)

    print("Enter interface or default(wlan0) press enter")
    INTERFACE = input("SCD> ")
    if INTERFACE == "exit":
        sys.exit(0)
    # تحديد مسار ملف التكوين (نسبي للمشروع)
    config_path = os.path.join("rl_cyber_env", "config", "env_config.py")

    # قراءة الملف الحالي
    try:
        with open(config_path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}")
        return None

    # تعديل الأسطر حسب المدخلات
    modified = False
    for i, line in enumerate(lines):
        if TARGET_IP and line.strip().startswith("TARGET_IP"):
            lines[i] = f'    TARGET_IP = "{TARGET_IP}"\n'
            modified = True

        elif Port_NC and line.strip().startswith("STREAM_PORT"):
            lines[i] = f"    STREAM_PORT = {Port_NC}\n"
            modified = True

        elif INTERFACE and line.strip().startswith("INTERFACE"):
            lines[i] = f'    INTERFACE = "{INTERFACE}"\n'
            modified = True

    # كتابة التغييرات إذا وجدت
    if modified:
        with open(config_path, "w") as f:
            f.writelines(lines)
        print("Configuration updated successfully.")
    print(f"IP: {TARGET_IP}") if TARGET_IP else print(f"Using default IP ")
    print(f"Port nc: {Port_NC}") if Port_NC else print(f"Using default port ")
    (
        print(f"Interface: {INTERFACE}")
        if INTERFACE
        else print(f"Using default interface ")
    )
    # return 'run'
    # launch_training_terminal()


def launch_training_terminal(type_of_attack="exploit", file_name="train_exploit.py"):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # print(current_dir)
    while current_dir and not os.path.exists(os.path.join(current_dir, type_of_attack)):
        current_dir = os.path.dirname(current_dir)

    if not current_dir:
        print("Could not locate project root (Train_cl).")
        return

    trainer_script = current_dir + f"/{type_of_attack}/{file_name}"

    if not os.path.isfile(trainer_script):
        print(f"Error: trainer.py not found at {trainer_script}")
        return

    # أمر بايثون لتشغيل السكريبت
    python_cmd = [sys.executable, trainer_script]

    # لينكس: جرب عدة محاكيات طرفية شائعة
    cols = 100
    rows = 30
    # لظهور النافذة في أعلى منتصف الشاشة (تقريباً)
    # يمكنك حساب المنتصف لاحقاً، أو ببساطة استخدم +0+0 للزاوية العليا اليسرى
    geometry = f"{cols}x{rows}+0+0"  # أعلى اليسار
    # أو geometry = f'{cols}x{rows}+200+0'   # إزاحة أفقية حسب الرغبة

    terminals = [
        [
            "gnome-terminal",
            "--geometry",
            geometry,
            "--",
            "bash",
            "-c",
            f'{" ".join(python_cmd)}; exec bash',
        ],
        [
            "xterm",
            "-geometry",
            geometry,
            "-e",
            "bash",
            "-c",
            f'{" ".join(python_cmd)}; exec bash',
        ],
        [
            "konsole",
            "--geometry",
            geometry,
            "-e",
            "bash",
            "-c",
            f'{" ".join(python_cmd)}; exec bash',
        ],
        [
            "xfce4-terminal",
            "--geometry",
            geometry,
            "-e",
            "bash",
            "-c",
            f'{" ".join(python_cmd)}; exec bash',
        ],
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
        print(f"  python {trainer_script}")


def launch_moitor_terminal(type_of_attack="exploit", file_name="analysis_tool.py"):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir and not os.path.exists(os.path.join(current_dir, type_of_attack)):
        current_dir = os.path.dirname(current_dir)

    if not current_dir:
        print("Could not locate project root (Train_cl).")
        return

    attack_dir = os.path.join(current_dir, type_of_attack)
    trainer_script = os.path.join(attack_dir, file_name)

    if not os.path.isfile(trainer_script):
        print(f"Error: file not found at {trainer_script}")
        return

    # أمر بايثون لتشغيل السكريبت من مجلد نوع الهجمة
    cmd = f"cd {attack_dir} && {sys.executable} {trainer_script}; exec bash"

    cols = 100
    rows = 30
    geometry = f"{cols}x{rows}+0+0"

    terminals = [
        ["gnome-terminal", "--geometry", geometry, "--", "bash", "-c", cmd],
        ["xterm", "-geometry", geometry, "-e", "bash", "-c", cmd],
        ["konsole", "--geometry", geometry, "-e", "bash", "-c", cmd],
        ["xfce4-terminal", "--geometry", geometry, "-e", "bash", "-c", cmd],
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
        print(f"  cd {attack_dir} && python {trainer_script}")


if __name__ == "__main__":
    # rl_new_train()
    launch_training_terminal()
