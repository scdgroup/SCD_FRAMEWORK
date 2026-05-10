from train_main import rl_new_train, _kill_by_pattern
import sys

if __name__ == "__main__":
    try:
        auto_start = "--auto" in sys.argv
        rl_new_train(auto_start=auto_start)

    except KeyboardInterrupt:
        _kill_by_pattern("train_recon.py")
        _kill_by_pattern("train_exploit.py")
        _kill_by_pattern("train_scan.py")
        _kill_by_pattern("suricata")
