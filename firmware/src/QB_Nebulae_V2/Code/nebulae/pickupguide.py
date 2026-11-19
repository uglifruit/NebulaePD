# uf2_3: the knob pickup guide on the button LEDs. Python 2 and 3 compatible, no hardware (tests run on the PC).
#
# After a layer change (Source held or let go) a knob keeps its value until it is turned to it or through it
# (uf2_2, control.py). While a held knob is turned, one button LED blinks fast to say where the held value is,
# the buttons read left to right like a meter (the owner's design, 2026-11-19):
#   Record = much lower than the knob, File = lower, Reset = higher, Freeze = much higher;
#   "much" = more than SPLIT (15 % of the knob's turn) away. Source is left alone.
# When the knob picks up, all four flash once (FLASH seconds), then the normal LEDs come back. The guide also
# goes away HOLD seconds after the knob stops moving.

SPLIT = 0.15
HOLD = 1.0
FLASH = 0.2
BLINK_MS = 60          # on 60 ms, off 60 ms: about 8 Hz
BUTTONS = ("record", "next", "reset", "freeze")


def choose(states, now, hold=HOLD, flash=FLASH):
    """states: (moved_at, gap, picked_at) per knob (None entries are skipped), times in seconds; gap = held value
    minus the knob, or None when the knob isn't held. Of the knobs moved within `hold`, the most recent one
    decides: ("gap", gap) while it is held, ("flash",) just after it picked up, else None."""
    best = None
    for st in states:
        if st is None:
            continue
        moved_at = st[0]
        if moved_at <= 0 or now - moved_at > hold:
            continue
        if best is None or moved_at > best[0]:
            best = st
    if best is None:
        return None
    moved_at, gap, picked_at = best
    if gap is not None:
        return ("gap", gap)
    if picked_at > 0 and now - picked_at <= flash:
        return ("flash",)
    return None


def leds(guide, now_ms, split=SPLIT):
    """Brightness for each of BUTTONS (a dict), or None when there is nothing to show."""
    if guide is None:
        return None
    if guide[0] == "flash":
        return dict((b, 1.0) for b in BUTTONS)
    gap = guide[1]
    if gap < -split:
        lit = "record"
    elif gap < 0:
        lit = "next"
    elif gap <= split:
        lit = "reset"
    else:
        lit = "freeze"
    on = (int(now_ms) // BLINK_MS) % 2 == 0
    out = dict((b, 0.0) for b in BUTTONS)
    out[lit] = 1.0 if on else 0.0
    return out
