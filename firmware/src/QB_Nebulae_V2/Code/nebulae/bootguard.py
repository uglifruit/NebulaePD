# uf2: boot-loop guard for every engine (Csound, Pd, SuperCollider). Python 2 and 3 compatible. Never raises.
#
# PATH counts the app starts since an instrument last ran HEALTHY_S seconds. A crash makes systemd restart the app,
# which loads the same boot instrument again (the stock boot loop, e.g. GENDYN). After LIMIT starts in a row without
# a healthy run, the next start loads the factory default instead. A power cycle during a hang counts the same way.
PATH = "/home/alarm/QB_Nebulae_V2/Code/config/boot_guard.txt"
LIMIT = 2
HEALTHY_S = 20.0


def read(path=PATH):
    try:
        with open(path, "r") as f:
            return max(0, int(f.read().strip() or "0"))
    except Exception:
        return 0


def write(count, path=PATH):
    try:
        with open(path, "w") as f:
            f.write("%d\n" % count)
        return True
    except Exception:
        return False


def on_app_start(path=PATH):
    """Count this start. True if the factory default should be loaded instead of the boot instrument."""
    count = read(path)
    fallback = count >= LIMIT
    write(1 if fallback else count + 1, path)
    return fallback


def mark_healthy(path=PATH):
    return write(0, path)
