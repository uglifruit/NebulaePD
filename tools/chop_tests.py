#!/usr/bin/env python3
"""Offline tests of 09_chop (Pd batch runs + log/WAV checks). Run from the repo root on Windows:

  python tools/chop_tests.py [scenario ...]        (no arguments = all)

Test audio: one bar at 120 BPM (16 steps of 125 ms) with a tone burst on every other step, each at its own
frequency (250 Hz x 1.2^i), two of them off the grid (+6 ms, -4 ms). So the output shows which slice played
where: burst onsets (times) and zero-crossing frequencies. Pd's test prints ("ev:", "slices:", "st:", ...) carry
the logical time in ms. Renders and logs go to firmware/dist/chop_sim/<scenario>/.

Scenarios
  file      a stick WAV, free-running clock: 8 onset slices, replayed in time (each hit 3 ms after its step)
  grab      the loop as live input on a 500 ms clock: Record grabs the next bar, which then replays (input muted)
  mono44    a mono 44.1 kHz file: sr-corrected pitch, both outputs, slices
  shuffle   Start 1: other slices on the same steps; new order every cycle; Freeze holds the order
  fx        reverse / ratchet / pitch / jumps / gate / density as dice outcomes in the event log; WAV clicks
  clock     external clock (400 ms): lock, jitter (+-2 ms), stop (free-run on), restart after 3 s (step 1)
  sync      Source gate: the next beat is step 1; just after a beat: that beat re-fires as step 1
  sens      alt Size: equal 16ths (CCW), sensitivity changes the slice count; a pad falls back to the grid
  long      a 12 s file is treated as 4 bars of it at the clock tempo
  filehold  grab, then a file, then File held: back to the grab
  cpu       60 s of everything on, against 04_glitch's batch time
"""
import math
import os
import re
import subprocess
import sys
import time
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen     # noqa: E402
import chop    # noqa: E402

PD = r"C:\Program Files\Pd\bin\pd.com"
OUT = os.path.join(ROOT, "firmware", "dist", "chop_sim").replace("\\", "/")
SR = 48000
STEP_MS = 125.0
HITS = [0, 2, 4, 6, 8, 10, 12, 14]
FREQS = [250 * 1.2 ** i for i in range(8)]
OFFS_MS = {6: 6.0, 10: -4.0}            # off-grid hits (step: ms)
PRE = chop.PRE_MS
CH0 = ("\\; blend 1 \\; start 0 \\; size 1 \\; density 1 \\; overlap 0 \\; window 0 \\; speed 0.5 \\; pitch 0.6 "
       "\\; freeze 0 \\; record 0 \\; source 0 \\; filestate 0")
FAILS = []


# --- test audio ------------------------------------------------------------------------------------------------------
def onset_s(i):
    k = HITS[i]
    return (k * STEP_MS + OFFS_MS.get(k, 0.0)) / 1000


def loop_audio(sr, bars=1):
    n = int(round(2.0 * bars * sr))
    x = np.zeros(n)
    t = np.arange(int(0.1 * sr)) / sr
    env = np.minimum(1, t / 0.0005) * np.exp(-t / 0.025)
    for b in range(bars):
        for i, f in enumerate(FREQS):
            s0 = int(round((2.0 * b + onset_s(i)) * sr))
            seg = 0.5 * np.sin(2 * np.pi * f * t) * env
            x[s0:s0 + len(seg)] += seg[:max(0, n - s0)]
    return x


def pad_audio(sr, sec=2.0):
    t = np.arange(int(sec * sr)) / sr
    return 0.2 * (np.sin(2 * np.pi * 220 * t) + np.sin(2 * np.pi * 277.2 * t) + np.sin(2 * np.pi * 330 * t))


def write_wav(path, x, sr, channels=2):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    if channels == 2:
        pcm = np.repeat(pcm, 2)
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def read_wav(path):
    """Pd's float WAV (or PCM16) -> (sr, array [frames, channels])."""
    b = open(path, "rb").read()
    pos, fmt, data = 12, None, None
    while pos + 8 <= len(b):
        cid, size = b[pos:pos + 4], int.from_bytes(b[pos + 4:pos + 8], "little")
        body = b[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            fmt = (int.from_bytes(body[0:2], "little"), int.from_bytes(body[2:4], "little"),
                   int.from_bytes(body[4:8], "little"), int.from_bytes(body[14:16], "little"))
        elif cid == b"data":
            data = body
        pos += 8 + size + (size & 1)
    tag, ch, sr, bits = fmt
    if bits == 24:
        u = np.frombuffer(data[:len(data) // 3 * 3], np.uint8).reshape(-1, 3).astype(np.int32)
        a = ((u[:, 0] | (u[:, 1] << 8) | (u[:, 2] << 16)) ^ 0x800000) - 0x800000
        a = a / 8388608.0
    else:
        a = np.frombuffer(data, "<f4" if bits == 32 else "<i2").astype(float)
        if bits == 16:
            a /= 32768
    return sr, a[:len(a) // ch * ch].reshape(-1, ch)


# --- running ---------------------------------------------------------------------------------------------------------
def run(name, steps, dur_ms, files=None, extra_test=None):
    d = f"{OUT}/{name}"
    os.makedirs(f"{d}/wavs", exist_ok=True)
    for f in os.listdir(f"{d}/wavs") if files is not None else []:      # files=None: keep what's there
        os.remove(f"{d}/wavs/{f}")
    for fname, (x, sr, ch) in (files or {}).items():
        write_wav(f"{d}/wavs/{fname}", x, sr, ch)
    test = dict(steps=steps + [(dur_ms, "\\; pd quit")], wav=f"{d}/out.wav", dir=f"{d}/wavs",
                patterns=["*.wav"])
    test.update(extra_test or {})
    gen.write(f"{d}/t.pd", chop.chop_patch(gen.Canvas, gen.controls_canvas, test=test))
    t0 = time.time()
    p = subprocess.run([PD, "-nogui", "-batch", "-r", "48000", "-stderr", "-open", f"{d}/t.pd"],
                       capture_output=True, text=True, timeout=600)
    el = time.time() - t0
    log = p.stdout + p.stderr
    open(f"{d}/log.txt", "w").write(log)
    sr, w = read_wav(f"{d}/out.wav")
    return Log(log), w, el


class Log:
    def __init__(self, text):
        self.text = text
        self.rows = []
        for line in text.splitlines():
            m = re.match(r"(\w+): (.*)", line.strip())
            if m:
                vals = m.group(2).split()
                self.rows.append((m.group(1), vals))

    def get(self, label):
        out = []
        for lab, v in self.rows:
            if lab == label:
                out.append([float(a) if re.match(r"^-?[\d.e+-]+$", a) else a for a in v])
        return out

    def errors(self):
        return [ln for ln in self.text.splitlines() if "error" in ln.lower() or "no such" in ln.lower()
                or "bad arguments" in ln.lower() or "couldn't" in ln.lower()]


def check(name, ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(f"{name}: {msg}")


def bursts(x, sr, t0=0.0, t1=None, thr=0.05):
    """Tone-burst onsets (s) and zero-crossing frequencies in [t0, t1)."""
    i0, i1 = int(t0 * sr), int((t1 or len(x) / sr) * sr)
    seg = x[i0:i1]
    env = np.abs(seg)
    out = []
    i = 0
    while i < len(seg):
        if env[i] > thr:
            w = seg[i + int(0.004 * sr):i + int(0.045 * sr)]
            zc = np.count_nonzero(np.diff(np.signbit(w)))
            f = zc / 2 / (len(w) / sr) if len(w) else 0
            out.append(((i0 + i) / sr, f))
            # skip to the end of this burst: the envelope stays below thr for 20 ms
            j = i + int(0.03 * sr)
            while j < len(seg) and np.max(env[j:j + int(0.02 * sr)], initial=0) > thr:
                j += int(0.005 * sr)
            i = j
        else:
            i += 1
    return out


def nearest_freq(f):
    k = int(np.argmin([abs(math.log(f / g)) for g in FREQS])) if f > 0 else -1
    return k, (abs(math.log(f / FREQS[k])) < 0.06 if k >= 0 else False)


def clicks(x, thr):
    x = x[:-int(0.4 * SR)]                  # the recording table outlasts the DSP run: its tail is zeros
    d = np.abs(np.diff(x))
    return int(np.count_nonzero(d > thr)), float(d.max(initial=0))


def no_errors(name, log):
    e = log.errors()
    check(name, not e, f"no Pd errors ({len(e)}: {e[:3]})")


# --- scenarios -------------------------------------------------------------------------------------------------------
def sc_file():
    """No clock: free-run 120 BPM from 1 s (steps at 1000 + 125 n ms). File press at 1.2 s -> the slot plays from
    the next bar line (3 s)."""
    name = "file"
    log, w, _ = run(name, [(10, CH0), (1200, "\\; filestate 1"), (1260, "\\; filestate 0")], 7000,
                    files={"a_loop.wav": (loop_audio(SR), SR, 2)})
    no_errors(name, log)
    sl = log.get("slices")
    check(name, len(sl) >= 1 and sl[-1][2] == 8 and sl[-1][3] == 0 and sl[-1][4] == 16,
          f"slices: 8 onset slices over 16 steps ({sl[-1][1:] if sl else None})")
    starts = [r[2] for r in log.get("slice")][-8:]
    err = [s / SR - max(0, onset_s(i) - PRE / 1000) for i, s in enumerate(starts)]
    check(name, len(starts) == 8 and all(-0.0005 < e < 0.001 for e in err),
          f"slice starts at the onset - {PRE:g} ms (-0.5..+1 ms): " + " ".join(f"{e * 1000:+.2f}" for e in err))
    sw = log.get("sw")
    check(name, sw and abs(sw[0][0] - 3000) < 1 and sw[0][1] == 2, f"switch to slot 2 at the 3 s bar line ({sw})")
    b = bursts(w[:, 0], SR, 3.0 - 0.3, 7.0 - 0.3)
    good = 0
    for tb, f in b:
        k, okf = nearest_freq(f)
        tl = tb + 0.3                           # logical s
        step = (tl - 1.0) / (STEP_MS / 1000)
        dev = (step - round(step)) * STEP_MS
        good += okf and k == (int(round(step)) % 16) // 2 and -0.2 < dev < 3.0
    check(name, len(b) == 16 and good == 16, f"16 bursts in 2 bars, each the slice of its step, 0-3 ms after the "
                                             f"step ({good}/{len(b)})")
    n, mx_ = clicks(w[int(2.7 * SR):, 0], 0.12)
    check(name, n == 0, f"no clicks (max step {mx_:.3f})")


def sc_grab():
    """Test clock 500 ms from 1.2 s (bar 0 at 1.2 s); the loop restarts every bar. Record at 1.5 s -> the grab runs
    3.2..5.2 s, then replays; the input is muted at 5.3 s. Blend 1 = wet only."""
    name = "grab"
    path = f"{OUT}/{name}/src.wav"
    write_wav(path, loop_audio(SR), SR, 2)
    log, w, _ = run(name, [(10, CH0 + f" \\; ch_tload {path}"), (1200, "\\; ch_tclk 500"), (1500, "\\; record 1"),
                           (5300, "\\; ch_tmute 1")], 9200)
    no_errors(name, log)
    sw = log.get("sw")
    check(name, sw and abs(sw[0][0] - 5200) < 2 and sw[0][1] in (0, 1), f"grab plays from the 5.2 s bar line ({sw})")
    an = log.get("ana_g")
    check(name, an and 7 <= an[-1][2] <= 10, f"grab analysis: {an[-1][2] if an else None} candidates (8 hits)")
    sl = log.get("slices")
    check(name, sl and sl[-1][2] == 8, f"8 slices ({sl[-1][1:] if sl else None})")
    b = bursts(w[:, 0], SR, 5.2 - 0.3, 9.2 - 0.3)
    good = 0
    devs = []
    for tb, f in b:
        k, okf = nearest_freq(f)
        tl = tb + 0.3
        step = (tl - 1.2) / (STEP_MS / 1000)
        dev = (step - round(step)) * STEP_MS
        devs.append(dev)
        good += okf and k == (int(round(step)) % 16) // 2 and -1.0 < dev < 4.0
    check(name, len(b) == 16 and good == 16, f"replay: 16 bursts, the right slices on their steps ({good}/{len(b)}; "
                                             f"onset - step {min(devs, default=0):+.1f}..{max(devs, default=0):+.1f} ms)")
    n, mx_ = clicks(w[int(4.9 * SR):, 0], 0.12)
    check(name, n == 0, f"no clicks (max step {mx_:.3f})")


def sc_mono44():
    name = "mono44"
    log, w, _ = run(name, [(10, CH0), (1200, "\\; filestate 1"), (1260, "\\; filestate 0")], 7000,
                    files={"m.wav": (loop_audio(44100), 44100, 1)})
    no_errors(name, log)
    sl = log.get("slices")
    check(name, sl and sl[-1][2] == 8, f"8 slices ({sl[-1][1:] if sl else None})")
    b = bursts(w[:, 0], SR, 2.7, 6.7)
    br = bursts(w[:, 1], SR, 2.7, 6.7)
    good = sum(nearest_freq(f)[1] for _, f in b)
    check(name, len(b) == 16 and good == 16, f"16 bursts at the right pitch (sr corrected): {good}/{len(b)}")
    check(name, len(br) == len(b), f"mono file on both outputs (R {len(br)} bursts)")


def ev_cycles(log, t0, cycle_ms=2000, k0=1000):
    """Events grouped by cycle: {cycle: [(step, slice, rev, semi, dur, ratchet)]}."""
    out = {}
    for r in log.get("ev"):
        t, k, vt, xs, ej, rev, semi, i0, i1, xd, xe, hr = r[:12]
        if t < t0:
            continue
        out.setdefault(int((t - k0) // cycle_ms), []).append((int(k), int(ej), int(rev), semi, xd, int(hr)))
    return out


def sc_shuffle():
    """File at 1.2 s (plays from 3 s). Start 1 from 2.5 s: every hit a random slice, a new order per cycle; Freeze on
    at 7.5 s: 9..13 s repeat; Freeze off at 13.5: new again."""
    name = "shuffle"
    log, w, _ = run(name, [(10, CH0), (1200, "\\; filestate 1"), (1260, "\\; filestate 0"), (2500, "\\; start 1"),
                           (7500, "\\; freeze 1"), (13500, "\\; freeze 0")], 17000,
                    files={"a_loop.wav": (loop_audio(SR), SR, 2)})
    no_errors(name, log)
    cy = ev_cycles(log, 3000)
    order = {c: [e[1] for e in v if True] for c, v in cy.items()}
    steps = {c: [e[0] for e in v] for c, v in cy.items()}
    check(name, all(s == HITS for c, s in steps.items() if c in (1, 2, 3, 4, 5, 6)),
          f"hits stay on the loop's steps: {steps.get(2)}")
    own = sum(o == list(range(8)) for c, o in order.items() if 1 <= c <= 6)
    check(name, own == 0, f"Shuffle 1: no cycle in the original order ({own})")
    check(name, order.get(1) != order.get(2) and order.get(2) != order.get(3), "unfrozen: a new order every cycle")
    check(name, order.get(4) == order.get(5) == order.get(6), f"frozen 9-15 s: the same order "
                                                             f"({order.get(4)} {order.get(5)} {order.get(6)})")
    check(name, order.get(7) != order.get(6), "unfrozen again: new")


def sc_fx():
    """File; then one effect at a time, each for 2 cycles (from 3 s): reverse (window 1), ratchet (overlap 1),
    pitch +12 (pitch 0.8), jumps up (speed 1), jumps down (speed 0), gate (size 0), density 0.5, everything."""
    name = "fx"
    base = "\\; window 0 \\; overlap 0 \\; pitch 0.6 \\; speed 0.5 \\; size 1 \\; density 1"
    seq = [("rev", "\\; window 1"), ("rat", "\\; overlap 1"), ("pitch", "\\; pitch 0.8"), ("up", "\\; speed 1"),
           ("down", "\\; speed 0"), ("gate", "\\; size 0"), ("dens", "\\; density 0.5"),
           ("all", "\\; window 0.5 \\; overlap 0.5 \\; speed 0.85 \\; size 0.6 \\; density 0.8 \\; start 0.5")]
    steps = [(10, CH0), (1200, "\\; filestate 1"), (1260, "\\; filestate 0")]
    for i, (_, m) in enumerate(seq):
        steps.append((2900 + 4000 * i, base + " " + m))
    log, w, _ = run(name, steps, 3000 + 4000 * len(seq) + 100, files={"a_loop.wav": (loop_audio(SR), SR, 2)})
    no_errors(name, log)
    evs = log.get("ev")

    def part(i):
        return [r for r in evs if 3000 + 4000 * i <= r[0] < 7000 + 4000 * i]
    rv = part(0)
    check(name, rv and all(r[5] == 1 for r in rv) and all(r[7] > r[8] for r in rv),
          f"Window 1: every hit reversed ({len(rv)})")
    rt = part(1)
    hr = sorted(set(int(r[11]) for r in rt))
    check(name, hr and set(hr) <= {2, 3, 4} and len(rt) > 16, f"Overlap 1: ratchets x{hr} ({len(rt)} events for 16 "
                                                              f"hits)")
    pt = part(2)
    check(name, pt and all(r[6] == 12 for r in pt), "Pitch 0.8: +12 on every hit")
    up = part(3)
    check(name, up and all(r[6] in (5, 7, 12) for r in up) and len(set(r[6] for r in up)) >= 2,
          f"Speed 1: every hit jumps up {sorted(set(r[6] for r in up))}")
    dn = part(4)
    check(name, dn and all(r[6] in (-12, -24) for r in dn), f"Speed 0: every hit jumps down "
                                                           f"{sorted(set(r[6] for r in dn))}")
    gt_ = part(5)
    check(name, gt_ and all(abs(r[9] - chop.MINMS) < 0.5 or r[9] < 0.04 * 250 for r in gt_),
          f"Size 0: short stabs ({sorted(set(round(r[9], 1) for r in gt_))[:4]} ms)")
    ds = part(6)
    check(name, 3 <= len(ds) <= 13, f"Density 0.5: about half the hits ({len(ds)} of 16)")
    # pitch check in the WAV: +12 -> twice each burst's frequency
    b = bursts(w[:, 0], SR, 11.0 - 0.3, 15.0 - 0.3)
    okp = sum(nearest_freq(f / 2)[1] for _, f in b)
    check(name, len(b) >= 14 and okp >= len(b) - 1, f"+12 bursts at twice the frequency ({okp}/{len(b)})")
    n, mx_ = clicks(w[int(2.7 * SR):, 0], 0.2)
    check(name, n == 0, f"no clicks over all effects (max step {mx_:.3f}, threshold 0.2)")
    check(name, not np.isnan(w).any() and np.abs(w).max() <= 1.0, "no NaN, bounded")


def st_times(log):
    return [(r[0], int(r[1])) for r in log.get("st")]


def sc_clock():
    """Free-run from 1 s (125 ms steps). External clock 400 ms from 2.0 s, +-2 ms jitter; stops at 6.0 s (free-run
    at 400 ms beats); restarts at 9.5 s (gap > 2 s): step 1 at once."""
    name = "clock"
    steps = [(10, CH0)]
    t = 2030.0
    jit = [0, 2, -2, 1, -1, 2, 0, -2, 1, 0]
    i = 0
    pulses = []
    while t < 6000:
        tp = t + jit[i % len(jit)]
        pulses.append(tp)
        i += 1
        t += 400
    t = 9500.0
    while t < 11000:
        pulses.append(t)
        t += 400
    for tp in pulses:
        steps += [(round(tp, 3), "\\; reset 1"), (round(tp + 5, 3), "\\; reset 0")]
    log, w, _ = run(name, steps, 11500)
    no_errors(name, log)
    st = st_times(log)
    free = [t for t, k in st if t < 2030]
    d0 = np.diff(free)
    check(name, len(d0) > 4 and np.allclose(d0, 125, atol=0.01), f"free-run 125 ms steps ({d0[:4]})")
    first = [(t, k) for t, k in st if t >= 2030][0]
    check(name, abs(first[0] - 2030) < 0.01 and first[1] == 0, f"first pulse = step 1 now ({first})")
    locked = [t for t, k in st if 2900 <= t < 6000]
    d1 = np.diff(locked)
    check(name, len(d1) > 10 and np.all(np.abs(d1 - 100) < 4), f"locked: 100 ms steps +- jitter "
                                                               f"({d1.min():.1f}..{d1.max():.1f})")
    beats = [t for t, k in st if 2030 <= t < 6000 and k % 4 == 0]
    dev = [min(abs(b - p) for p in pulses) for b in beats]
    check(name, max(dev) < 3, f"beat steps on the pulses (max {max(dev):.1f} ms), never doubled")
    ks = [k for t, k in st if 2030 <= t < 9500]
    gaps = [b for a, b in zip(ks, ks[1:]) if b != (a + 1) % 16]
    check(name, not gaps, f"step numbers continuous through jitter and the stop ({gaps[:5]})")
    fr = [t for t, k in st if 6200 <= t < 9400]
    d2 = np.diff(fr)
    check(name, len(d2) > 10 and np.allclose(d2, 100, atol=1.5), f"stopped: free-runs on at the last tempo ({d2[:3]})")
    rs = [(t, k) for t, k in st if t >= 9500][0]
    check(name, abs(rs[0] - 9500) < 0.01 and rs[1] == 0, f"restart after 3.5 s: step 1 at the first pulse ({rs})")
    # tempo ramps: 400 -> 640 ms (+30 per beat) and back down (-40 per beat): no doubled or skipped steps
    steps = [(10, CH0)]
    t, iv, pulses = 2000.0, 400.0, []
    for d in [30] * 8 + [-40] * 8:
        pulses.append(t)
        t += iv
        iv += d
    for tp in pulses:
        steps += [(round(tp, 3), "\\; reset 1"), (round(tp + 5, 3), "\\; reset 0")]
    log, w, _ = run(name + "_ramp", steps, t + 100)
    st = [(t_, k) for t_, k in st_times(log) if pulses[0] <= t_ <= pulses[-1]]
    ks = [k for _, k in st]
    gaps = [b for a, b in zip(ks, ks[1:]) if b != (a + 1) % 16]
    check(name, not gaps and len(ks) == 4 * (len(pulses) - 1) + 1,
          f"tempo ramps: one step per 16th, none doubled or skipped ({len(ks)} steps for {len(pulses)} beats)")
    beats = [t_ for t_, k in st if k % 4 == 0]
    dev = [min(abs(b - p) for p in pulses) for b in beats]
    print(f"  info ramp: beat steps vs pulses: median {np.median(dev):.1f} ms, max {max(dev):.1f} ms")


def sc_sync():
    """Free-run 120 BPM from 1 s (beats at 1000 + 500 n). Source gate at 2.2 s (mid-beat) -> the beat at 2.5 s is
    step 1; at 4.010 s (10 ms after a beat) -> that beat re-fires as step 1."""
    name = "sync"
    log, w, _ = run(name, [(10, CH0), (2200, "\\; sourcegate 1"), (2205, "\\; sourcegate 0"),
                           (4010, "\\; sourcegate 1 \\; source 1"), (4015, "\\; sourcegate 0")], 5000)
    no_errors(name, log)
    st = st_times(log)
    a = [k for t, k in st if abs(t - 2500) < 0.01]
    check(name, a == [0], f"gate mid-beat: the next beat is step 1 ({a})")
    b = [(t, k) for t, k in st if 3999 <= t <= 4011]
    check(name, len(b) == 2 and b[1] == (4010, 0), f"gate 10 ms after a beat: re-fired as step 1 ({b})")
    c_ = [(t, k) for t, k in st if 4100 <= t < 4300]
    check(name, c_ and c_[0][1] == 1, f"latch toggle from the same gate is ignored (one event): {c_[:2]}")


def sc_sens():
    """File (8 hits) then alt Size: 0 (grid: 16), 0.15 (insensitive), 0.9 (sensitive); then a pad file -> grid."""
    name = "sens"
    alt = lambda v0, v1, t: [(t + 5 * i, f"\\; size_alt {v0 + (v1 - v0) * i / 10:g}") for i in range(11)]
    log, w, _ = run(name, [(10, CH0), (1200, "\\; filestate 1"), (1260, "\\; filestate 0")]
                    + alt(0.5, 0.0, 4000) + alt(0.0, 0.5, 5000) + [(6000, "\\; filestate 1"),
                                                                  (6060, "\\; filestate 0")],
                    9500, files={"a_loop.wav": (loop_audio(SR), SR, 2), "b_pad.wav": (pad_audio(SR), SR, 2)})
    no_errors(name, log)
    sl = log.get("slices")
    show = [(r[0], int(r[2]), int(r[3])) for r in sl]
    grid = [s for t, s, g in show if 4000 < t < 4200]
    check(name, grid and grid[-1] == 16, f"alt Size CCW: equal 16ths ({show})")
    back = [s for t, s, g in show if 5000 < t < 5200]
    check(name, back and back[-1] == 8, "back to onsets: 8")
    pad = [(s, g) for t, s, g in show if t > 6000]
    check(name, pad and pad[-1] == (16, 1), f"pad: too few onsets -> grid ({pad})")


def sc_long():
    name = "long"
    log, w, _ = run(name, [(10, CH0), (1200, "\\; filestate 1"), (1260, "\\; filestate 0")], 12000,
                    files={"l.wav": (loop_audio(SR, bars=3), SR, 2)})
    no_errors(name, log)
    sl = log.get("slices")
    check(name, sl and sl[-1][4] == 64 and abs(sl[-1][5] - 6.0 * SR) < 2,
          f"6.0 s file at 120 BPM = 3 bars -> 4 bars of steps, all of it ({sl[-1][1:] if sl else None})")
    log2, w2, _ = run(name + "12", [(10, CH0), (1200, "\\; filestate 1"), (1260, "\\; filestate 0")], 12000,
                      files={"l.wav": (loop_audio(SR, bars=7), SR, 2)})
    sl2 = log2.get("slices")
    check(name, sl2 and sl2[-1][4] == 64 and abs(sl2[-1][5] - 8.0 * SR) < 2,
          f"14 s file (> 6 bars): its first 4 bars ({sl2[-1][1:] if sl2 else None})")


def sc_filehold():
    """Grab (as in grab), then File at 6 s (plays from 7.2 s), then File held 9.0-9.6 s: back to the grab at
    11.2 s."""
    name = "filehold"
    path = f"{OUT}/{name}/src.wav"
    write_wav(path, loop_audio(SR), SR, 2)
    log, w, _ = run(name, [(10, CH0 + f" \\; ch_tload {path}"), (1200, "\\; ch_tclk 500"), (1500, "\\; record 1"),
                           (5300, "\\; ch_tmute 1"), (6000, "\\; filestate 1"), (6060, "\\; filestate 0"),
                           (9000, "\\; filestate 1"), (9600, "\\; filestate 0")], 12000,
                    files={"a_loop.wav": (loop_audio(SR), SR, 2)})
    no_errors(name, log)
    sw = [(r[0], int(r[1])) for r in log.get("sw")]
    check(name, len(sw) == 3 and sw[1] == (7200, 2) and sw[2][0] == 11200 and sw[2][1] == sw[0][1],
          f"grab -> file at 7.2 s -> back to the grab at 11.2 s ({sw})")
    ld = log.get("load")
    check(name, len(ld) == 1, f"the held press loads nothing ({len(ld)} loads)")


def sc_cpu():
    """CPU per minute of audio: (63 s run - 3 s run) of chop with everything on (no test prints or WAV recording)
    against the same for 04_glitch's glitch test; best of 3 each. Batch runs = CPU time, so this is a ratio."""
    name = "cpu"
    import glitch
    d = f"{OUT}/{name}"
    os.makedirs(f"{d}/wavs", exist_ok=True)
    write_wav(f"{d}/wavs/a.wav", loop_audio(SR), SR, 2)
    fx = ("\\; window 0.4 \\; overlap 0.6 \\; speed 0.8 \\; size 0.7 \\; density 0.9 \\; start 0.6 "
          "\\; blend 0.7")
    for dur in (3000, 63000):
        steps = [(10, CH0), (1200, "\\; filestate 1"), (1260, "\\; filestate 0"), (2900, fx), (dur, "\\; pd quit")]
        gen.write(f"{d}/c{dur}.pd", chop.chop_patch(gen.Canvas, gen.controls_canvas,
                                                   test=dict(steps=steps, dir=f"{d}/wavs", patterns=["*.wav"])))
        sc = gen.glitch_glitch_test()
        sc["steps"] = [s_ for s_ in sc["steps"] if "quit" not in s_[1]] + [(dur, "\\; pd quit")]
        gen.write(f"{d}/g{dur}.pd", glitch.glitch_patch(gen.Canvas, gen.controls_canvas, test=sc))

    def tm(path):
        best = 1e9
        for _ in range(3):
            t0 = time.time()
            subprocess.run([PD, "-nogui", "-batch", "-r", "48000", "-stderr", "-open", path], capture_output=True)
            best = min(best, time.time() - t0)
        return best
    r = {(k, dur): tm(f"{d}/{k}{dur}.pd") for k in "cg" for dur in (3000, 63000)}
    pc, pg = r["c", 63000] - r["c", 3000], r["g", 63000] - r["g", 3000]
    print(f"  info per minute of audio: chop {pc:.2f} s, 04_glitch {pg:.2f} s ({pc / pg:.2f}x); "
          f"load + 3 s: chop {r['c', 3000]:.2f} s, glitch {r['g', 3000]:.2f} s")
    check(name, pc / pg < 2.0, "under 2x 04_glitch per minute")


def stream(knob, v0, v1, t):
    """An alt knob turned from v0 to v1 over 50 ms (the module streams alt values while Source is held)."""
    return [(t + 5 * i, f"\\; {knob} {v0 + (v1 - v0) * i / 10:g}") for i in range(11)]


def sc_alt():
    """Grab with alt Start 0.5 (2 bars: 3.2..7.2 s); swing (alt Density 1) from 7.5 s; ratchet range x2 (alt
    Overlap 0, Overlap 1) from 9.3 s; soft edges (alt Window 1) from 11.3 s; stutter (alt Blend 1) from 13.3 s;
    Source + Record (record_alt) at 15.3 s = alt defaults."""
    name = "alt"
    path = f"{OUT}/{name}/src.wav"
    write_wav(path, loop_audio(SR), SR, 2)
    st = ([(10, CH0 + f" \\; ch_tload {path}"), (1200, "\\; ch_tclk 500")] + stream("start_alt", 0.0, 0.5, 1300)
          + [(1500, "\\; record 1"), (7300, "\\; ch_tmute 1")] + stream("density_alt", 0.0, 1.0, 7500)
          + [(9300, "\\; overlap 1")] + stream("overlap_alt", 0.5, 0.0, 9300)
          + [(11300, "\\; overlap 0")] + stream("window_alt", 0.2, 1.0, 11300)
          + stream("blend_alt", 0.0, 1.0, 13300) + [(15300, "\\; record_alt 1")])
    log, w, _ = run(name, st, 17300)
    no_errors(name, log)
    sw = log.get("sw")
    sl = log.get("slices")
    check(name, sw and abs(sw[0][0] - 7200) < 2 and sl and sl[-1][4] == 32 and sl[-1][2] == 16,
          f"alt Start 0.5: a 2-bar grab (plays from 7.2 s, 32 steps, 16 slices: {sl[-1][1:] if sl else None})")
    stp = st_times(log)
    odd = [(t - 1200) % 500 for t, k in stp if 8200 <= t < 9200 and k % 2 == 1]
    check(name, odd and all(abs(o - 187.5) < 0.1 or abs(o - 437.5) < 0.1 for o in odd),
          f"swing: odd 16ths half a 16th late ({sorted(set(odd))})")
    ev = log.get("ev")
    rt = [int(r[11]) for r in ev if 9700 <= r[0] < 11300]
    check(name, rt and set(rt) == {2}, f"ratchet range CCW: x2 only ({sorted(set(rt))})")
    ed = [r[10] for r in ev if 11700 <= r[0] < 13300]
    check(name, ed and all(abs(e - 20) < 0.01 or abs(e - r[9] / 2) < 0.01 for e, r in
                           zip(ed, [r for r in ev if 11700 <= r[0] < 13300])), f"soft edges: 20 ms fades ({ed[:3]})")
    js = [int(r[4]) for r in ev if 13700 <= r[0] < 15300]
    check(name, js and len(set(js)) == 1, f"stutter: every hit repeats the previous slice ({sorted(set(js))})")
    after = [(t - 1200) % 500 for t, k in stp if 15800 <= t < 17200 and k % 2 == 1]
    ed2 = [r[10] for r in ev if 15800 <= r[0] < 17200]
    js2 = [int(r[4]) for r in ev if 15800 <= r[0] < 17200]
    check(name, after and all(abs(o - 125) < 0.1 or abs(o - 375) < 0.1 for o in after)
          and ed2 and all(abs(e - chop.EDGE0) < 0.01 for e in ed2) and len(set(js2)) > 1,
          "Source + Record: alt defaults again (straight, 1.5 ms edges, no stutter)")


def sc_stick():
    """The unit's own stick WAVs (firmware/dist/stick_audio, read from the SD image): load each, report bars,
    slices and whether slice starts sit on attacks; render 2 bars at Shuffle 0 (no NaN, bounded)."""
    name = "stick"
    src = os.path.join(ROOT, "firmware", "dist", "stick_audio")
    if not os.path.isdir(src):
        print("  skip (no firmware/dist/stick_audio)")
        return
    import shutil
    for f in sorted(os.listdir(src)):
        n2 = f"{name}_{f[:12]}"
        d = f"{OUT}/{n2}/wavs"
        os.makedirs(d, exist_ok=True)
        for g in os.listdir(d):
            os.remove(f"{d}/{g}")
        shutil.copy(os.path.join(src, f), d)
        log, w, _ = run(n2, [(10, CH0), (1200, "\\; filestate 1"), (1260, "\\; filestate 0")], 9000,
                        files=None)
        no_errors(n2, log)
        sl = log.get("slices")
        fr = log.get("frames")
        if not sl:
            check(n2, False, "loaded and sliced")
            continue
        s_, g_, P_, nn = int(sl[-1][2]), int(sl[-1][3]), int(sl[-1][4]), sl[-1][5]
        srf, x = read_wav(os.path.join(src, f))
        mono = x.mean(axis=1)
        starts = [int(r[2]) for r in log.get("slice")][-s_:]
        att = 0
        for b0 in starts[1:]:
            e0 = np.mean(mono[max(0, b0 - int(0.01 * srf)):b0] ** 2) + 1e-12
            e1 = np.mean(mono[b0:b0 + int(0.01 * srf)] ** 2)
            att += e1 > 2 * e0
        print(f"  info {f}: {len(mono) / srf:.2f} s @ {srf} Hz -> {P_ // 16} bar(s), {s_} slices "
              f"({'grid' if g_ else 'onsets'}), {att}/{max(1, s_ - 1)} starts on an attack")
        check(n2, not np.isnan(w).any() and np.abs(w).max() <= 1.0, "render: no NaN, bounded")
        if not g_:
            check(n2, att >= 0.7 * (s_ - 1), "onset slices start on attacks (>= 70 %)")


SCEN = dict(file=sc_file, grab=sc_grab, mono44=sc_mono44, shuffle=sc_shuffle, fx=sc_fx, clock=sc_clock,
            sync=sc_sync, sens=sc_sens, long=sc_long, filehold=sc_filehold, alt=sc_alt, stick=sc_stick, cpu=sc_cpu)

if __name__ == "__main__":
    names = sys.argv[1:] or list(SCEN)
    for n in names:
        print(f"[{n}]")
        SCEN[n]()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
