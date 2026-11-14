#!/usr/bin/env python3
"""Offline tests of 13_partials (Pd batch runs + WAV checks). Run from the repo root on Windows:

  python tools/partials_tests.py [scenario ...]        (no arguments = all)

Scenarios
  pitch     Density 0 = one sine at C2 (nothing at the 2nd harmonic); Pitch 0.8 = C3
  harm      all 16 partials at n x C2, Window fully CW = equal levels
  stretch   Size 1: partial n at n^1.4 x C2
  masks     Start: odd only, even only (+ half the fundamental), primes
  tilt      Window: partial 8 against 1 at -36 / -18 / 0 dB (n^-2(1-w))
  drift     Overlap 1: Speed past a click = levels move; between the clicks = still; Freeze = still
  deal      Reset: a new mix, gliding over alt Density's time; File: back to even
  twin      Source: every partial gets a twin a few cents up (beating)
  sub       Record: a sine an octave below
  level     the output level stays within 3 dB across shapes; everything moving: bounded, no NaN
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
import partials   # noqa: E402
import shimmer    # noqa: E402
from chop_tests import read_wav, Log, PD  # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "partials_sim").replace("\\", "/")
SR = 48000
C2 = partials.C2
V0 = ("\\; blend 1 \\; start 0 \\; size 0 \\; window 1 \\; density 1 \\; overlap 0 \\; speed 0.5 \\; pitch 0.6 "
      "\\; freeze 0 \\; record 0 \\; source 0 \\; filestate 0")
FAILS = []


def check(name, ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(f"{name}: {msg}")


def run(name, steps, dur_ms):
    d = f"{OUT}/{name}"
    os.makedirs(d, exist_ok=True)
    test = dict(steps=steps + [(dur_ms, "\\; pd quit")], wav=f"{d}/out.wav")
    gen.write(f"{d}/t.pd", partials.partials_patch(gen.Canvas, gen.controls_canvas, test=test))
    p = subprocess.run([PD, "-nogui", "-batch", "-r", "48000", "-stderr", "-open", f"{d}/t.pd"],
                       capture_output=True, text=True, timeout=900)
    log = p.stdout + p.stderr
    open(f"{d}/log.txt", "w").write(log)
    e = [ln for ln in log.splitlines() if "error" in ln.lower() or "couldn't" in ln.lower()
         or "bad arguments" in ln.lower() or "no such" in ln.lower()]
    check(name, not e, f"no Pd errors ({e[:3]})")
    return Log(log), read_wav(f"{d}/out.wav")[1]


def seg(w, t0, t1, ch=0):
    return w[int((t0 - 0.3) * SR):int((t1 - 0.3) * SR), ch]


def mono(w, t0, t1):
    return 0.5 * (seg(w, t0, t1, 0) + seg(w, t0, t1, 1))


def lv(x, f0, bw=3):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)), 1 << 18))
    f = np.fft.rfftfreq(1 << 18, 1 / SR)
    return 20 * math.log10(X[(f > f0 - bw) & (f < f0 + bw)].max() + 1e-12)


def rms_db(x):
    return 10 * math.log10(np.mean(x ** 2) + 1e-20)


def levels(x, freqs):
    return np.array([lv(x, f) for f in freqs])


def sc_pitch():
    name = "pitch"
    log, w = run(name, [(10, V0 + " \\; density 0"), (3000, "\\; pitch 0.8")], 5500)
    a, b = mono(w, 1.0, 2.9), mono(w, 3.5, 5.4)
    X = np.abs(np.fft.rfft(a * np.hanning(len(a)), 1 << 18))
    f = np.fft.rfftfreq(1 << 18, 1 / SR)
    pk = f[np.argmax(X)]
    Y = np.abs(np.fft.rfft(b * np.hanning(len(b)), 1 << 18))
    pk2 = f[np.argmax(Y)]
    check(name, abs(pk / C2 - 1) < 0.003 and abs(pk2 / (2 * C2) - 1) < 0.003, f"one sine: {pk:.2f} Hz, then {pk2:.2f}")
    check(name, lv(a, C2) - lv(a, 2 * C2) > 60, f"nothing at the 2nd harmonic ({lv(a, C2) - lv(a, 2 * C2):.0f} dB down)")


def sc_harm():
    name = "harm"
    log, w = run(name, [(10, V0)], 3500)
    x = mono(w, 1.0, 3.4)
    L = levels(x, [n * C2 for n in range(1, 17)])
    check(name, L.max() - L.min() < 1.5, f"16 partials at n x C2, Window CW: levels within {L.max() - L.min():.2f} dB")


def sc_stretch():
    name = "stretch"
    log, w = run(name, [(10, V0 + " \\; size 1")], 3500)
    x = mono(w, 1.0, 3.4)
    ok, det = True, []
    for n in (2, 3, 5):                                    # (stretched partials can land near other n x C2)
        f = C2 * n ** 1.4
        d = lv(x, f) - lv(x, n * C2)
        det.append(f"{n}: {d:.0f} dB")
        ok &= d > 30
    check(name, ok, "Size 1: partials at n^1.4 x C2, not at n x C2 (" + ", ".join(det) + ")")


def sc_masks():
    name = "masks"
    log, w = run(name, [(10, V0 + " \\; start 0.3333"), (3000, "\\; start 0.6667"), (6000, "\\; start 1")], 8500)
    x = mono(w, 1.0, 2.9)
    L = levels(x, [n * C2 for n in range(1, 17)])
    odd_ok = min(L[0::2]) - max(L[1::2]) > 40
    check(name, odd_ok, f"odd only: even partials {min(L[0::2]) - max(L[1::2]):.0f} dB under the odd ones")
    x = mono(w, 4.0, 5.9)
    L = levels(x, [n * C2 for n in range(1, 17)])
    ev = min(L[1::2]) - max(L[2::2])                       # even (2,4..) over odd n >= 3
    check(name, ev > 40 and abs(L[0] - L[1] + 6) < 1.5, f"even only: odd partials {ev:.0f} dB under; the "
                                                         f"fundamental at half ({L[0] - L[1]:.1f} dB)")
    x = mono(w, 6.5, 8.4)
    L = levels(x, [n * C2 for n in range(1, 17)])
    on = [L[n - 1] for n in sorted(partials.PRIMES)]
    off = [L[n - 1] for n in range(1, 17) if n not in partials.PRIMES]
    check(name, min(on) - max(off) > 40, f"primes: 4, 6, 8, 9 ... {min(on) - max(off):.0f} dB under 1, 2, 3, 5, 7 ...")


def sc_tilt():
    name = "tilt"
    log, w = run(name, [(10, V0 + " \\; window 0"), (3000, "\\; window 0.5"), (6000, "\\; window 1")], 8500)
    res = []
    for t0, want in ((1.0, -36.1), (4.0, -18.1), (6.5, 0)):
        x = mono(w, t0, t0 + 1.9)
        res.append(lv(x, 8 * C2) - lv(x, C2))
    check(name, all(abs(r - wv) < 1 for r, wv in zip(res, (-36.1, -18.1, 0))),
          "Window 0 / 0.5 / 1: partial 8 at %.1f / %.1f / %.1f dB (want -36 / -18 / 0)" % tuple(res))


def spread_over_time(w, t0, t1, n=8):
    rows = []
    for k in range(int((t1 - t0) / 0.5)):
        x = mono(w, t0 + 0.5 * k, t0 + 0.5 * k + 0.5)
        rows.append(levels(x, [m * C2 for m in range(1, n + 1)]))
    r = np.array(rows)
    return float(np.median(r.max(axis=0) - r.min(axis=0)))


def sc_drift():
    name = "drift"
    st = [(10, V0 + " \\; overlap 1 \\; speed 1"), (5000, "\\; speed 0.55"), (9000, "\\; speed 0"),
          (13000, "\\; freeze 1")]
    log, w = run(name, st, 17000)
    a, b, c_, d = (spread_over_time(w, t, t + 3.5) for t in (1.3, 5.3, 9.3, 13.3))
    check(name, a > 6 and c_ > 6, f"Speed past a click: levels move ({a:.1f} dB CW, {c_:.1f} dB CCW)")
    check(name, b < 0.5, f"between the clicks: still ({b:.2f} dB)")
    check(name, d < 0.5, f"Freeze: still ({d:.2f} dB)")


def sc_deal():
    name = "deal"
    st = [(10, V0), (1500, "\\; reset 1"), (1520, "\\; reset 0"), (5500, "\\; filestate 1"),
          (5520, "\\; filestate 0")]
    log, w = run(name, st, 9000)
    fr = [n * C2 for n in range(1, 17)]
    A = levels(mono(w, 0.6, 1.4), fr)                       # even (the load deal is flat)
    M = levels(mono(w, 2.3, 2.7), fr)                       # half-way through the 2 s glide
    B = levels(mono(w, 4.0, 5.4), fr)                       # dealt
    C = levels(mono(w, 8.0, 8.9), fr)                       # flattened again
    db = B - B.max()
    check(name, (A.max() - A.min()) < 1.5 and (db.min() < -6), f"Reset: a new mix (spread {A.max() - A.min():.1f} "
                                                                f"-> {B.max() - B.min():.1f} dB)")
    mid = np.median(np.abs((M - M.max()) - (B - B.max())))
    check(name, mid > 1, f"it glides (half-way, {mid:.1f} dB from the new mix)")
    check(name, (C.max() - C.min()) < 1.5, f"File: even again ({C.max() - C.min():.1f} dB)")


def sc_twin():
    name = "twin"
    st = [(10, V0 + " \\; window 1"), (3000, "\\; source 1")]
    log, w = run(name, st, 9000)
    f16 = 16 * C2
    tw = f16 * 2 ** (6 / 1200)
    a, b = mono(w, 1.0, 2.9), mono(w, 4.5, 8.9)
    da, db = lv(a, tw, 0.8) - lv(a, f16, 0.8), lv(b, tw, 0.8) - lv(b, f16, 0.8)
    check(name, da < -20 and abs(db) < 3, f"Source: partial 16's twin at +6 cents ({tw:.1f} Hz) {da:.0f} dB -> "
                                          f"{db:+.1f} dB against the partial")


def sc_sub():
    name = "sub"
    log, w = run(name, [(10, V0), (2000, "\\; record 1")], 5000)
    a, b = mono(w, 0.8, 1.9), mono(w, 3.0, 4.9)
    check(name, lv(b, C2 / 2) - lv(a, C2 / 2) > 30, f"Record: an octave below appears "
                                                    f"(+{lv(b, C2 / 2) - lv(a, C2 / 2):.0f} dB at {C2 / 2:.1f} Hz)")


def sc_level():
    name = "level"
    st = [(10, V0 + " \\; density 0"), (2000, "\\; density 1 \\; window 1"), (4000, "\\; window 0"),
          (6000, "\\; start 1 \\; window 0.5"), (8000, "\\; start 0.3333 \\; size 0.6")]
    log, w = run(name, st, 10000)
    r = [rms_db(mono(w, t + 0.5, t + 1.9)) for t in (0.3, 2, 4, 6, 8)]
    check(name, max(r) - min(r) < 3, "level across shapes: " + " ".join(f"{v:.1f}" for v in r) + " dB")
    st = [(10, V0 + " \\; overlap 1 \\; speed 1 \\; source 1 \\; record 1")]
    for i in range(30):
        st.append((500 + 500 * i, f"\\; start {(i * 0.37) % 1:.3f} \\; size {(i * 0.29) % 1:.3f} "
                                  f"\\; window {(i * 0.53) % 1:.3f} \\; density {(i * 0.41) % 1:.3f} "
                                  f"\\; pitch {-0.3 + (i * 0.23) % 1.6:.3f} \\; reset {i % 2}"))
    log, w = run("level2", st, 16000)
    check(name, np.isfinite(w).all() and np.abs(w).max() <= 1.0, f"everything moving: bounded, no NaN "
                                                                 f"(peak {np.abs(w).max():.3f})")


def sc_cpu():
    name = "cpu"
    d = f"{OUT}/cpu"
    os.makedirs(d, exist_ok=True)
    for dur in (3000, 63000):
        st = [(10, V0 + " \\; overlap 1 \\; speed 1 \\; source 1 \\; record 1"), (dur, "\\; pd quit")]
        gen.write(f"{d}/x{dur}.pd", partials.partials_patch(gen.Canvas, gen.controls_canvas, test=dict(steps=st)))
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
    print(f"  info per minute of audio (drifting, twins on): partials {px:.2f} s, 07_shimmer {ps:.2f} s "
          f"({px / ps:.2f}x shimmer)")
    check(name, px / ps < 1.0, "below 07_shimmer's CPU")


SCEN = dict(pitch=sc_pitch, harm=sc_harm, stretch=sc_stretch, masks=sc_masks, tilt=sc_tilt, drift=sc_drift,
            deal=sc_deal, twin=sc_twin, sub=sc_sub, level=sc_level, cpu=sc_cpu)

if __name__ == "__main__":
    names = sys.argv[1:] or list(SCEN)
    for n in names:
        print(f"[{n}]")
        SCEN[n]()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
