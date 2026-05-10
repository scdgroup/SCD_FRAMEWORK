from train_main import rl_new_train, _kill_by_pattern
import sys

# الاكمال التلقائي قريييييييبا
# from ..core.my_enums import setup_readline
# setup_readline()

if __name__ == "__main__":
    try:
        
        auto_start = "--auto" in sys.argv
        rl_new_train(auto_start=auto_start)
        # rl_new_train(auto_start=auto_start)
        # train()

    except KeyboardInterrupt:
        _kill_by_pattern("train_recon.py")
        _kill_by_pattern("train_exploit.py")
        _kill_by_pattern("train_scan.py")
