#!/usr/bin/env python3
"""Offline tests of 12_shift (Pd batch runs + WAV/log checks). Run from the repo root on Windows:

  python tools/shift_tests.py [scenario ...]        (no arguments = all)

Test input (both sides): a sine (sh_tsf/sh_tsa) and white noise (sh_tna). Renders go to firmware/dist/shift_sim/.

Scenarios
  shift     +100 Hz: a 1 kHz sine comes back at 1100 Hz (the other sideband > 30 dB down); Record flips it to 900;
            Size fully clockwise = left up, right down; Ring = both sidebands; the click = no shift; -300 Hz
  direct    Overlap: the shifted input is heard at once (no delay); Blend 0 = dry only
  time      free time = 2000^Speed ms: echo spacing at two Speed settings
  clock     Reset pulses every 500 ms: time = beat x division (1/4, then 1 bar), jitter ignored, free again 2 s
            after the clock stops; echo spacing on the clock
  climb     feedback with +50 Hz: each echo is 50 Hz higher than the one before (500, 550, 600 ...)
  freeze    Freeze: the loop holds (the level stays up), new input stays out; released, it decays
  barber    File toggles Barber: the loop is a band-pass bell around Window's centre (the bp~ gain measured)
  runaway   everything at the top (feedback 110 %, Ring, ping-pong, drive x6, sweeps) for 40 s: bounded, no NaN
  cpu       per minute of audio against 07_shimmer
"""
import math
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen        # noqa: E402
import shift      # noqa: E402
import shimmer    # noqa: E402
from chop_tests import read_wav, Log, PD  # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "shift_sim").replace("\\", "/")
SR = 48000
V0 = ("\\; blend 1 \\; start 0 \\; size 0 \\; density 0 \\; overlap 0 \\; window 0.5 \\; speed 0.2 "
      "\\; pitch 0.6 \\; freeze 0 \\; record 0 \\; source 0 \\; filestate 0 \\; sh_wd 0")    # no wow: exact tones
FAILS = []


def check(name, ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(f"{name}: {msg}")


def run(name, steps, dur_ms):
    d = f"{OUT}/{name}"
    os.makedirs(d, exist_ok=True)
    test = dict(steps=steps + [(dur_ms, "\\; pd quit")], wav=f"{d}/out.wav")
    gen.write(f"{d}/t.pd", shift.shift_patch(gen.Canvas, gen.controls_canvas, test=test))
    p = subprocess.run([PD, "-nogui", "-batch", "-r", "48000", "-stderr", "-open", f"{d}/t.pd"],
                       capture_output=True, text=True, timeout=900)
    log = p.stdout + p.stderr
    open(f"{d}/log.txt", "w").write(log)
    sr, w = read_wav(f"{d}/out.wav")
    return Log(log), w


def no_errors(name, log):
    e = [ln for ln in log.text.splitlines() if "error" in ln.lower() or "couldn't" in ln.lower()
         or "bad arguments" in ln.lower() or "no such" in ln.lower()]
    check(name, not e, f"no Pd errors ({e[:3]})")


def seg(w, t0, t1, ch=0):
    """logical seconds (WAV time + 0.3)."""
    return w[int((t0 - 0.3) * SR):int((t1 - 0.3) * SR), ch]


def rms_db(x):
    return 10 * math.log10(np.mean(x ** 2) + 1e-20)


def spec(x):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return np.fft.rfftfreq(len(x), 1 / SR), X


def level_at(x, f0, bw=8):
    f, X = spec(x)
    return 20 * math.log10(X[(f > f0 - bw) & (f < f0 + bw)].max() + 1e-12)


def env(x, ms=1.0):
    n = max(1, int(SR * ms / 1000))
    return np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode="same"))


def onsets(x, thr_db=-30, gap_ms=20):
    """times (s, WAV time) where the envelope rises through thr (relative to its max)."""
    e = env(x)
    thr = e.max() * 10 ** (thr_db / 20)
    out, last = [], -1e9
    above = e > thr
    for i in np.flatnonzero(above[1:] & ~above[:-1]) + 1:
        if i - last > gap_ms * SR / 1000:
            out.append(i / SR)
        last = i
    return out


def prints(log, label):
    return [float(v[0]) for lab, v in log.rows if lab == label and v]


# --- scenarios -------------------------------------------------------------------------------------------------------
def sc_shift():
    name = "shift"
    p100 = shift.pitch_for(100)
    st = [(10, V0 + f" \\; sh_tsf 1000 \\; sh_tsa 0.3 \\; pitch {p100:.6f}"),
          (2000, "\\; record 1"), (3500, "\\; record 0 \\; size 1"), (5000, "\\; size 0 \\; source 1"),
          (6500, "\\; source 0 \\; pitch 0.6"), (8000, f"\\; pitch {shift.pitch_for(-300):.6f}")]
    log, w = run(name, st, 9500)
    no_errors(name, log)
    check(name, abs(shift.shift_hz(p100) - 100) < 1e-6 and shift.shift_hz(0.6) == 0, "pitch map: +100 Hz, click 0")
    for t, ch, want, other, what in ((1.0, 0, 1100, 900, "+100 Hz"), (2.5, 0, 900, 1100, "Record: flipped"),
                                     (4.0, 0, 1100, 900, "Size CW: left up"), (4.0, 1, 900, 1100, "right down"),
                                     (8.5, 0, 700, 1300, "-300 Hz")):
        x = seg(w, t, t + 0.8, ch)
        a, b = level_at(x, want), level_at(x, other)
        f, X = spec(x)
        top = f[np.argmax(X)]
        check(name, abs(top - want) < 5 and a - b > 30, f"{what}: peak {top:.0f} Hz (want {want}), the other "
                                                        f"sideband {a - b:.0f} dB down")
    x = seg(w, 5.5, 6.3)
    a, b, cc = level_at(x, 1100), level_at(x, 900), level_at(x, 1000)
    check(name, abs(a - b) < 3 and a - cc > 30, f"Ring: 1100 vs 900 Hz {a - b:+.1f} dB, carrier 1000 Hz "
                                                f"{a - cc:.0f} dB down")
    x = seg(w, 7.0, 7.8)
    f, X = spec(x)
    check(name, abs(f[np.argmax(X)] - 1000) < 5 and level_at(x, 1000) - level_at(x, 1100) > 40,
          "the click: no shift (1000 Hz out, nothing at 1100)")
    pr = prints(log, "fl")
    check(name, any(abs(v - 100) < 0.01 for v in pr) and any(abs(v + 300) < 0.05 for v in pr),
          f"shift values sent: {sorted(set(round(v, 2) for v in pr))[:8]}")


def sc_direct():
    name = "direct"
    st = [(10, V0 + f" \\; sh_tsf 1000 \\; sh_tsa 0.3 \\; pitch {shift.pitch_for(200):.6f} \\; speed 1 "
                    "\\; overlap 1"),
          (3000, "\\; blend 0")]
    log, w = run(name, st, 4000)
    no_errors(name, log)
    x = seg(w, 0.5, 1.5)                    # before the first echo (2 s)
    a, b = level_at(x, 1200), level_at(x, 1000)
    check(name, a - b > 25, f"Overlap: 1200 Hz heard before any echo ({a - b:.0f} dB over the input frequency)")
    x = seg(w, 3.3, 3.9)
    check(name, level_at(x, 1000) - level_at(x, 1200) > 40, "Blend 0: dry only")


def sc_time():
    name = "time"
    st = [(10, V0 + " \\; density 0.6 \\; speed 0.6"), (1500, "\\; sh_tna 0.6"), (1505, "\\; sh_tna 0"),
          (4000, "\\; speed 0.8"), (4800, "\\; sh_tna 0.6"), (4805, "\\; sh_tna 0")]
    log, w = run(name, st, 9000)
    no_errors(name, log)
    for t0, t1, spd in ((1.4, 3.9, 0.6), (4.7, 9.0, 0.8)):
        x = seg(w, t0, t1)
        on = onsets(x)
        want = shift.free_ms(spd)
        sp = np.diff(on[:4]) * 1000
        check(name, len(sp) >= 2 and all(abs(s - want) < 1.5 for s in sp),
              f"Speed {spd}: echo spacing {np.round(sp, 1).tolist()} ms (want {want:.1f})")


def sc_clock():
    name = "clock"
    st = [(10, V0 + " \\; speed 0.5 \\; density 0.6")]
    jit = [0, 2, -1, 1, -2, 0, 1, -1, 2, 0]
    for i, j in enumerate(jit):                       # 10 pulses, 500 ms +- 2 ms
        t = 1200 + 500 * i + j
        st += [(t, "\\; reset 1"), (t + 10, "\\; reset 0")]
    st += [(4000, "\\; sh_tna 0.6"), (4005, "\\; sh_tna 0"), (5800, "\\; speed 0.8")]
    log, w = run(name, st, 9500)
    no_errors(name, log)
    T = prints(log, "T")
    per = prints(log, "per")
    clk = prints(log, "clk")
    check(name, per and all(abs(p - 500) <= 2 for p in per) and len(set(per[-7:])) == 1,
          f"beat follows the clock (+-2 ms jitter), then holds still: {per}")
    check(name, any(abs(v - 500) <= 1 for v in T) and any(abs(v - 2000) <= 4 for v in T),
          f"time = beat x division: 1/4 = 500, 1 bar = 2000 ({sorted(set(round(v, 1) for v in T))})")
    check(name, clk[-1:] == [0] and round(T[-1], 1) == round(shift.free_ms(0.8), 1),
          f"clock stopped: free again, time {T[-1]:.1f} (want {shift.free_ms(0.8):.1f})")
    on = onsets(seg(w, 3.9, 5.7))
    sp = np.diff(on[:3]) * 1000
    check(name, len(sp) >= 2 and all(abs(s - 500) < 1.5 for s in sp), f"echoes on the clock: {np.round(sp, 1)} ms")


def sc_climb():
    name = "climb"
    spd = math.log(200) / math.log(shift.FREE_MAX)
    st = [(10, V0 + f" \\; density 0.8 \\; speed {spd:.6f} \\; sh_tsf 500 \\; pitch {shift.pitch_for(50):.6f}"),
          (1500, "\\; sh_tsa 0.3"), (1600, "\\; sh_tsa 0")]
    log, w = run(name, st, 4000)
    no_errors(name, log)
    t0 = 1.5
    found = []
    for k in range(1, 7):                             # echo k: (t0 + 0.2 k .. + 0.1 s), at 500 + 50 k Hz
        x = seg(w, t0 + 0.2 * k + 0.02, t0 + 0.2 * k + 0.09)
        x = np.pad(x, (0, 8192 - len(x)))
        f, X = spec(x)
        found.append(f[np.argmax(X)])
    want = [500 + 50 * k for k in range(1, 7)]
    check(name, all(abs(a - b) < 12 for a, b in zip(found, want)),
          f"echo pitches {np.round(found).tolist()} (want {want})")


def sc_freeze():
    name = "freeze"
    st = [(10, V0 + f" \\; density 0.3 \\; speed 0.6 \\; sh_tna 0.3 \\; pitch {shift.pitch_for(5):.6f}"),
          (2000, "\\; freeze 1"), (2100, "\\; sh_tna 0 \\; sh_tsf 3000 \\; sh_tsa 0.3"),
          (7000, "\\; freeze 0")]
    log, w = run(name, st, 10000)
    no_errors(name, log)
    a = rms_db(seg(w, 1.0, 2.0))
    b = rms_db(seg(w, 5.5, 6.9))
    m = rms_db(seg(w, 3.0, 4.0))
    # the delay reads between samples (a gentle low-pass per pass): the top end softens in the first second,
    # then the level holds
    check(name, b - a > -6 and abs(b - m) < 2, f"held: {m - a:+.1f} dB after 1-2 s, {b - a:+.1f} dB after 4 s "
                                               f"(before {a:.1f} dB)")
    x = seg(w, 5.5, 6.9)
    f, X = spec(x)
    band = 20 * np.log10(X[(f > 2000) & (f < 4000)].mean() + 1e-12)
    check(name, level_at(x, 3000) - band < 15, "new input stays out (no 3 kHz line in the held loop)")
    check(name, level_at(seg(w, 8.0, 9.0), 3000) - level_at(x, 3000) > 30, "released: the new input comes in")
    check(name, np.abs(w).max() <= 1.0 and np.isfinite(w).all(), f"bounded (peak {np.abs(w).max():.2f})")


def sc_barber():
    name = "barber"
    bc = 200 * 20 ** 0.5
    st = [(10, V0 + f" \\; sh_tsf {bc:.2f} \\; sh_tsa 0.3"), (1500, "\\; filestate 1"), (1600, "\\; filestate 0"),
          (3000, "\\; sh_tsa 0 \\; sh_tna 0.3 \\; density 0.95"), (5000, "\\; filestate 1"),
          (5100, "\\; filestate 0")]
    log, w = run(name, st, 7000)
    no_errors(name, log)
    check(name, prints(log, "bb")[-2:] == [1, 0], f"File toggles Barber: {prints(log, 'bb')}")
    g = rms_db(seg(w, 2.0, 2.9)) - rms_db(seg(w, 0.8, 1.4))
    check(name, abs(g) < 1.5, f"bp~ at the bell's centre: {g:+.2f} dB against the tone path (BARBER_GAIN "
                              f"{shift.BARBER_GAIN})")
    f, Xb = spec(seg(w, 4.0, 4.9))
    _, Xt = spec(seg(w, 5.8, 6.7))
    hi = (f > 6000) & (f < 12000)
    mid = (f > bc / 1.5) & (f < bc * 1.5)
    db = lambda X, m: 20 * np.log10(X[m].mean() + 1e-12)
    tilt_b, tilt_t = db(Xb, mid) - db(Xb, hi), db(Xt, mid) - db(Xt, hi)
    check(name, tilt_b - tilt_t > 10, f"Barber: the loop is a bell (mid over 6-12 kHz {tilt_b:.0f} dB, "
                                      f"tone mode {tilt_t:.0f} dB)")


def sc_runaway():
    name = "runaway"
    st = [(10, V0 + " \\; density 1 \\; source 1 \\; start 1 \\; size 1 \\; overlap 1 \\; sh_tna 0.5 "
                    "\\; sh_tsa 0.5 \\; sh_dr 6 \\; sh_wd 4 \\; sh_wr 5 \\; speed 0.3 \\; window 0.9"),
          (1500, "\\; filestate 1"), (1600, "\\; filestate 0")]
    for i in range(40):
        st.append((2000 + 1000 * i, f"\\; pitch {0.1 + 0.8 * ((i * 0.37) % 1):.3f} \\; speed {(i * 0.29) % 1:.3f} "
                                    f"\\; window {(i * 0.53) % 1:.3f}" + (" \\; freeze 1" if i % 7 == 3 else
                                                                         " \\; freeze 0")))
    log, w = run(name, st, 43000)
    no_errors(name, log)
    check(name, np.isfinite(w).all() and np.abs(w).max() <= 1.0, f"bounded, no NaN (peak {np.abs(w).max():.3f})")
    check(name, rms_db(w[-SR * 5:, 0]) > -40, f"still sounding at the end ({rms_db(w[-SR * 5:, 0]):.1f} dB)")


def sc_cpu():
    name = "cpu"
    d = f"{OUT}/cpu"
    os.makedirs(d, exist_ok=True)
    for dur in (3000, 63000):
        st = [(10, V0 + " \\; density 0.9 \\; sh_tna 0.3 \\; source 0 \\; overlap 1"), (dur, "\\; pd quit")]
        gen.write(f"{d}/x{dur}.pd", shift.shift_patch(gen.Canvas, gen.controls_canvas, test=dict(steps=st)))
        sh = gen.shimmer_loop_test()
        sh["steps"] = [s_ for s_ in sh["steps"] if "quit" not in s_[1]] + [(dur, "\\; pd quit")]
        gen.write(f"{d}/s{dur}.pd", shimmer.shimmer_patch(gen.Canvas, gen.controls_canvas, test=sh))

    def tm(path):
        best = 1e9
        for _ in range(3):
            t0 = time.time()
            subprocess.run([PD, "-nogui", "-batch", "-r", "48000", "-stderr", "-open", path], capture_output=True)
            best = min(best, time.time() - t0)
        return best
    r = {(k, dur): tm(f"{d}/{k}{dur}.pd") for k in "xs" for dur in (3000, 63000)}
    px, ps = (r[k, 63000] - r[k, 3000] for k in "xs")
    print(f"  info per minute of audio: shift {px:.2f} s, 07_shimmer {ps:.2f} s ({px / ps:.2f}x shimmer)")
    check(name, px / ps < 1.0, "below 07_shimmer's CPU")


SCEN = dict(shift=sc_shift, direct=sc_direct, time=sc_time, clock=sc_clock, climb=sc_climb, freeze=sc_freeze,
            barber=sc_barber, runaway=sc_runaway, cpu=sc_cpu)

if __name__ == "__main__":
    names = sys.argv[1:] or list(SCEN)
    for n in names:
        print(f"[{n}]")
        SCEN[n]()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
