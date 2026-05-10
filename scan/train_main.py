import os
import subprocess
import sys
import time


def _kill_by_pattern(pattern):
    try:
        subprocess.run(
            ["pkill", "-f", pattern],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def get_network_from_interface(interface):
    """
    تستخرج عنوان الشبكة (CIDR) من جدول التوجيه لواجهة معينة.
    مثال: المدخل 'wlan0' -> المخرج '192.168.100.0/24'
    """
    try:
        # تشغيل الأمر ip route show dev <interface>
        result = subprocess.run(
            ["ip", "route", "show", "dev", interface],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout.strip()
        if not output:
            return None

        # قد يحتوي الإخراج على أكثر من سطر، ويمثل السطر الأول أحياناً التوجيه الافتراضي.
        # نبحث عن أول عنوان شبكة بصيغة CIDR.
        for line in output.splitlines():
            parts = line.split()
            if parts:
                network = parts[0]
                if "/" in network:
                    return network
        return None
    except FileNotFoundError:
        print("الأمر 'ip' غير موجود. هل أنت على نظام Linux؟")
        return None


def run_subprocess(INTERFACE=None):
    from config.env_config import Config

    config = Config()
    interface = INTERFACE if INTERFACE else getattr(config, "INTERFACE", None)
    network = get_network_from_interface(interface)

    if not interface:
        print(
            "ERROR: No interface specified. Set INTERFACE in config or pass INTERFACE to run_subprocess."
        )
        return None

    if not network:
        print(f"ERROR: unable to determine network for interface {interface}.")
        return None

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


def welcome_train_rl():
    print("\033]0;Training Scan\a", end="")
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


def ip_to_home_net(ip_str):
    parts = ip_str.strip().split(".")
    if len(parts) != 4:
        raise ValueError("Invalid IP address")
    network_part = ".".join(parts[:3])  # 192.168.2
    return f"{network_part}.0/24"


def rl_new_train(auto_start=False):
    if not auto_start:
        welcome_train_rl()
    from config.env_config import Config

    def get_config_value(attr_name, default=""):
        return getattr(Config, attr_name, default)

    TARGET_IP = ""
    INTERFACE = ""
    STREAM_PORT = ""
    DEFAULT_EPISODES = ""
    SAVE_INTERVAL = ""

    if not auto_start:
        print(
            f"Enter target IP or default({get_config_value('TARGET_IP')}) press enter"
        )
        try:
            TARGET_IP = input("SCD/Training/Scan> ")
        except (EOFError, KeyboardInterrupt):
            _kill_by_pattern("train_scan.py")
            _kill_by_pattern("suricata")

            TARGET_IP = ""

        if TARGET_IP == "exit":
            _kill_by_pattern("train_scan.py")
            return
        print(
            f"Enter interface or default({get_config_value('INTERFACE')}) press enter"
        )
        try:
            INTERFACE = input("SCD/Training/Scan> ")
        except (EOFError, KeyboardInterrupt):
            _kill_by_pattern("train_scan.py")
            _kill_by_pattern("suricata")
            INTERFACE = ""
        if INTERFACE == "exit":
            _kill_by_pattern("train_scan.py")
            return

        print(
            f"Enter STREAM PORT or default({get_config_value('STREAM_PORT')}) press enter"
        )

        try:
            STREAM_PORT = input("SCD/Training/Scan> ")
        except (EOFError, KeyboardInterrupt):
            _kill_by_pattern("train_scan.py")
            _kill_by_pattern("suricata")
            STREAM_PORT = ""

        if STREAM_PORT == "exit":
            _kill_by_pattern("train_scan.py")
            return

        print(
            f"Enter DEFAULT EPISODES for log receiver or default({get_config_value('DEFAULT_EPISODES')}) press enter"
        )
        try:
            DEFAULT_EPISODES = input("SCD/Training/Scan> ")
        except (EOFError, KeyboardInterrupt):
            _kill_by_pattern("train_scan.py")
            _kill_by_pattern("suricata")
            DEFAULT_EPISODES = ""
        if DEFAULT_EPISODES == "exit":
            _kill_by_pattern("train_scan.py")
            return
        print(
            f'Enter save interval or default({get_config_value("SAVE_INTERVAL")}) press enter'
        )
        try:
            SAVE_INTERVAL = input("SCD/Training/Scan> ")
        except (EOFError, KeyboardInterrupt):
            _kill_by_pattern("train_scan.py")
            _kill_by_pattern("suricata")
            SAVE_INTERVAL = ""
        if SAVE_INTERVAL == "exit":
            _kill_by_pattern("train_scan.py")

    # تحديد مسار ملف التكوين (نسبي للمشروع)
    config_path = os.path.join("scan", "config", "env_config.py")
    # config_path = os.path.join("config", "env_config.py")

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

        elif INTERFACE and line.strip().startswith("INTERFACE"):
            lines[i] = f'    INTERFACE = "{INTERFACE}"\n'
            modified = True
        elif STREAM_PORT and line.strip().startswith("STREAM_PORT"):
            lines[i] = f"    STREAM_PORT = {STREAM_PORT}\n"
            modified = True
        elif DEFAULT_EPISODES and line.strip().startswith("DEFAULT_EPISODES"):
            lines[i] = f"    DEFAULT_EPISODES = {DEFAULT_EPISODES}\n"
            modified = True
        elif SAVE_INTERVAL and line.strip().startswith("SAVE_INTERVAL"):
            lines[i] = f"    SAVE_INTERVAL = {SAVE_INTERVAL}\n"
            modified = True
    # كتابة التغييرات إذا وجدت
    if modified:
        with open(config_path, "w") as f:
            f.writelines(lines)
        if not auto_start:
            print("Configuration updated successfully.")

    if not auto_start:
        print(f"IP: {TARGET_IP}") if TARGET_IP else print(f"Using default IP ")
        (
            print(f"Port: {STREAM_PORT}")
            if STREAM_PORT
            else print(f"Using default port ")
        )
        (
            print(f"Interface: {INTERFACE}")
            if INTERFACE
            else print(f"Using default interface ")
        )
        (
            print(f"Save Interval: {SAVE_INTERVAL}")
            if SAVE_INTERVAL
            else print(f"Using default save interval ")
        )
        (
            print(f"Default Episodes: {DEFAULT_EPISODES}")
            if DEFAULT_EPISODES
            else print(f"Using default episodes ")
        )
        print("Starting training with above configuration...")

    # return 'run'
    # launch_training_terminal()
    from trainer import train

    try:
        run_subprocess(INTERFACE=INTERFACE)
        train()
    except KeyboardInterrupt:
        _kill_by_pattern("train_recon.py")
        _kill_by_pattern("train_exploit.py")
        _kill_by_pattern("train_scan.py")


def launch_training_terminal():

    current_dir = os.path.dirname(os.path.abspath(__file__))
    # print(current_dir)
    while current_dir and not os.path.exists(os.path.join(current_dir, "recon")):
        current_dir = os.path.dirname(current_dir)

    if not current_dir:
        print("Could not locate project root (Train_cl).")
        return

    trainer_script = current_dir + "/scan/train_scan.py"

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


if __name__ == "__main__":
    # rl_new_train()
    launch_training_terminal()
