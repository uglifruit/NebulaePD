# First boot after a firmware update (uf1): carry calibration and settings over from the replaced tree.
# Python 2 and 3 compatible. Never raises: any problem leaves the stock behaviour (the forced calibration stands).
#
# update.sh moves the old tree to /home/alarm/backup/old, installs the new one and forces a CV calibration, which
# is wrong if cables were patched. On the first start of the new tree (no MARKER yet) this restores:
#   misc/calibration_data.txt   if the old one is valid
#   config/bootinstr.txt, config/nebsettings.txt, config/neb_options.txt   if the new tree has none
# Nothing is restored if the calibration was written during this boot (Pitch held at power-on = recalibrate +
# reset settings on purpose). MARKER is written in every case, so this runs once per installed tree.
import os
import shutil
import time

CODE = "/home/alarm/QB_Nebulae_V2/Code/"
OLD = "/home/alarm/backup/old/QB_Nebulae_V2/Code/"
MARKER = "config/uf_migrated"
CAL = "misc/calibration_data.txt"
CAL_NAMES = ["start", "size", "density", "overlap", "blend", "window", "speed", "pitch"]
CARRY = ["config/bootinstr.txt", "config/nebsettings.txt", "config/neb_options.txt"]


def valid_calibration(path):
    try:
        found = {}
        with open(path, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2 and parts[0] in CAL_NAMES:
                    val = float(parts[1])
                    if val != val or abs(val) > 2.0:
                        return False
                    found[parts[0]] = val
        return len(found) == len(CAL_NAMES)
    except Exception:
        return False


def boot_time(now=None):
    try:
        with open("/proc/uptime", "r") as f:
            up = float(f.read().split()[0])
    except Exception:
        return None
    return (time.time() if now is None else now) - up


def migrate(code=CODE, old=OLD, booted_at="auto"):
    """Returns a list of log lines. booted_at: wall-clock boot time (None = unknown, "auto" = from /proc/uptime)."""
    log = []
    try:
        if os.path.exists(code + MARKER):
            return log
        if booted_at == "auto":
            booted_at = boot_time()
        if not os.path.isdir(old):
            log.append("no previous tree - nothing to carry over")
        else:
            new_cal = code + CAL
            fresh = (os.path.isfile(new_cal) and booted_at is not None
                     and os.path.getmtime(new_cal) >= booted_at - 1.0)
            if fresh or booted_at is None:
                log.append("calibration written this boot (or boot time unknown) - nothing restored")
            else:
                if valid_calibration(old + CAL):
                    shutil.copyfile(old + CAL, new_cal)
                    log.append("restored calibration from the previous tree")
                else:
                    log.append("previous calibration missing or invalid - kept the new one")
                for rel in CARRY:
                    if os.path.isfile(old + rel) and not os.path.isfile(code + rel):
                        shutil.copyfile(old + rel, code + rel)
                        log.append("restored " + rel)
        with open(code + MARKER, "w") as f:
            f.write("\n".join(log) + "\n")
    except Exception as e:
        log.append("migration error: " + str(e))
    return log
