# Optional user settings for the custom firmware (uf1), read from neb_options.txt.
# Python 2 and 3 compatible. Any problem (no file, bad line, bad value) falls back to the default.
#
# neb_options.txt goes in the USB stick's root; fileloader.py copies it to OPTIONS_PATH at each instrument load.
# Format: one `key=value` per line, `#` starts a comment. Known keys:
#   pitch_coeff = 0.95     Pitch CV one-pole coefficient per filter step (stock firmware: 0.33). The filter steps
#                          twice per poll pass (ui.py re-sets Pitch each pass). 1.0 = no smoothing.
#   sel_page_steps = 4     Pitch encoder steps per page in the instrument selector (1-16). The encoder gives 4 steps per
#                          cycle, usually one detent; Speed needs 8 to change bank.
#   pd_alts_at_load = 0    1 = send every *_alt value once when a Pd patch connects (stock: only while Source is
#                          held). Each Pd load resets them to the defaults first (nebulae.py), so this only tells a
#                          patch the defaults it already starts with: off by default.
import os

OPTIONS_PATH = "/home/alarm/QB_Nebulae_V2/Code/config/neb_options.txt"
USB_NAME = "neb_options.txt"

# key: (default, minimum, maximum)
OPTIONS = {
    "pitch_coeff": (0.95, 0.05, 1.0),
    "sel_page_steps": (4.0, 1.0, 16.0),
    "pd_alts_at_load": (0.0, 0.0, 1.0),
}


def read(path=OPTIONS_PATH):
    values = {}
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                values[key.strip().lower()] = val.strip()
    except Exception:
        pass
    return values


def get(key, path=OPTIONS_PATH):
    default, lo, hi = OPTIONS[key]
    raw = read(path).get(key)
    if raw is None:
        return default
    try:
        val = float(raw)
    except ValueError:
        return default
    if val != val:  # NaN
        return default
    return max(lo, min(hi, val))


def copy_from_usb(usb_dir="/mnt/memory", path=OPTIONS_PATH):
    """Copy neb_options.txt from the stick (if present). Keeps the last copy when the stick has none."""
    src = os.path.join(usb_dir, USB_NAME)
    if not os.path.isfile(src):
        return False
    try:
        with open(src, "r") as f:
            data = f.read()
        with open(path, "w") as f:
            f.write(data)
        return True
    except Exception:
        return False
