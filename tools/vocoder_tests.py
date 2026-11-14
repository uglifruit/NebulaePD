#!/usr/bin/env python3
"""Offline tests of 10_vocoder (Pd batch runs + WAV/log checks). Run from the repo root on Windows:

  python tools/vocoder_tests.py [scenario ...]        (no arguments = all)

Test input: the modulator (left) is a sine (vc_tsf/vc_tsa), white noise (vc_tna) and a 6.5 kHz noise band
(vc_tha); the external carrier (right) is a sine (vc_tcf/vc_tca). Renders go to firmware/dist/vocoder_sim/.

Scenarios
  bands     a sine modulator at band 3 / 9 / 15 -> the output's energy sits in that band (internal saw carrier)
  shift     Speed fully clockwise / anticlockwise: the band-9 formant moves up / down 6 bands
  freeze    Freeze holds the spectral envelope after the modulator stops; File held = momentary freeze
  gate      modulator noise at -70 dB is gated (silence); at -30 dB it opens
  ext       Source on: a 1 kHz carrier on the right input is what comes out
  pitch     Pitch at the click = C3 harmonics, +1 octave = C4 (unison chord, noise modulator); chord shapes
            (Start) and Reset stepping the chord
  track     Record on: the carrier root follows a 220 Hz voice (sigmund~), rounded to A3
  sib       Overlap: high-passed noise follows the modulator's sibilance
  level     a noise modulator at 0.3 rms comes out at a similar level; everything on and moving: no NaN, bounded
  cpu       per minute of audio against 07_shimmer and 04_glitch
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
import vocoder    # noqa: E402
from chop_tests import read_wav, Log, PD  # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "vocoder_sim").replace("\\", "/")
SR = 48000
FB = vocoder.FB
V0 = ("\\; blend 1 \\; start 0 \\; size 0.5 \\; density 0 \\; overlap 0 \\; window 0.3 \\; speed 0.5 "
      "\\; pitch 0.15 \\; freeze 0 \\; record 0 \\; source 0 \\; filestate 0")      # root 27.5 Hz: a dense saw
FAILS = []


def check(name, ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(f"{name}: {msg}")


def run(name, steps, dur_ms):
    d = f"{OUT}/{name}"
    os.makedirs(d, exist_ok=True)
    test = dict(steps=steps + [(dur_ms, "\\; pd quit")], wav=f"{d}/out.wav")
    gen.write(f"{d}/t.pd", vocoder.vocoder_patch(gen.Canvas, gen.controls_canvas, test=test))
    p = subprocess.run([PD, "-nogui", "-batch", "-r", "48000", "-stderr", "-open", f"{d}/t.pd"],
                       capture_output=True, text=True, timeout=600)
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


def band_energy(x):
    """dB energy per vocoder band (1/3-octave-ish windows around the band centres)."""
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    r = (FB[1] / FB[0]) ** 0.5
    return np.array([10 * np.log10(X[(f >= fb / r) & (f < fb * r)].sum() + 1e-20) for fb in FB])


def peaks(x, n=6, fmin=30, fmax=4000):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = (f > fmin) & (f < fmax)
    X, f = X[m], f[m]
    idx = [i for i in range(1, len(X) - 1) if X[i] > X[i - 1] and X[i] >= X[i + 1]]
    idx.sort(key=lambda i: -X[i])
    return sorted(f[i] for i in idx[:n])


# --- scenarios -------------------------------------------------------------------------------------------------------
def sc_bands():
    name = "bands"
    st = [(10, V0)]
    for i, k in enumerate((3, 9, 15)):
        st += [(1000 + 1500 * i, f"\\; vc_tsf {FB[k]:.2f} \\; vc_tsa 0.3")]
    log, w = run(name, st, 5500)
    no_errors(name, log)
    for i, k in enumerate((3, 9, 15)):
        e = band_energy(seg(w, 1.5 + 1.5 * i, 2.4 + 1.5 * i))
        top = int(np.argmax(e))
        check(name, abs(top - k) <= 1 and e.max() - e[k] < 3 and e[k] - np.median(e) > 20,
              f"sine at band {k} ({FB[k]:.0f} Hz): loudest output band {top}, band {k} "
              f"{e[k] - np.median(e):.0f} dB over the median")


def sc_shift():
    name = "shift"
    st = [(10, V0 + f" \\; vc_tsf {FB[12]:.2f} \\; vc_tsa 0.3"), (2000, "\\; speed 1"), (4000, "\\; speed 0"),
          (6000, "\\; speed 0.8125")]
    log, w = run(name, st, 7500)
    no_errors(name, log)
    for t, want, what in ((1.0, 12, "none"), (3.0, 18, "+6 (Speed CW)"), (5.0, 6, "-6 (Speed CCW)"),
                          (7.0, None, "+3 (Speed half-way right)")):
        e = band_energy(seg(w, t, t + 0.4))
        top = int(np.argmax(e))
        want = 15 if want is None else want
        check(name, abs(top - want) <= 1 and e.max() - e[want] < 3,
              f"shift {what}: loudest band {top} (expected {want}, within 3 dB)")


def sc_freeze():
    name = "freeze"
    # Window 0.9 (a slow envelope, 3 Hz): what is held is then close to the average spectrum before the freeze
    st = [(10, V0 + " \\; vc_tna 0.3 \\; window 0.9"), (1500, "\\; freeze 1"), (1600, "\\; vc_tna 0"),
          (3000, "\\; freeze 0"),
          (4000, "\\; vc_tna 0.3"), (4500, "\\; filestate 1"), (4600, "\\; vc_tna 0"), (5500, "\\; filestate 0")]
    log, w = run(name, st, 6500)
    no_errors(name, log)
    a, b, c_ = rms_db(seg(w, 1.0, 1.4)), rms_db(seg(w, 2.0, 2.9)), rms_db(seg(w, 3.5, 3.9))
    check(name, abs(a - b) < 3 and c_ < a - 40, f"Freeze: held after the input stops ({a:.1f} -> {b:.1f} dB), "
                                                 f"released -> silence ({c_:.1f} dB)")
    ea, eb = band_energy(seg(w, 1.0, 1.4)), band_energy(seg(w, 2.2, 2.6))     # equal lengths
    df = np.abs(ea - eb)[3:]                    # bands 0-2: too few carrier harmonics per window to compare
    check(name, np.median(df) < 3 and df.max() < 9, f"the held spectrum matches (median {np.median(df):.1f}, "
                                                    f"max {df.max():.1f} dB)")
    d, e_ = rms_db(seg(w, 4.8, 5.4)), rms_db(seg(w, 5.9, 6.3))
    check(name, abs(d - a) < 3 and e_ < a - 40, f"File held = momentary freeze ({d:.1f} dB), released ({e_:.1f} dB)")


def sc_gate():
    name = "gate"
    st = [(10, V0 + " \\; vc_tna 0.0003"), (2000, "\\; vc_tna 0.03")]
    log, w = run(name, st, 3500)
    no_errors(name, log)
    a, b = rms_db(seg(w, 1.0, 1.9)), rms_db(seg(w, 2.5, 3.4))
    check(name, a < -100 and b > a + 60, f"gate: -70 dB in -> {a:.1f} dB out, -30 dB in -> {b:.1f} dB out (open)")


def sc_ext():
    name = "ext"
    st = [(10, V0 + " \\; source 1 \\; vc_tca 0.5 \\; vc_tcf 1000 \\; vc_tna 0.3")]
    log, w = run(name, st, 3000)
    no_errors(name, log)
    p = peaks(seg(w, 1.5, 2.5), 1, 30, 10000)
    check(name, p and abs(p[0] - 1000) < 5, f"external carrier: the output is the 1 kHz carrier ({p})")


def harmonic_peaks(x, fmin, fmax, n=8):
    """The n strongest spectral peaks in [fmin, fmax], merging peaks closer than 3 %."""
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = (f > fmin) & (f < fmax)
    X, f = X[m], f[m]
    idx = sorted((i for i in range(1, len(X) - 1) if X[i] > X[i - 1] and X[i] >= X[i + 1]), key=lambda i: -X[i])
    out = []
    for i in idx:
        if all(abs(f[i] / g - 1) > 0.03 for g in out):
            out.append(f[i])
        if len(out) == n:
            break
    return sorted(out)


def has(ps, f, tol=0.015):
    return any(abs(p / f - 1) < tol for p in ps)


def sc_pitch():
    """Noise modulator with a slow envelope (Window 0.9), so the output's lines are the carrier's."""
    name = "pitch"
    st = [(10, V0 + " \\; pitch 0.6 \\; vc_tna 0.3 \\; window 0.9"), (2000, "\\; pitch 0.8"),
          (4000, "\\; pitch 0.6 \\; start 0.45"), (6000, "\\; reset 1"), (6010, "\\; reset 0")]
    log, w = run(name, st, 7500)
    no_errors(name, log)
    p1 = harmonic_peaks(seg(w, 1.0, 1.9), 60, 700, 4)
    check(name, has(p1, 130.81) and all(abs(f / 130.81 - round(f / 130.81)) < 0.03 for f in p1),
          f"Pitch at the click: C3 harmonics ({[round(f, 1) for f in p1]})")
    p2 = harmonic_peaks(seg(w, 3.0, 3.9), 120, 1400, 4)
    check(name, has(p2, 261.63) and not has(p2, 130.81), f"Pitch 0.8 = +1 octave: C4 ({[round(f, 1) for f in p2]})")
    fv = [[round(r[0], 2) for r in log.get(f"fv{v}")] for v in range(3)]
    major = [130.81, 164.81, 196.0]
    minor = [130.81, 155.56, 196.0]
    seen = list(zip(*fv))
    check(name, tuple(major) in seen, f"Start 0.45 = major: voices C3 E3 G3 ({seen[-3:]})")
    check(name, seen and list(seen[-1]) == minor, f"Reset: the next chord = minor: C3 Eb3 G3 ({seen[-1]})")
    p4 = harmonic_peaks(seg(w, 6.5, 7.4), 140, 170, 2)
    check(name, has(p4, 155.56), f"... and it sounds: Eb3 in the output ({[round(f, 1) for f in p4]})")


def sc_track():
    name = "track"
    st = [(10, V0 + " \\; pitch 0.6 \\; vc_tsf 220 \\; vc_tsa 0.3 \\; vc_tna 0.02"), (1500, "\\; record 1"),
          (3000, "\\; pitch 0.8")]
    log, w = run(name, st, 4500)
    no_errors(name, log)
    fv = [r[0] for r in log.get("fv0")]
    check(name, any(abs(f - 220) < 0.5 for f in fv), f"Track: the root follows the voice (220 Hz): {fv[-3:]}")
    check(name, abs(fv[-1] - 440) < 1, f"Track + Pitch 0.8 (+12, rounded semitones): {fv[-1]:.1f} Hz")
    pk = harmonic_peaks(seg(w, 2.0, 2.9), 150, 300, 2)
    check(name, has(pk, 220), f"the output sounds at 220 Hz ({[round(f, 1) for f in pk]})")


def sc_sib():
    name = "sib"
    st = [(10, V0 + " \\; vc_tha 0.3"), (2000, "\\; overlap 1")]
    log, w = run(name, st, 3500)
    no_errors(name, log)

    def hf(x):
        X = np.abs(np.fft.rfft(x)) ** 2
        f = np.fft.rfftfreq(len(x), 1 / SR)
        return 10 * np.log10(X[f > 5000].sum() + 1e-20)
    a, b = hf(seg(w, 1.0, 1.9)), hf(seg(w, 2.5, 3.4))
    check(name, b > a + 6, f"Overlap 1 adds sibilance noise above 5 kHz ({a:.1f} -> {b:.1f} dB)")


def sc_level():
    name = "level"
    st = [(10, V0 + " \\; vc_tna 0.3 \\; pitch 0.6"), (3000, "\\; blend 0")]
    moves = []
    for i in range(40):
        t = 4000 + i * 100
        moves.append((t, f"\\; start {i % 8 / 8:g} \\; size {(i * 0.13) % 1:g} \\; density {(i * 0.07) % 1:g} "
                         f"\\; overlap {(i * 0.11) % 1:g} \\; window {(i * 0.17) % 1:g} \\; speed {(i * 0.23) % 1:g} "
                         f"\\; pitch {0.3 + (i * 0.19) % 0.9:g} \\; blend {(i * 0.29) % 1:g} \\; vc_tsa 0.4 "
                         f"\\; vc_tsf {100 + i * 97}"))
    moves += [(6000, "\\; freeze 1"), (7000, "\\; freeze 0 \\; record 1"), (7500, "\\; source 1 \\; vc_tca 0.8")]
    log, w = run(name, st + moves, 8500)
    no_errors(name, log)
    a = rms_db(seg(w, 1.5, 2.9))
    nin = 20 * math.log10(0.3 / math.sqrt(3))          # noise~ is uniform: rms = amplitude / sqrt 3
    check(name, nin - 6 < a < nin + 3, f"white noise at {nin:.1f} dB rms in -> {a:.1f} dB out (Blend 1)")
    b = rms_db(seg(w, 3.2, 3.9))
    check(name, abs(b - nin) < 1, f"Blend 0 = the dry modulator ({b:.1f} dB)")
    check(name, not np.isnan(w).any() and np.abs(w).max() <= 1.0, f"everything moving: no NaN, bounded (peak "
                                                                   f"{np.abs(w).max():.2f})")


def sc_cpu():
    name = "cpu"
    import glitch
    import shimmer
    d = f"{OUT}/{name}"
    os.makedirs(d, exist_ok=True)
    for dur in (3000, 63000):
        st = [(10, V0 + " \\; vc_tna 0.3 \\; size 0.6 \\; overlap 0.5 \\; speed 0.7"), (dur, "\\; pd quit")]
        gen.write(f"{d}/v{dur}.pd", vocoder.vocoder_patch(gen.Canvas, gen.controls_canvas, test=dict(steps=st)))
        sc = gen.glitch_glitch_test()
        sc["steps"] = [s_ for s_ in sc["steps"] if "quit" not in s_[1]] + [(dur, "\\; pd quit")]
        gen.write(f"{d}/g{dur}.pd", glitch.glitch_patch(gen.Canvas, gen.controls_canvas, test=sc))
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
    r = {(k, dur): tm(f"{d}/{k}{dur}.pd") for k in "vgs" for dur in (3000, 63000)}
    pv, pg, ps = (r[k, 63000] - r[k, 3000] for k in "vgs")
    print(f"  info per minute of audio: vocoder {pv:.2f} s, 07_shimmer {ps:.2f} s, 04_glitch {pg:.2f} s "
          f"({pv / ps:.2f}x shimmer)")
    check(name, pv / ps < 1.5, "at most about 07_shimmer's CPU (< 1.5x)")


SCEN = dict(bands=sc_bands, shift=sc_shift, freeze=sc_freeze, gate=sc_gate, ext=sc_ext, pitch=sc_pitch,
            track=sc_track, sib=sc_sib, level=sc_level, cpu=sc_cpu)

if __name__ == "__main__":
    names = sys.argv[1:] or list(SCEN)
    for n in names:
        print(f"[{n}]")
        SCEN[n]()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
