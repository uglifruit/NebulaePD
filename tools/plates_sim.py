#!/usr/bin/env python3
"""Offline tests of instr/plates.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/plates_sim.py [scenario ...]
  python tools/plates_sim.py m609

  hold      Density = Hold: silent at 0, every voice droning at 1, on C2 (sine, unison)
  touch     Record, Reset, Freeze (while held) and Source (latched) bring in pairs 1-4, fifths apart (Start 0.58)
  swell     alt Density: the swell in is quick or slow; out takes longer
  sharp     Size: more overtones (sine -> square-ish)
  detune    alt Size: the pair's two voices apart (beating)
  fm        Window: neighbour FM spreads energy off the harmonics
  lfo       Speed: still between the clicks, shaking past them; File: OR brighter than AND on average
  delay     Overlap: echoes after a touch ends; none at 0
  drive     Blend: harmonics from distortion
  input     alt Blend: the input comes through
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles, drones at C2
Renders go to firmware/dist/plates_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "plates_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "plates.instr")
SR = 48000
C2 = 65.406
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0\ngkloopsize = 0\ngkdensity = 0\ngkwindow = 0\n"
        "gkoverlap = 0\ngkblend = 0\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\ngkreset = 0\n")
ALTS = "start_alt=0.4 size_alt=0 density_alt=0.2 window_alt=0.3 overlap_alt=0 blend_alt=0 pitch_alt=0"
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    import wave
    t = np.arange(70 * SR) / SR
    for name, sig in (("in_silence.wav", np.zeros_like(t)), ("in_sine.wav", 0.3 * np.sin(2 * np.pi * 440 * t))):
        with wave.open(os.path.join(OUT, name), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.stack([sig, sig], 1) * 32767).astype("<i2").tobytes())
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def run(name, secs, auto, alts=ALTS, wav="in_silence.wav"):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=alts, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, wav), name)


def near_peak(x, t0, t1, f0, tol=0.03):
    s = seg(x, t0, t1)
    n = 1 << 19
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)), n))
    f = np.fft.rfftfreq(n, 1 / SR)
    m = np.flatnonzero((f > f0 * (1 - tol)) & (f < f0 * (1 + tol)))
    i = m[np.argmax(sp[m])]
    a, b, c = np.log(sp[i - 1:i + 2] + 1e-20)
    return float(f[i] + 0.5 * (a - c) / (a - 2 * b + c) * (f[1] - f[0])), float(db(sp[i]))


def centroid(x, t0, t1, n=8192):
    f, p = psd(x, t0, t1, n=n)
    m = (f > 30) & (f < 12000)
    return float(np.sum(f[m] * p[m]) / np.sum(p[m]))


def sc_hold():
    print("hold")
    (x, _) = run("hold", 6, steps("gkdensity", (0, 0), (3, 1)))
    a, b = rms(x, 1.5, 2.9), rms(x, 4.5, 5.9)
    f = near_peak(x, 4.5, 5.9, C2)[0]
    check("Hold 0: silent; Hold 1: droning", a < 1e-4 and b > 0.05, "rms %.1e -> %.3f" % (a, b))
    check("on C2 (within 0.3 %)", abs(f / C2 - 1) < 0.003, "%.2f Hz" % f)


def sc_touch():
    print("touch")
    auto = ("gkloopstart = 0.5833\n" +
            "gkrecord = (kt > 1.5 && kt < 3 ? 1 : 0)\ngkreset = (kt > 4 && kt < 5.5 ? 1 : 0)\n"
            "gkfreeze = (kt > 6.5 && kt < 8 ? 1 : 0)\ngksource = (kt > 9 ? 1 : 0)\n")
    (x, _) = run("touch", 11, auto)
    want = [C2 * 2 ** (p * 7 / 12) for p in range(4)]
    got = []
    for a, w in zip((2.3, 4.8, 7.3, 10.0), want):
        got.append(near_peak(x, a, a + 0.7, w)[0])
    others = [near_peak(x, 2.3, 3.0, w, tol=0.01)[1] for w in want[1:]]
    own = near_peak(x, 2.3, 3.0, want[0], tol=0.01)[1]
    check("each touch brings its pair in: C2, G2, D3, A3 (within 0.3 %)",
          all(abs(g / w - 1) < 0.003 for g, w in zip(got, want)),
          " ".join("%.2f" % g for g in got) + "  (want " + " ".join("%.2f" % w for w in want) + ")")
    check("only that pair (others > 30 dB under while Record is held)", own - max(others) > 30,
          "%+.1f dB" % (own - max(others)))
    q = rms(x, 3.9, 4.0)
    check("released pairs fade out (pair 1 down > 25 dB 1 s after release)",
          db(q) - db(rms(x, 2.5, 2.9)) < -25, "%+.1f dB" % (db(q) - db(rms(x, 2.5, 2.9))))


def t_to(x, t0, t1, frac):
    s = seg(x, t0, t1)
    w = int(0.01 * SR)
    r = np.array([np.sqrt(np.mean(s[i:i + w] ** 2)) for i in range(0, len(s) - w, w)])
    top = r.max()
    return float(np.argmax(r >= frac * top) * 0.01)


def sc_swell():
    print("swell")
    auto = "gkrecord = (kt > 1.5 ? 1 : 0)\n"
    (x, _) = run("swell0", 5, auto, alts=ALTS.replace("density_alt=0.2", "density_alt=0"))
    (y, _) = run("swell1", 9, auto, alts=ALTS.replace("density_alt=0.2", "density_alt=0.8"))
    a, b = t_to(x, 1.5, 4.9, 0.7), t_to(y, 1.5, 8.9, 0.7)
    check("alt Density: swell to 70 % quick -> slow (< 0.15 s, then > 1 s)", a < 0.15 and b > 1,
          "%.2f s -> %.2f s" % (a, b))


def harm(x, t0, t1, f0, n):
    return near_peak(x, t0, t1, f0 * n, tol=0.01)[1]


def sc_sharp():
    print("sharp")
    # (Hold 0.6: at full Hold eight unison voices push the output's soft clip, which adds a 3rd harmonic itself)
    (x, _) = run("sharp", 7, "gkdensity = 0.6\n" + steps("gkloopsize", (0, 0), (4, 1)))
    a = harm(x, 2, 3.9, C2, 3) - harm(x, 2, 3.9, C2, 1)
    b = harm(x, 5, 6.9, C2, 3) - harm(x, 5, 6.9, C2, 1)
    check("Size: the 3rd harmonic up > 20 dB (sine -> sharp)", b - a > 20, "%+.1f -> %+.1f dB" % (a, b))


def sc_detune():
    print("detune")
    (x, _) = run("det0", 5, "gkdensity = 1\n")
    (y, _) = run("det1", 5, "gkdensity = 1\n", alts=ALTS.replace("size_alt=0", "size_alt=1"))
    lo = near_peak(y, 1.5, 4.9, C2 * 2 ** (-20 / 1200), tol=0.004)[0]
    hi = near_peak(y, 1.5, 4.9, C2 * 2 ** (20 / 1200), tol=0.004)[0]
    one = near_peak(x, 1.5, 4.9, C2, tol=0.01)[0]
    check("alt Size: two voices 40 cents apart (within 3 cents), one at 0",
          abs(1200 * np.log2(hi / lo) - 40) < 3 and abs(one / C2 - 1) < 0.003,
          "%.1f cents apart; at 0: %.2f Hz" % (1200 * np.log2(hi / lo), one))


def hi_ratio(x, t0, t1, lo=800):
    f, p = psd(x, t0, t1, n=16384)
    m = (f > 30) & (f < 12000)
    return float(10 * np.log10(np.sum(p[m & (f > lo)]) / np.sum(p[m])))


def sc_fm():
    print("fm")
    (x, _) = run("fm", 7, "gkdensity = 1\ngkloopstart = 0.58\n" + steps("gkwindow", (0, 0), (4, 0.7)))
    a, b = hi_ratio(x, 2, 3.9), hi_ratio(x, 5, 6.9)
    check("Window: FM spreads the sines' energy upward (above 800 Hz: > 15 dB more)", b - a > 15,
          "%+.1f -> %+.1f dB" % (a, b))


def sc_lfo():
    print("lfo")
    # the LFO gates the FM, so the energy the FM throws above 600 Hz pulses with it: watch that band's envelope
    # (pairs in exact octaves: in tempered fifths their harmonics beat slowly and the band pulses by itself)
    auto = ("gkdensity = 1\ngkwindow = 0.3\ngkloopstart = 1\n" + steps("gkspeed", (0, 0.5), (4, 0.9)) +
            pulses(8.0, 8.05, name="gkfilestate"))
    (x, _) = run("lfo", 12, auto)
    s = x.mean(axis=1)
    sp = np.fft.rfft(s)
    sp[np.fft.rfftfreq(len(s), 1 / SR) < 600] = 0
    h = np.fft.irfft(sp, len(s))
    w = int(0.01 * SR)

    def env(t0, t1):
        return np.array([np.sqrt(np.mean(h[i:i + w] ** 2)) for i in range(int(t0 * SR), int(t1 * SR) - w, w)])
    e1, e2, e3 = env(2, 3.9), env(5, 7.9), env(9, 11.9)
    v1, v2 = np.std(e1) / np.mean(e1), np.std(e2) / np.mean(e2)
    check("Speed: steady between the clicks, pulsing past them (the FM band's envelope varies x3, > 0.3)",
          v2 > 3 * v1 and v2 > 0.3, "%.2f -> %.2f" % (v1, v2))
    check("File: A OR B keeps the FM on longer than A AND B (band level > 3 dB higher)",
          db(np.mean(e2)) - db(np.mean(e3)) > 3, "%+.1f dB" % (db(np.mean(e2)) - db(np.mean(e3))))


def sc_delay():
    print("delay")
    auto = "gkrecord = (kt > 1.5 && kt < 1.9 ? 1 : 0)\n"
    (x, _) = run("delay0", 5, auto, alts=ALTS.replace("density_alt=0.2", "density_alt=0"))
    (y, _) = run("delay1", 5, auto + "gkoverlap = 0.8\n", alts=ALTS.replace("density_alt=0.2", "density_alt=0"))
    a, b = db(rms(x, 3.0, 4.0)), db(rms(y, 3.0, 4.0))
    check("Overlap: echoes ring on after the touch (> 30 dB over none)", b - a > 30, "%.1f -> %.1f dB" % (a, b))


def sc_drive():
    print("drive")
    (x, _) = run("drive", 7, "gkdensity = 0.6\n" + steps("gkblend", (0, 0), (4, 1)))
    a = harm(x, 2, 3.9, C2, 3) - harm(x, 2, 3.9, C2, 1)
    b = harm(x, 5, 6.9, C2, 3) - harm(x, 5, 6.9, C2, 1)
    check("Blend: distortion lifts the 3rd harmonic (> 15 dB)", b - a > 15, "%+.1f -> %+.1f dB" % (a, b))


def sc_input():
    print("input")
    (x, _) = run("input", 4, "", alts=ALTS.replace("blend_alt=0", "blend_alt=1"), wav="in_sine.wav")
    (y, _) = run("input0", 4, "", wav="in_sine.wav")
    a, b = near_peak(y, 1.5, 3.9, 440)[1], near_peak(x, 1.5, 3.9, 440)[1]
    check("alt Blend: the input comes through (> 40 dB more than at 0)", b - a > 40, "%+.1f dB" % (b - a))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkblend = frac(kt * 0.04)\n"
            "gkrecord = (frac(kt * 0.7) > 0.5 ? 1 : 0)\ngkreset = (frac(kt * 0.45) > 0.6 ? 1 : 0)\n"
            "gkfreeze = (frac(kt * 0.3) > 0.4 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.5 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.4) < 0.03 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\ngkdensity_alt = frac(kt * 0.04)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkoverlap_alt = frac(kt * 0.03)\ngkblend_alt = frac(kt * 0.02)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_sine.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_sine.wav"), "looper")
    print("  CPU for 62 s: plates %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 4, BASE + "gkdensity = 1\n", sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "4", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f = near_peak(x, 2.0, 3.9, C2)[0]
    check("6.09: compiles, drones at C2 (within 0.3 %)", ok and abs(f / C2 - 1) < 0.003 and not np.isnan(x).any(),
          "%.2f Hz, rms %.3f" % (f, rms(x, 2.0, 3.9)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["hold", "touch", "swell", "sharp", "detune", "fm", "lfo", "delay", "drive", "input",
                            "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
