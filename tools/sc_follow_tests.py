#!/usr/bin/env python3
"""Offline tests of sc/06_sc_follow.scd: NRT renders in SuperCollider 3.10.4 (sc3-plugins) with a melody as input.

  python tools/sc_follow_tests.py [scenario ...]

Input: a C major scale (C4 .. C5, 0.4 s a note, a sine with two harmonics), looped. After 10 s the key tracker has
settled, and each note's harmony is checked from the wet output (Blend 1): its strongest partial between the
expected note's neighbours.
  third    the click = the diatonic third above (C->E, D->F, E->G, ...)
  octave   Pitch +1 octave of V/oct = 7 more steps (an octave and a third)
  below    Record on = a third below
  chrom    Source on = parallel major thirds (D -> F#)
  freeze   Freeze holds the last note as a drone after the input stops
  arp      Density 0.9 + Reset pulses every 125 ms: one note per pulse, cycling four notes
  level    everything moving: bounded, no NaN
Renders go to firmware/dist/sc_tests/.
"""
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sc_nrt_tests as N   # noqa: E402

SR = 48000
NOTE = 0.4
SCALE = [60, 64, 67, 71, 72, 67, 62, 65, 69, 71, 67, 60]   # clearly C major (C E G B weigh most)
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


def melody(secs, stop=None):
    t = np.arange(int(secs * SR)) / SR
    x = np.zeros_like(t)
    for i in range(int(secs / NOTE)):
        if stop and i * NOTE >= stop:
            break
        f = 440 * 2 ** ((SCALE[i % len(SCALE)] - 69) / 12)
        m = (t >= i * NOTE) & (t < (i + 1) * NOTE)
        tt = t[m] - i * NOTE
        env = np.minimum(1, tt / 0.01) * np.minimum(1, (NOTE - tt) / 0.02)
        x[m] = 0.3 * env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)
                            + 0.15 * np.sin(6 * np.pi * f * tt))
    return x


def inwav(name, x):
    path = "%s/%s.wav" % (N.OUT, name)
    os.makedirs(N.OUT, exist_ok=True)
    N.write_wav(path, [x.astype(np.float32), x.astype(np.float32)])
    return path


def strongest_midi(seg, lo, hi):
    """The strongest partial between midi lo and hi, as a (fractional) midi number."""
    x = seg.mean(axis=1) * np.hanning(len(seg))
    sp = np.abs(np.fft.rfft(x, 1 << 16))
    f = np.fft.rfftfreq(1 << 16, 1 / SR)
    m = (f > 440 * 2 ** ((lo - 69) / 12)) & (f < 440 * 2 ** ((hi - 69) / 12))
    pk = f[m][np.argmax(sp[m])]
    return 69 + 12 * math.log2(pk / 440)


BASE = dict(blend=1, density=0, overlap=0, start=0.5, size=0.1, pitch=0.6, window=0.4, blend_alt=0, speed=0.5,
            density_alt=0.2)


def harmony_check(name, x, expect, t0=10.0, t1=19.6):
    """expect(input midi) -> the harmony midi. Per note: the strongest partial within +-1.5 semitones."""
    good, tot, bad = 0, 0, []
    for i in range(int(t0 / NOTE), int(t1 / NOTE)):
        src = SCALE[i % len(SCALE)]
        want = expect(src)
        seg = N.seg(x, i * NOTE + 0.2, i * NOTE + 0.38)
        got = strongest_midi(seg, want - 1.5, want + 1.5)
        tot += 1
        if abs(got - want) < 0.3:
            good += 1
        else:
            bad.append((src, want, round(got, 2)))
    check(good >= 0.85 * tot, f"{name}: {good}/{tot} notes have their harmony ({bad[:4]})")


def diatonic(src, steps):
    pcs = [0, 2, 4, 5, 7, 9, 11]
    d = pcs.index((src - 60) % 12) + 7 * ((src - 60) // 12) + steps
    return 60 + pcs[d % 7] + 12 * (d // 7)


def sc_third():
    print("[third]")
    x = N.render("06_sc_follow.scd", "follow_third", [], 20, init=BASE, input_wav=inwav("cmaj", melody(20)))
    harmony_check("click = diatonic third above", x, lambda s: diatonic(s, 2))


def sc_octave():
    print("[octave]")
    x = N.render("06_sc_follow.scd", "follow_oct", [], 20, init=dict(BASE, pitch=0.8),
                 input_wav=inwav("cmaj", melody(20)))
    harmony_check("Pitch +1 octave = an octave and a third", x, lambda s: diatonic(s, 9))


def sc_below():
    print("[below]")
    x = N.render("06_sc_follow.scd", "follow_below", [], 20, init=dict(BASE, record=1),
                 input_wav=inwav("cmaj", melody(20)))
    harmony_check("Record on = a third below", x, lambda s: diatonic(s, -2))


def sc_chrom():
    print("[chrom]")
    x = N.render("06_sc_follow.scd", "follow_chrom", [], 20, init=dict(BASE, source=1),
                 input_wav=inwav("cmaj", melody(20)))
    harmony_check("Source on = parallel major thirds", x, lambda s: s + 4)


def sc_freeze():
    print("[freeze]")
    # the input stops at 12 s; its last note (from 11.6 s) is G4; Freeze from 11.75 s
    x = N.render("06_sc_follow.scd", "follow_freeze", [(11.75, dict(freeze=1))], 16, init=BASE,
                 input_wav=inwav("cmaj_stop", melody(16, stop=12.0)))
    a = N.rms(N.seg(x, 11.2, 11.7))
    b = N.rms(N.seg(x, 13.0, 15.5))
    m = strongest_midi(N.seg(x, 13.0, 15.5), 69, 73)
    check(b > 0.5 * a and abs(m - 71) < 0.3, f"Freeze: the harmony (B4, {m:.2f}) holds after the input stops "
                                             f"(rms {a:.3f} -> {b:.3f})")
    y = N.render("06_sc_follow.scd", "follow_nofreeze", [], 16, init=BASE,
                 input_wav=inwav("cmaj_stop", melody(16, stop=12.0)))
    c = N.rms(N.seg(y, 13.0, 15.5))
    check(c < 0.1 * a, f"... and without Freeze it stops (rms {c:.4f})")


def sc_arp():
    print("[arp]")
    ev = [(10.0 + 0.125 * i, dict(t_reset=1)) for i in range(64)]
    x = N.render("06_sc_follow.scd", "follow_arp", ev, 18.5, init=dict(BASE, density=0.9, size=0.05),
                 input_wav=inwav("cmaj", melody(20)))
    env = N.seg(x, 10.0, 18.0).mean(axis=1)
    w = int(0.004 * SR)
    e = np.sqrt(np.convolve(env ** 2, np.ones(w) / w, "same"))
    hop = int(0.125 * SR)
    peaks = [e[i * hop:(i + 1) * hop].max() for i in range(63)]
    lows = [e[i * hop + int(0.1 * SR):(i + 1) * hop].min() for i in range(63)]
    rel = np.array(lows) / np.array(peaks)
    check(np.median(rel) < 0.35, f"one note per pulse (the level dips between pulses: median {np.median(rel):.2f})")
    notes = [round(strongest_midi(N.seg(x, 10.0 + 0.125 * i + 0.01, 10.0 + 0.125 * i + 0.06), 55, 90)) for i in range(32)]
    check(len(set(notes)) >= 3, f"it cycles notes ({notes[:12]})")


def sc_level():
    print("[level]")
    ev = []
    for i in range(30):
        ev.append((2 + i * 0.5, dict(pitch=0.4 + (i * 0.07) % 0.5, start=(i * 0.13) % 1, density=(i * 0.31) % 1,
                                     overlap=(i * 0.17) % 1, window=(i * 0.23) % 1, speed=(i * 0.29) % 1,
                                     blend=(i * 0.11) % 1, source=i % 2, record=(i // 3) % 2, freeze=(i // 7) % 2,
                                     size_alt=(i * 0.19) % 1, blend_alt=0.5, t_reset=1)))
    x = N.render("06_sc_follow.scd", "follow_level", ev, 18, init=BASE, input_wav=inwav("cmaj", melody(20)))
    check(not np.isnan(x).any() and float(np.abs(x).max()) <= 0.96 and N.rms(x[2 * SR:]) > 0.01,
          f"everything moving: bounded, no NaN, not silent (peak {np.abs(x).max():.3f}, rms {N.rms(x[2 * SR:]):.3f})")


SCEN = dict(third=sc_third, octave=sc_octave, below=sc_below, chrom=sc_chrom, freeze=sc_freeze, arp=sc_arp,
            level=sc_level)

if __name__ == "__main__":
    for n in sys.argv[1:] or list(SCEN):
        SCEN[n]()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
