# First boot after a firmware update (uf1): carry calibration and settings over from the replaced tree.
# Python 2 and 3 compatible. Never raises: any problem leaves the stock behaviour (the forced calibration stands).
#
# update.sh moves the old tree to /home/alarm/backup/old, installs the new one and forces a CV calibration, which
# is wrong if cables were patched. On the first start of the new tree (no MARKER yet) this restores:
#   misc/calibration_data.txt   if the old one is valid
#   config/bootinstr.txt, config/nebsettings.txt, config/neb_options.txt   if the new tree has none
# MARKER is written in every case, so this runs once per installed tree.
# No timestamps are used: the module has no RTC and its clock restarts at about the same moment every boot, so file
# times can't tell this boot from the last. A Pitch-held recalibration on that one first boot is therefore
# overridden by the restore; recalibrate on any later boot.
import os
import shutil

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


def migrate(code=CODE, old=OLD):
    """Returns a list of log lines."""
    log = []
    try:
        if os.path.exists(code + MARKER):
            return log
        if not os.path.isdir(old):
            log.append("no previous tree - nothing to carry over")
        else:
            if valid_calibration(old + CAL):
                shutil.copyfile(old + CAL, code + CAL)
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
