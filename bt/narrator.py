#!/usr/bin/env python
# narrator.py: the Nebulae storyteller's mind (docs/BLUETOOTH.md, stage 3). Python 2.7 (the module) and 3 (tests).
#
#   python2 narrator.py --events /dev/shm/neb_bt/events --state /dev/shm/neb_bt/state [--settings F] [--no-data]
#                       [--log F]
#   python3 narrator.py --replay events.txt          (the PC: prints the story a recorded event file would tell)
#
# bt_storyteller.instr (tools/storyteller.py) appends one line per happening to the events file:
#   k <t> <control> <value>                 a control changed (0..1; pitch 0.6 = unison, 0.2 per octave;
#                                           speed: rate = 8 * value - 4)
#   a <t> <in dB> <out dB> <centroid Hz> <low>   every 0.25 s: input/output level, brightness, share of lows
#   o <t> <strength dB>                    an onset in the input
# (t = Csound's clock, seconds since the instrument loaded.) This reads them, keeps a picture of what is
# happening (knob moves, CV-like motion, pulses, silence, brightness, sounds it has heard before) and, when the
# keyboard has time, writes one observation to stdout (piped into btkbd): a [data] line, then a line of poetry
# from phrases.py. Output is limited to characters that type the same on UK and US keyboards.
from __future__ import division, print_function

import collections
import math
import os
import random
import string
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phrases as P  # noqa: E402

SAFE = set(string.ascii_letters + string.digits + " .,!?()-:%'/=+<>*;[]\n")
KNOBS = ["density", "size", "start", "pitch", "speed", "blend", "window", "overlap"]
SETTLE = 0.7          # s without change: a hand move is over
CV_SETTLE = 3.0       # s without change: a CV-like motion is over
CPS = 26.0            # btkbd types about 28 characters a second
GAP = 3.5             # s between observations (1 s for urgent ones)
# settings.txt on the stick (bt_keyboard/), "name = value" lines; anything missing or unreadable keeps its default
DEFAULTS = {"data": "full",    # full: [time, what happened / the sound]; short: [time, what happened]; off: none
            "pace": GAP,       # seconds between observations: 1 = chatty .. 60 = taciturn (urgent ones: 1 s)
            "coda": 20.0}      # % of lines that get a closing musing (0 .. 100)
INTERVALS = {1: "a semitone", 2: "a whole tone", 3: "a minor third", 4: "a major third", 5: "a fourth",
             6: "a tritone", 7: "a fifth", 8: "a minor sixth", 9: "a major sixth", 10: "a minor seventh",
             11: "a major seventh", 12: "an octave", 19: "an octave and a fifth", 24: "two octaves"}


def read_settings(path, base=None):
    """settings.txt -> {"data", "pace", "coda"}, keeping defaults for anything missing or wrong."""
    out = dict(DEFAULTS if base is None else base)
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except (IOError, OSError, TypeError):
        return out
    for line in lines:
        line = line.split("#", 1)[0]
        if "=" not in line:
            continue
        k, v = [x.strip().lower() for x in line.split("=", 1)]
        try:
            if k == "data" and v in ("full", "short", "off"):
                out[k] = v
            elif k == "pace":
                out[k] = min(60.0, max(1.0, float(v)))
            elif k == "coda":
                out[k] = min(100.0, max(0.0, float(v)))
        except ValueError:
            pass
    return out


def clean(text):
    return "".join(c if c in SAFE else " " for c in text)


def cap(s):
    return s[:1].upper() + s[1:]


def dur(sec):
    sec = int(round(sec))
    if sec < 120:
        return "%d seconds" % sec
    m = int(round(sec / 60.0))
    return "1 minute" if m == 1 else "%d minutes" % m


def clock(t):
    t = max(0, int(t))
    return "%d:%02d" % (t // 60, t % 60) if t < 3600 else "%d:%02d:%02d" % (t // 3600, t // 60 % 60, t % 60)


class _Fields(dict):
    def __missing__(self, key):
        return ""


def fill(template, **f):
    d = _Fields()
    for k, v in f.items():
        d[k] = v
        d[cap(k)] = cap(str(v))
    return string.Formatter().vformat(template, (), d)


class Voice(object):
    """Picks lines from pools like a shuffled deck: no repeat until the pool is used up, never twice running."""

    def __init__(self, rng):
        self.rng = rng
        self.decks = {}
        self.last = {}

    def pick(self, key, pool):
        pool = [p for p in pool if p]
        if not pool:
            return ""
        deck = self.decks.get(key)
        if not deck:
            deck = list(range(len(pool)))
            self.rng.shuffle(deck)
            if len(deck) > 1 and deck[-1] == self.last.get(key):
                deck[0], deck[-1] = deck[-1], deck[0]
        i = deck.pop()
        self.decks[key] = deck
        self.last[key] = i
        return pool[i % len(pool)]


def fmt_val(name, v):
    if name == "pitch":
        return "%+.1f st" % ((v - 0.6) * 60.0)
    if name == "speed":
        return "x%.2f" % (8.0 * v - 4.0)
    return "%.2f" % v


class Control(object):
    def __init__(self, name):
        self.name = name
        self.v = None
        self.t = 0.0
        self.moving = False
        self.cv = None          # None, "lfo", "steps", "wander"
        self.cv_t = self.cv_check = self.cv_first = 0.0
        self.wander_said = False
        self.period = 0.0
        self.touched = False
        self.settled = []       # (t, value) where hand moves ended

    def begin(self, t):
        self.moving = True
        self.t0, self.v0 = t, self.v
        self.rev, self.dir, self.n, self.jumps = 0, 0, 0, 0
        self.lo = self.hi = self.v
        self.extrema = []

    def update(self, t, v):
        if self.v is None:
            self.v, self.t = v, t
            return
        if not self.moving:
            self.begin(t)
        dv = v - self.v
        d = (1 if dv > 0 else -1) if abs(dv) > 0.003 else 0
        if d and self.dir and d != self.dir:
            self.rev += 1
            self.extrema.append(t)
        if d:
            self.dir = d
        # a step: a jump after a plateau (a sequencer), not a fast but continuous change (an LFO)
        if abs(dv) > 0.02 and t - self.t >= 0.12:
            self.jumps += 1
        self.n += 1
        self.lo, self.hi = min(self.lo, v), max(self.hi, v)
        self.v, self.t = v, t


class Pulses(object):
    """A train of pulses (Reset gate, or onsets in the input): regular, loose or irregular, and its tempo."""

    def __init__(self, what):
        self.what = what
        self.times = collections.deque(maxlen=12)
        self.kind = None
        self.bpm = 0.0
        self.mean = 0.0
        self.changed_t = -1e9

    def add(self, t):
        if self.times and t - self.times[-1] < 0.05:
            return
        self.times.append(t)

    def analyse(self, now):
        ts = [t for t in self.times if now - t < 12.0]
        if len(ts) < 8:
            return None
        iv = [b - a for a, b in zip(ts, ts[1:])][-8:]
        if max(iv) > 3.0:
            return None
        mean = sum(iv) / len(iv)
        sd = math.sqrt(sum((x - mean) ** 2 for x in iv) / len(iv))
        cv = sd / mean if mean > 0 else 1.0
        kind = "regular" if cv < 0.06 else ("loose" if cv < 0.2 else "irregular")
        return kind, 60.0 / mean, mean, cv


class Narrator(object):
    def __init__(self, rng=None, show_data=True, settings=None):
        self.rng = rng or random.Random()
        self.voice = Voice(self.rng)
        self.settings = dict(settings or DEFAULTS)
        if not show_data:
            self.settings["data"] = "off"
        self.ctl = dict((n, Control(n)) for n in KNOBS)
        self.latch = {}
        self.now = 0.0
        self.frames = collections.deque(maxlen=480)     # 2 minutes of analysis frames
        self.cands = []
        self.busy_until = 0.0
        self.last_said = -1e9
        self.cooldown = {}
        self.spoken = {}
        self.connected = False
        self.ever_connected = False
        self.connect_t = 0.0
        self.milestones = [5, 15, 30, 45, 60, 90, 120, 180, 240]
        self.last_touch = 0.0
        self.recent_moves = []                          # (t, name) of ended hand moves
        self.resets = []
        self.reset_pulses = Pulses("the Reset gate")
        self.onset_pulses = Pulses("the sound you give me")
        self.last_onset = -1e9
        self.quiet_since = None
        self.silence_n, self.silence_next = 0, 20.0
        self.freeze_t = None
        self.freeze_said = 0
        self.frozen_alone_said = False
        self.prints = []                                # recognition: (t, fingerprint, raw)
        self.last_print_t = -1e9
        self.trend_t = -1e9
        self.activity = collections.deque(maxlen=200)

    # ------------------------------------------------------------------ input
    def feed(self, line):
        parts = line.split()
        if not parts:
            return
        try:
            kind, t = parts[0], float(parts[1])
        except (IndexError, ValueError):
            return
        self.now = max(self.now, t)
        if kind == "k" and len(parts) >= 4:
            self.on_control(t, parts[2], float(parts[3]))
        elif kind == "a" and len(parts) >= 6:
            self.frames.append((t, float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])))
        elif kind == "o" and len(parts) >= 3:
            self.on_onset(t, float(parts[2]))

    def set_connected(self, on):
        if on and not self.connected:
            self.connect_t = self.now
            pool = P.GREET_AGAIN if self.ever_connected else P.GREET
            self.say(10, "greet", "connected", lambda: self.voice.pick("greet%d" % self.ever_connected, pool))
            self.ever_connected = True
        self.connected = on

    def on_control(self, t, name, v):
        self.activity.append(t)
        if name in self.ctl:
            c = self.ctl[name]
            if c.v is not None and not c.cv:
                self.last_touch = t
            c.update(t, v)
            return
        old = self.latch.get(name)
        self.latch[name] = v
        if old is None:
            return
        self.last_touch = t
        if name.endswith("_alt"):
            base = name[:-4]
            data = "%s (hidden layer) %.2f > %.2f" % (base, old, v)
            self.say(3, "alt", data, lambda: fill(self.voice.pick("alt", P.ALT), name=self.name(base)), cool=40)
        elif name == "freeze":
            self.freeze_t = t if v >= 0.5 else None
            self.freeze_said = 0
            self.frozen_alone_said = False
            pool = P.FREEZE_ON if v >= 0.5 else P.FREEZE_OFF
            self.say(6, "freeze", "freeze %s" % ("on" if v >= 0.5 else "off"), lambda: self.voice.pick(
                "freeze%d" % (v >= 0.5), pool))
        elif name == "record":
            pool = P.RECORD_ON if v >= 0.5 else P.RECORD_OFF
            self.say(6, "record", "record %s" % ("on" if v >= 0.5 else "off"), lambda: self.voice.pick(
                "rec%d" % (v >= 0.5), pool))
        elif name == "source":
            pool = P.SOURCE_LIVE if v >= 0.5 else P.SOURCE_FILE
            self.say(5, "source", "source: %s" % ("live input" if v >= 0.5 else "files"), lambda: self.voice.pick(
                "src%d" % (v >= 0.5), pool))
        elif name == "file":
            self.say(4, "file", "file %d > %d" % (old, v), lambda: self.voice.pick("file", P.FILE_NEXT))
        elif name == "reset" and v >= 0.5 and old < 0.5:
            self.resets.append(t)
            self.reset_pulses.add(t)

    def on_onset(self, t, strength):
        self.activity.append(t)
        quiet_before = self.level_mean(t - 2.0, t - 0.1)
        silent = quiet_before is not None and quiet_before < -50
        if strength >= 12.0 and (t - self.last_onset > 3.0 or silent):
            calm = t - self.last_onset
            data = "onset +%.0f dB after %s" % (strength, "silence" if silent else (
                "%.1f s without onsets" % calm if calm < 1e6 else "nothing"))
            self.say(7, "transient", data, lambda: self.voice.pick("transient", P.TRANSIENT), cool=20)
        self.last_onset = t
        self.onset_pulses.add(t)

    # ---------------------------------------------------------------- helpers
    def name(self, control):
        return self.voice.pick("name_" + control, P.NAMES.get(control, [control]))

    def window(self, t0, t1):
        return [f for f in self.frames if t0 <= f[0] < t1]

    def level_mean(self, t0, t1):
        w = self.window(t0, t1)
        return sum(f[1] for f in w) / len(w) if w else None

    def snapshot(self):
        if not self.frames:
            return ""
        w = self.window(self.now - 1.0, self.now + 1.0) or [self.frames[-1]]
        lin, lout = sum(f[1] for f in w) / len(w), sum(f[2] for f in w) / len(w)
        cent, low = sum(f[3] for f in w) / len(w), sum(f[4] for f in w) / len(w)
        busy = sum(1 for a in self.activity if self.now - a < 30.0)
        mood = "busy" if busy > 30 else "calm"
        if lin < -55:
            return "in silent, out %.0f dB, %s" % (lout, mood)
        return "in %.0f dB, out %.0f dB, %d Hz, lows %d%%, %s" % (lin, lout, cent, low * 100, mood)

    def say(self, prio, key, data, text_fn, cool=0.0):
        # cool: seconds after this kind was last *spoken* before it may be said again
        if cool:
            self.cooldown[key] = cool
            if self.now - self.spoken.get(key, -1e9) < cool:
                return
        self.cands = [c for c in self.cands if c[1] != key]      # the newest of a kind replaces the older one
        # the data snapshot is taken now, when it was observed, not when it gets typed
        self.cands.append((prio, key, data, text_fn, self.now, self.snapshot()))

    # ------------------------------------------------------------------ think
    def tick(self, now=None):
        """Update the picture; return the next thing to type (or None)."""
        if now is not None:
            self.now = max(self.now, now)
        now = self.now
        self.think_controls(now)
        self.think_pulses(now)
        self.think_sound(now)
        self.think_time(now)
        return self.speak(now)

    def think_controls(self, now):
        for name in KNOBS:
            c = self.ctl[name]
            if not c.moving:
                continue
            quiet = now - c.t
            if c.cv:
                if quiet > CV_SETTLE:
                    c.moving = False
                    cv = c.cv
                    c.cv = None
                    self.say(4, "cvstop:" + name, "%s: %s stopped" % (name, cv), lambda n=name: fill(
                        self.voice.pick("cvstop", P.CV_STOP), name=self.name(n)))
                elif c.cv == "wander" and now - c.cv_check > 3.0:
                    # a wave needs a few turning points before it shows: look again; "wandering" is only said
                    # once it has stayed that way for 6 s
                    c.cv_check = now
                    if self.classify_cv(c, now, quiet=True) != "wander":
                        self.report_cv(c)
                    elif not c.wander_said and now - c.cv_first > 6.0:
                        c.wander_said = True
                        self.report_cv(c)
                elif now - c.cv_t > 90.0:
                    c.cv_t = now
                    self.report_cv(c, again=True)
                continue
            if quiet > SETTLE:
                c.moving = False
                self.report_move(c)
            elif now - c.t0 > 6.0 and ((c.n > 30 and c.rev >= 3) or c.jumps >= 6):
                self.classify_cv(c, now)

    def classify_cv(self, c, now, quiet=False):
        ext = c.extrema[-8:]
        halves = [b - a for a, b in zip(ext, ext[1:])]
        kind, period = "wander", 0.0
        if len(halves) >= 3:
            m = sum(halves) / len(halves)
            sd = math.sqrt(sum((h - m) ** 2 for h in halves) / len(halves))
            if m > 0 and sd / m < 0.3:
                kind, period = "lfo", 2.0 * m
        if kind == "wander" and c.jumps >= 6 and c.jumps > 0.5 * c.n:
            kind = "steps"
        if not quiet:
            c.cv_first, c.wander_said = now, False
        c.cv, c.cv_t, c.cv_check, c.period = kind, now, now, period
        if not quiet and kind != "wander":
            self.report_cv(c)
        return kind

    def report_cv(self, c, again=False):
        n = c.name
        if c.cv == "lfo":
            data = "%s moving by itself: wave, period %.1f s, range %s..%s" % (n, c.period, fmt_val(n, c.lo),
                                                                              fmt_val(n, c.hi))
            per = "%.0f seconds" % c.period if c.period >= 2 else "%.1f seconds" % c.period
            self.say(6, "cv:" + n, data, lambda: fill(self.voice.pick("lfo", P.LFO), name=self.name(n),
                                                      period=per))
        elif c.cv == "steps":
            data = "%s moving by itself: steps (%d jumps), range %s..%s" % (n, c.jumps, fmt_val(n, c.lo),
                                                                             fmt_val(n, c.hi))
            self.say(6, "cv:" + n, data, lambda: fill(self.voice.pick("steps", P.STEPS), name=self.name(n)))
        else:
            data = "%s moving by itself: wandering, range %s..%s" % (n, fmt_val(n, c.lo), fmt_val(n, c.hi))
            self.say(6, "cv:" + n, data, lambda: fill(self.voice.pick("wander", P.WANDER), name=self.name(n)))

    def report_move(self, c):
        n, frm, to, d = c.name, c.v0, c.v, max(0.0, c.t - c.t0)
        mag, spread = to - frm, c.hi - c.lo
        data = "%s %s > %s in %.1f s" % (n, fmt_val(n, frm), fmt_val(n, to), d)
        if c.rev:
            data += ", %d reversal%s, range %s..%s" % (c.rev, "" if c.rev == 1 else "s", fmt_val(n, c.lo),
                                                        fmt_val(n, c.hi))
        prio, pool, key = 4, None, None
        returned = [s for s in c.settled if self.now - s[0] > 20.0 and abs(s[1] - to) < 0.015]
        c.settled = (c.settled + [(self.now, to)])[-12:]
        self.recent_moves = [m for m in self.recent_moves if self.now - m[0] < 2.5] + [(self.now, n)]
        fields = {}
        if c.rev >= 2 and spread > 0.06:
            pool, key = P.INDECISION, "indecision"
        elif n == "pitch" and abs(mag) > 0.004:
            st = int(round((to - frm) * 60.0))
            if abs(to - 0.6) < 0.004:
                pool, key = P.UNISON, "unison"
            elif abs(st) == 12:
                pool, key = (P.OCTAVE_UP if st > 0 else P.OCTAVE_DOWN), "oct%d" % (st > 0)
            elif 0 < abs(st) <= 24:
                pool, key = P.PITCH_JUMP, "pitchjump"
                fields = {"interval": INTERVALS.get(abs(st), "%d semitones" % abs(st)),
                          "dir": "up" if st > 0 else "down"}
        elif n == "speed":
            f0, f1 = 8.0 * frm - 4.0, 8.0 * to - 4.0
            if f1 < -0.05 <= f0:
                pool, key, prio = P.BACKWARDS, "backwards", 5
            elif abs(f1) < 0.05 <= abs(f0):
                pool, key, prio = P.STOPPED, "stopped", 5
            elif abs(f1 - 1.0) < 0.03 <= abs(f0 - 1.0):
                pool, key = P.NORMAL, "normal"
            elif abs(mag) > 0.005:
                pool, key = (P.UP if abs(f1) > abs(f0) else P.DOWN)["speed"], "speed%d" % (abs(f1) > abs(f0))
        if pool is None:
            if returned and abs(frm - to) > 0.08:
                pool, key = P.RETURNED, "returned"
            elif to >= 0.985 and mag > 0.05:
                pool, key = P.TOP, "top"
            elif to <= 0.015 and mag < -0.05:
                pool, key = P.BOTTOM, "bottom"
            elif abs(mag) < 0.03:
                pool, key, prio = P.SMALL, "small", 2
            elif abs(mag) > 0.6:
                pool, key, prio = P.BIG, "big", 5
            elif n in P.UP:
                pool, key = (P.UP if mag > 0 else P.DOWN)[n], "%s%d" % (n, mag > 0)
            else:
                pool, key = P.SMALL, "small"
            if not c.touched and key not in ("small", "returned"):
                pool, key = P.FIRST_TOUCH, "first"
        c.touched = True
        coda = None
        if abs(mag) > 0.2 and d < 0.25:
            coda = P.FAST
        elif d > 4.0 and abs(mag) > 0.1:
            coda = P.SLOW

        def text(pool=pool, key=key, fields=fields, coda=coda):
            line = fill(self.voice.pick(key, pool), name=self.name(n), **fields)
            if coda:
                line += " " + self.voice.pick("coda_speed%d" % (coda is P.FAST), coda)
            return line
        self.say(prio, "move:" + n, data, text)

    def think_pulses(self, now):
        # Reset as a single press or a burst (not a steady train)
        if self.resets and now - self.resets[-1] > 1.6:
            recent = [t for t in self.resets if self.resets[-1] - t < 2.0]
            if not self.reset_pulses.kind:
                if len(recent) >= 3:
                    n = len(recent)
                    self.say(5, "reset", "reset x%d in %.1f s" % (n, recent[-1] - recent[0]), lambda: fill(
                        self.voice.pick("resetburst", P.RESET_BURST), n=n))
                elif len(recent) == 1:
                    self.say(3, "reset", "reset", lambda: self.voice.pick("reset", P.RESET_ONE))
            self.resets = []
        for p in (self.reset_pulses, self.onset_pulses):
            a = p.analyse(now)
            if a:
                kind, bpm, mean, cv = a
                if p.kind is None:
                    self.pulse_say(p, kind, bpm, cv, P.PULSE_REGULAR if kind == "regular" else (
                        P.PULSE_LOOSE if kind == "loose" else P.PULSE_IRREGULAR), "pulse_" + kind)
                elif now - p.changed_t > 15.0:
                    if kind != p.kind:
                        self.pulse_say(p, kind, bpm, cv, P.PULSE_REGULAR if kind == "regular" else (
                            P.PULSE_LOOSE if kind == "loose" else P.PULSE_IRREGULAR), "pulse_" + kind)
                    elif kind != "irregular" and abs(bpm - p.bpm) > 0.08 * p.bpm:
                        self.pulse_say(p, kind, bpm, cv, P.PULSE_FASTER if bpm > p.bpm else P.PULSE_SLOWER,
                                       "pulse_tempo")
                p.mean = mean
            elif p.kind and p.times and now - p.times[-1] > max(3.0 * (p.mean or 1.0), 2.5):
                what = p.what
                self.say(4, "pulsestop:" + what, "%s: pulse stopped" % what, lambda: fill(
                    self.voice.pick("pulsestop", P.PULSE_STOP), what=what))
                p.kind = None
                p.times.clear()

    def pulse_say(self, p, kind, bpm, cv, pool, key):
        p.kind, p.bpm, p.changed_t = kind, bpm, self.now
        what = p.what
        data = "%s: %s pulse, %.0f bpm, timing spread %.0f%%" % (what, kind, bpm, cv * 100)
        b = int(round(bpm))
        self.say(6, "pulse:" + what, data, lambda: fill(self.voice.pick(key, pool), what=what, bpm=b))

    def think_sound(self, now):
        if not self.frames:
            return
        t, lin, lout, cent, low = self.frames[-1]
        quiet = lin < -55.0
        if quiet:
            if self.quiet_since is None:
                self.quiet_since, self.silence_n, self.silence_next = t, 0, 20.0
            q = now - self.quiet_since
            if q >= self.silence_next:
                # 20 s, 60 s, then every 3 minutes
                k = min(self.silence_n, 2)
                pool, prio = [(P.SILENCE_SHORT, 3), (P.SILENCE_LONG, 5), (P.SILENCE_VERY_LONG, 4)][k]
                self.silence_n += 1
                self.silence_next = 60.0 if self.silence_n == 1 else self.silence_next + 180.0
                ds = dur(q)
                self.say(prio, "silence", "in silent for %s" % ds, lambda pool=pool, ds=ds, k=k: fill(
                    self.voice.pick("sil%d" % k, pool), dur=ds))
        else:
            if self.quiet_since is not None and t - self.quiet_since >= 8.0:
                ds = dur(t - self.quiet_since)
                self.say(6, "arrive", "sound in after %s of silence, %.0f dB" % (ds, lin), lambda: fill(
                    self.voice.pick("arrive", P.ARRIVE), dur=ds))
            self.quiet_since = None
        # frozen, holding on alone
        if self.freeze_t is not None:
            held = now - self.freeze_t
            if held > 120.0 * (self.freeze_said + 1):
                self.freeze_said += 1
                dh = dur(held)
                self.say(3, "freezelong", "freeze held %s" % dh, lambda: fill(
                    self.voice.pick("freezelong", P.FREEZE_LONG), dur=dh))
            if quiet and self.quiet_since is not None and now - self.quiet_since > 15 and lout > -45 and \
                    not self.frozen_alone_said:
                self.frozen_alone_said = True
                self.say(4, "frozenalone", "freeze on, in silent, out %.0f dB" % lout, lambda: self.voice.pick(
                    "frozenalone", P.FROZEN_ALONE))
        if now - self.trend_t >= 2.0:
            self.trend_t = now
            self.think_trends(now)
        if not quiet and lin > -45.0 and now - self.last_print_t >= 4.0:
            self.last_print_t = now
            self.think_recognise(now)

    def think_trends(self, now):
        def stats(t0, t1):
            w = [f for f in self.window(t0, t1) if f[1] > -50.0]
            if len(w) < 0.6 * (t1 - t0) * 4:
                return None
            n = len(w)
            return (sum(f[1] for f in w) / n, math.exp(sum(math.log(max(f[3], 30.0)) for f in w) / n),
                    sum(f[4] for f in w) / n, sum(f[2] for f in w) / n)
        new, mid, old = stats(now - 6, now), stats(now - 13, now - 7), stats(now - 20, now - 14)
        if not (new and mid and old) or self.frames[-1][1] < -50.0:
            return
        lv, ce, lo = new[0] - old[0], new[1] / old[1], new[2] - old[2]
        base = "over 14 s: "
        if ce > 1.3 and old[1] < mid[1] < new[1]:
            self.say(5, "bright", base + "centroid %d > %d Hz" % (old[1], new[1]), lambda: self.voice.pick(
                "brighter", P.BRIGHTER), cool=30)
        elif ce < 1 / 1.3 and old[1] > mid[1] > new[1]:
            self.say(5, "bright", base + "centroid %d > %d Hz" % (old[1], new[1]), lambda: self.voice.pick(
                "darker", P.DARKER), cool=30)
        if lo > 0.15:
            self.say(5, "lows", base + "lows %d%% > %d%%" % (old[2] * 100, new[2] * 100), lambda: self.voice.pick(
                "lowsup", P.LOWS_UP), cool=30)
        elif lo < -0.15:
            self.say(5, "lows", base + "lows %d%% > %d%%" % (old[2] * 100, new[2] * 100), lambda: self.voice.pick(
                "lowsdown", P.LOWS_DOWN), cool=30)
        if lv > 8.0 and old[0] < mid[0] < new[0]:
            self.say(4, "level", base + "in %.0f > %.0f dB" % (old[0], new[0]), lambda: self.voice.pick(
                "louder", P.LOUDER), cool=30)
        elif lv < -8.0 and old[0] > mid[0] > new[0]:
            self.say(4, "level", base + "in %.0f > %.0f dB" % (old[0], new[0]), lambda: self.voice.pick(
                "softer", P.SOFTER), cool=30)
        if new[3] - new[0] > 9.0:
            self.say(2, "myvoice", "out %.0f dB, in %.0f dB" % (new[3], new[0]), lambda: self.voice.pick(
                "myvoice", P.MY_VOICE_LOUD), cool=120)

    def fingerprint(self, now):
        w = [f for f in self.window(now - 4.0, now + 1.0) if f[1] > -50.0]
        if len(w) < 8:
            return None
        n = len(w)
        lin = sum(f[1] for f in w) / n
        cent = math.exp(sum(math.log(max(f[3], 30.0)) for f in w) / n)
        low = sum(f[4] for f in w) / n
        p = self.onset_pulses
        bpm = p.bpm if p.kind and p.kind != "irregular" else 0.0
        fp = (int(round(lin / 6.0)), int(round(math.log(cent / 200.0, 2))), int(low * 4.0), int(bpm // 25))
        return fp, {"in": lin, "cent": cent, "low": low, "bpm": bpm}

    def think_recognise(self, now):
        got = self.fingerprint(now)
        if not got:
            return
        fp, raw = got

        def close(a, b):
            return sum(abs(x - y) for x, y in zip(a, b)) <= 1
        old = [p for p in self.prints if now - p[0] > 45.0 and close(p[1], fp)]
        recent = [p for p in self.prints if 4.0 < now - p[0] <= 30.0 and close(p[1], fp)]
        self.prints = (self.prints + [(now, fp, raw)])[-400:]
        if not old or recent:
            return
        then = old[0]
        r0 = then[2]
        diffs = []
        if raw["low"] - r0["low"] > 0.06:
            diffs.append("lows_up")
        elif raw["low"] - r0["low"] < -0.06:
            diffs.append("lows_down")
        if raw["cent"] / r0["cent"] > 1.15:
            diffs.append("brighter")
        elif raw["cent"] / r0["cent"] < 0.87:
            diffs.append("darker")
        if raw["in"] - r0["in"] > 3.0:
            diffs.append("louder")
        elif raw["in"] - r0["in"] < -3.0:
            diffs.append("softer")
        if raw["bpm"] and r0["bpm"]:
            if raw["bpm"] > r0["bpm"] * 1.06:
                diffs.append("faster")
            elif raw["bpm"] < r0["bpm"] * 0.94:
                diffs.append("slower")
        ago = dur(now - then[0])
        data = "heard %s ago: in %.0f > %.0f dB, %d > %d Hz, lows %d%% > %d%%" % (
            ago, r0["in"], raw["in"], r0["cent"], raw["cent"], r0["low"] * 100, raw["low"] * 100)

        def text():
            if not diffs:
                return fill(self.voice.pick("recsame", P.RECOGNISE_SAME), ago=ago)
            frag = " ".join(self.voice.pick("diff_" + d, P.DIFF[d]) for d in diffs[:2])
            line = fill(self.voice.pick("rec", P.RECOGNISE), ago=ago, diff=frag)
            coda = self.voice.pick("codadiff", P.CODA_DIFF + [""])
            return (line + " " + coda).strip()
        self.say(6, "recognise", data, text, cool=90)

    def think_time(self, now):
        if self.connected and self.milestones and now - self.connect_t >= self.milestones[0] * 60.0:
            m = self.milestones.pop(0)
            self.say(2, "time", "connected %d min" % m, lambda: fill(self.voice.pick("time", P.TIME), mins=m))
        if now - self.last_touch > 50.0 and now - self.last_said > 40.0 and self.frames:
            silent = self.frames[-1][1] < -55.0
            self.say(1, "idle", "untouched for %s" % dur(now - self.last_touch), lambda: self.voice.pick(
                "idle%d" % silent, P.IDLE_SILENT if silent else P.IDLE_SOUND), cool=100)

    # ------------------------------------------------------------------ speak
    def speak(self, now):
        self.cands = [c for c in self.cands if now - c[4] < (30.0 if c[0] >= 9 else 12.0)]
        if not self.connected or not self.cands or now < self.busy_until:
            return None
        top = max(c[0] for c in self.cands)
        if now - self.last_said < (1.0 if top >= 7 else self.settings["pace"]):
            return None
        moves = [c for c in self.cands if c[1].startswith("move:")]
        if len(moves) >= 3 and top < 7:
            names = [c[1][5:] for c in moves]
            self.cands = [c for c in self.cands if not c[1].startswith("move:")]
            n = len(names)
            chosen = (5, "many", "%d controls moved: %s" % (n, ", ".join(names)), lambda: fill(
                self.voice.pick("many", P.MANY), n=n), now, self.snapshot())
        else:
            best = sorted(self.cands, key=lambda c: (-c[0], c[4]))[0]
            self.cands.remove(best)
            chosen = best
        prio, key, data, text_fn, t0, snap = chosen
        self.spoken[key] = now
        poem = text_fn()
        if key != "greet" and "?" not in poem and self.rng.random() * 100.0 < self.settings["coda"]:
            poem += " " + self.voice.pick("coda", P.CODA)
        out = ""
        level = self.settings["data"]
        if level != "off":
            full = level == "full" and snap and key != "greet"
            out = "[%s %s%s]\n" % (clock(t0), data, (" / " + snap) if full else "")
        out += poem + "\n\n"
        out = clean(out)
        self.last_said = now
        self.busy_until = now + len(out) / CPS
        return out


# ------------------------------------------------------------------------------------------------ the module
def read_state(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except (IOError, OSError):
        return ""


def run(events, state, show_data, log_path, settings=None):
    log = open(log_path, "a") if log_path else None

    def note(msg):
        if log:
            log.write("%.1f %s\n" % (time.time(), msg))
            log.flush()
    nar = Narrator(show_data=show_data, settings=settings)
    while not os.path.exists(events):
        time.sleep(0.2)
    # os.read on a raw descriptor: always sees appended lines (glibc 2.28+ makes stdio's end-of-file sticky,
    # which could stop Python 2's file.read() from seeing anything new)
    fd = os.open(events, os.O_RDONLY)
    buf = ""
    last_data = time.time()
    seen = False
    next_state = 0.0
    note("narrator started, settings: data %(data)s, pace %(pace)g s, coda %(coda)g%%" % nar.settings)
    while True:
        chunk = os.read(fd, 65536)
        if chunk:
            buf += chunk.decode("ascii", "replace") if not isinstance(chunk, str) else chunk
            lines = buf.split("\n")
            buf = lines.pop()
            for line in lines:
                nar.feed(line)
            last_data = time.time()
            seen = True
        elif seen and time.time() - last_data > 4.0:
            note("no events for 4 s: the instrument has stopped")
            return
        if time.time() >= next_state:
            next_state = time.time() + 1.0
            nar.set_connected(read_state(state).startswith("connected"))
        out = nar.tick()
        if out:
            try:
                sys.stdout.write(out)
                sys.stdout.flush()
            except (IOError, OSError):
                note("keyboard gone")
                return
            note(out.replace("\n", " | "))
        time.sleep(0.1)


def replay(path, show_data=True, seed=1, settings=None):
    """The story of a recorded events file (PC tests): returns [(t, text)]."""
    nar = Narrator(rng=random.Random(seed), show_data=show_data, settings=settings)
    with open(path) as f:
        lines = [l for l in f.read().split("\n") if l.strip()]
    told = []
    nar.set_connected(True)
    t, i = 0.0, 0
    end = float(lines[-1].split()[1]) + 15.0 if lines else 0.0
    while t <= end:
        while i < len(lines) and float(lines[i].split()[1]) <= t:
            nar.feed(lines[i])
            i += 1
        out = nar.tick(t)
        if out:
            told.append((t, out))
        t += 0.1
    return told


def main(argv):
    args = {"events": "/dev/shm/neb_bt/events", "state": "/dev/shm/neb_bt/state", "log": None, "data": True,
            "replay": None, "settings": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--events", "--state", "--log", "--replay", "--settings") and i + 1 < len(argv):
            args[a[2:]] = argv[i + 1]
            i += 1
        elif a == "--no-data":
            args["data"] = False
        i += 1
    settings = read_settings(args["settings"])
    if args["replay"]:
        for t, text in replay(args["replay"], args["data"], settings=settings):
            sys.stdout.write(text)
        return 0
    try:
        run(args["events"], args["state"], args["data"], args["log"], settings)
    except Exception:
        # on the module: the reason goes to narrator.log (copied to the stick), not just to the journal
        import traceback
        if args["log"]:
            with open(args["log"], "a") as f:
                f.write("narrator crashed:\n" + traceback.format_exc())
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
