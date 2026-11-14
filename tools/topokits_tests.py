#!/usr/bin/env python3
"""Offline tests of 11_topokits (Pd batch runs + log/WAV checks). Run from the repo root on Windows:

  python tools/topokits_tests.py

Kit files (written to firmware/dist/topokits_sim/kits/): kit1 = all six voices, each a tone at its own frequency;
kit2 = only a 1 s kick (300 Hz). topo's test clock runs 16ths at 120 BPM from 1.2 s (pattern locked).

Checks: kit select on alt Pitch (0 -> 1 -> 2 -> 0); the router (kit 1: every hit is a sample; kit 2: only the
kick; kit 0: none); the samples sound (their tone frequencies appear only while their kit is on); tune and decay
reach the samples; no NaN / bounded; CPU against 06_topo.
"""
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen        # noqa: E402
import topo       # noqa: E402
from chop_tests import read_wav, write_wav, Log, PD   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "topokits_sim").replace("\\", "/")
SR = 48000
TONES = dict(K=440, S=660, C=880, CH=5000, OH=3500, P=1200)
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


def tone(f, sec, decay=0.05):
    t = np.arange(int(sec * SR)) / SR
    return 0.5 * np.sin(2 * np.pi * f * t) * (np.exp(-t / decay) if decay else 1.0)


def make_kits():
    d = f"{OUT}/kits"
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(f"{d}/{f}")
    from topokits import NAMES
    for v, f in TONES.items():
        write_wav(f"{d}/kit1_{NAMES[v]}.wav", tone(f, 0.15), SR, 2)
    write_wav(f"{d}/kit2_kick.wav", tone(300, 1.0, decay=0), SR, 1)
    write_wav(f"{d}/unrelated.wav", tone(100, 0.2), SR, 1)
    return d


def stream(knob, v0, v1, t):
    return [(t + 5 * i, f"\\; {knob} {v0 + (v1 - v0) * i / 10:g}") for i in range(11)]


def tone_db(x, f):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    return 10 * np.log10(X[(fr > f * 0.97) & (fr < f * 1.03)].sum() + 1e-20)


def seg(w, t0, t1, ch=0):
    return w[int((t0 - 0.3) * SR):int((t1 - 0.3) * SR), ch]


def run(name, steps, dur, kit_dir):
    d = f"{OUT}/{name}"
    os.makedirs(d, exist_ok=True)
    test = dict(steps=steps + [(dur, "\\; pd quit")], wav=f"{d}/out.wav")
    gen.write(f"{d}/t.pd", topo.topo_patch(gen.Canvas, gen.controls_canvas, test=test, kits=True, kit_dir=kit_dir))
    p = subprocess.run([PD, "-nogui", "-batch", "-r", "48000", "-stderr", "-open", f"{d}/t.pd"],
                       capture_output=True, text=True, timeout=600)
    log = p.stdout + p.stderr
    open(f"{d}/log.txt", "w").write(log)
    return Log(log), read_wav(f"{d}/out.wav")[1]


def main():
    kd = make_kits()
    st = ([(10, gen.TP0 + " \\; freeze 1 \\; density 0.6"), (1200, "\\; tp_tclk 1")]
          + stream("pitch_alt", 0.0, 0.03, 3200) + stream("pitch_alt", 0.03, 0.055, 7200)
          + stream("blend_alt", 0.5, 0.2, 11200) + [(13200, "\\; pitch 0.7")]
          + stream("pitch_alt", 0.055, 0.0, 15200))
    log, w = run("main", st, 17200, kd)
    errs = [ln for ln in log.text.splitlines() if "error" in ln.lower() or "couldn't" in ln.lower()]
    check(not errs, f"no Pd errors ({errs[:3]})")
    kits = [(r[0], int(r[1])) for r in log.get("kit")]
    ks = [k for _, k in kits]
    check(ks[:3] == [0, 1, 2] and ks[-1] == 0, f"alt Pitch selects kit 0 -> 1 -> 2 -> (back) 0 ({kits})")

    def count(label, t0, t1):
        return sum(1 for r in log.get(label) if t0 <= r[0] < t1)

    hits = {v: [r[0] for r in log.get(f"hit_{v}")] for v in topo.VOICES}
    smp = {v: [r[0] for r in log.get(f"smp_{v}")] for v in topo.VOICES}
    for t0, t1, kit in ((1200, 3200, 0), (3400, 7200, 1), (7400, 11200, 2), (15400, 17200, 0)):
        nh = {v: sum(1 for t in hits[v] if t0 <= t < t1) for v in topo.VOICES}
        ns = {v: sum(1 for t in smp[v] if t0 <= t < t1) for v in topo.VOICES}
        if kit == 1:
            ok = all(ns[v] == nh[v] for v in topo.VOICES) and sum(nh.values()) > 10
        elif kit == 2:
            ok = ns["K"] == nh["K"] > 0 and all(ns[v] == 0 for v in topo.VOICES if v != "K")
        else:
            ok = sum(ns.values()) == 0
        check(ok, f"kit {kit} ({t0 / 1000:g}-{t1 / 1000:g} s): samples {ns}, hits {nh}")
    a = {v: tone_db(seg(w, 1.3, 3.1), f) for v, f in TONES.items() if f < 4000}
    b = {v: tone_db(seg(w, 3.5, 7.1), f) for v, f in TONES.items() if f < 4000}
    played = [v for v in a if hits[v] and any(3400 <= t < 7200 for t in hits[v])]
    check(all(b[v] > a[v] + 15 for v in played), "kit 1's tones sound only with kit 1: "
          + ", ".join(f"{v} {a[v]:.0f}->{b[v]:.0f} dB" for v in played))
    k2 = tone_db(seg(w, 7.5, 11.1), 300) - tone_db(seg(w, 3.5, 7.1), 300)
    check(k2 > 20, f"kit 2's kick (300 Hz) sounds with kit 2 (+{k2:.0f} dB)")
    durs = [(r[0], r[1], r[2]) for r in log.get("dur_K")]
    d1 = [d for t, d, r in durs if 7400 <= t < 11200]
    d2 = [d for t, d, r in durs if 11400 <= t < 13200]
    check(d1 and abs(d1[-1] - 1000) < 1 and d2 and abs(d2[-1] - 1000 * np.exp(-0.3 * 2 * np.log(4))) < 2,
          f"decay (alt Blend 0.2) shortens the 1 s kick: {d1[-1] if d1 else 0:.0f} -> "
          f"{d2[-1] if d2 else 0:.0f} ms")
    r2 = [r for t, d, r in durs if t >= 13300]
    check(r2 and abs(r2[-1] / 48 - 2 ** 0.5) < 0.01, f"tune (Pitch 0.7 = +6 st) reaches the samples: rate "
                                                    f"{r2[-1] / 48 if r2 else 0:.4f}")
    check(not np.isnan(w).any() and np.abs(w).max() <= 1.0, f"no NaN, bounded (peak {np.abs(w).max():.2f})")
    # CPU per minute against 06_topo (same pattern, kit 1 on)
    d = f"{OUT}/cpu"
    os.makedirs(d, exist_ok=True)
    for dur in (3000, 63000):
        s2 = ([(10, gen.TP0 + " \\; density 0.6"), (1200, "\\; tp_tclk 1")] + stream("pitch_alt", 0, 0.03, 1300)
              + [(dur, "\\; pd quit")])
        gen.write(f"{d}/k{dur}.pd", topo.topo_patch(gen.Canvas, gen.controls_canvas, test=dict(steps=s2), kits=True,
                                                    kit_dir=kd))
        gen.write(f"{d}/t{dur}.pd", topo.topo_patch(gen.Canvas, gen.controls_canvas, test=dict(steps=s2)))

    def tm(path):
        best = 1e9
        for _ in range(3):
            t0 = time.time()
            subprocess.run([PD, "-nogui", "-batch", "-r", "48000", "-stderr", "-open", path], capture_output=True)
            best = min(best, time.time() - t0)
        return best
    r = {(k, dur): tm(f"{d}/{k}{dur}.pd") for k in "kt" for dur in (3000, 63000)}
    pk, pt = r["k", 63000] - r["k", 3000], r["t", 63000] - r["t", 3000]
    print(f"  info per minute of audio: topokits {pk:.2f} s, 06_topo {pt:.2f} s ({pk / pt:.2f}x)")
    check(pk / pt < 1.5, "under 1.5x 06_topo")


if __name__ == "__main__":
    main()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
