#!/usr/bin/env python3
"""Offline tests of instr/quartet.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/quartet_sim.py [scenario ...]
  python tools/quartet_sim.py m609

  drone     Source latches voice 4: C2 at the click (Start 0), level
  touch     Record / Reset / Freeze play voices 1-3 while held, tuned Start x 12 semitones apart
  envelope  alt Density: quick or slow swells
  chromatic alt Start past noon rounds the tuning to semitones
  wave      Size: sine -> saw (harmonics up)
  programs  File: each of the eleven programs changes the sound; sub-oscillators add f/2, chord adds notes
  filter    Window: darker anticlockwise
  delay     Overlap past noon: the delay runs on after the touch ends; at 0 it stops
  bite      Blend: harmonics from the bite
  lfo       Speed: steady between the clicks, the cutoff moving past them
  input     your input comes through (after the delay)
  reverb    alt Blend: a stereo reverb
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles, voice 4 at C2
Renders go to firmware/dist/quartet_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "quartet_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "quartet.instr")
SR = 48000
C2 = 65.406
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0\ngkloopsize = 0\ngkdensity = 0\ngkwindow = 1\n"
        "gkoverlap = 0\ngkblend = 0\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\ngkreset = 0\n")
ALTS = "start_alt=0 size_alt=0 density_alt=0.1 window_alt=0.6 overlap_alt=0.4 blend_alt=0 pitch_alt=0"
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


def hi(x, t0, t1, lo=1000, n=8192):
    f, p = psd(x, t0, t1, n=n)
    m = (f > 30) & (f < 14000)
    return float(10 * np.log10(np.sum(p[m & (f > lo)]) / np.sum(p[m]) + 1e-12))


def sc_drone():
    print("drone")
    (x, _) = run("drone", 4, "gksource = 1\n")
    f = near_peak(x, 1.5, 3.9, C2)[0]
    check("Source: voice 4 drones at C2 (within 0.3 %)", abs(f / C2 - 1) < 0.003, "%.2f Hz" % f)
    check("level: rms > 0.05, peak under 1", rms(x, 1.5, 3.9) > 0.05 and float(np.abs(x).max()) < 1,
          "rms %.3f, peak %.3f" % (rms(x, 1.5, 3.9), float(np.abs(x).max())))


def sc_touch():
    print("touch")
    auto = ("gkloopstart = 0.5833\ngkrecord = (kt > 1.5 && kt < 3 ? 1 : 0)\ngkreset = (kt > 4 && kt < 5.5 ? 1 : 0)\n"
            "gkfreeze = (kt > 6.5 && kt < 8 ? 1 : 0)\n")
    (x, _) = run("touch", 9, auto)
    want = [C2 * 2 ** (v * 7 / 12) for v in range(3)]
    got = [near_peak(x, a, a + 0.9, w)[0] for a, w in zip((2.0, 4.5, 7.0), want)]
    quiet = rms(x, 3.6, 3.95)
    check("Record, Reset, Freeze play voices 1-3: C2, G2, D3 at Start 0.58 (within 0.3 %)",
          all(abs(g / w - 1) < 0.003 for g, w in zip(got, want)),
          " ".join("%.2f" % g for g in got) + "  (want " + " ".join("%.2f" % w for w in want) + ")")
    check("silent between touches (> 40 dB down)", db(quiet) < db(rms(x, 2.0, 2.9)) - 40,
          "%.1f dB" % (db(quiet) - db(rms(x, 2.0, 2.9))))


def t_to(x, t0, t1, frac):
    s = seg(x, t0, t1)
    w = int(0.01 * SR)
    r = np.array([np.sqrt(np.mean(s[i:i + w] ** 2)) for i in range(0, len(s) - w, w)])
    return float(np.argmax(r >= frac * r.max()) * 0.01)


def sc_envelope():
    print("envelope")
    auto = "gkrecord = (kt > 1.5 ? 1 : 0)\n"
    (x, _) = run("env0", 5, auto, alts=ALTS.replace("density_alt=0.1", "density_alt=0"))
    (y, _) = run("env1", 8, auto, alts=ALTS.replace("density_alt=0.1", "density_alt=0.7"))
    a, b = t_to(x, 1.5, 4.9, 0.7), t_to(y, 1.5, 7.9, 0.7)
    check("alt Density: swell to 70 % quick -> slow (< 0.05 s, then > 1 s)", a < 0.05 and b > 1, "%.2f -> %.2f s" % (a, b))


def sc_chromatic():
    print("chromatic")
    auto = "gkloopstart = 0.4\ngkreset = 1\n"
    (x, _) = run("chrom0", 4, auto)
    (y, _) = run("chrom1", 4, auto, alts=ALTS.replace("start_alt=0", "start_alt=0.8"))
    a = near_peak(x, 1.5, 3.9, C2 * 2 ** (4.8 / 12), tol=0.02)[0]
    b = near_peak(y, 1.5, 3.9, C2 * 2 ** (5 / 12), tol=0.02)[0]
    check("Start 0.4: voice 2 4.8 semitones up (microtonal); alt Start past noon: exactly 5 (within 0.2 %)",
          abs(a / (C2 * 2 ** 0.4) - 1) < 0.002 and abs(b / (C2 * 2 ** (5 / 12)) - 1) < 0.002,
          "%.2f, %.2f Hz" % (a, b))


def sc_wave():
    print("wave")
    (x, _) = run("wave", 7, "gksource = 1\n" + steps("gkloopsize", (0, 0), (4, 0.3)))
    a = near_peak(x, 1.5, 3.9, 3 * C2, tol=0.01)[1] - near_peak(x, 1.5, 3.9, C2, tol=0.01)[1]
    b = near_peak(x, 4.5, 6.9, 3 * C2, tol=0.01)[1] - near_peak(x, 4.5, 6.9, C2, tol=0.01)[1]
    check("Size: sine -> saw (3rd harmonic up > 15 dB; the mix is saturated, as on the original, so the sine has some)", b - a > 15, "%+.1f -> %+.1f dB" % (a, b))


def sc_programs():
    print("programs")
    # one second per program: File pressed at 2.0, 3.0 ... 11.0 (program 0 from the start), MOD 0.7, a saw
    auto = ("gksource = 1\ngkdensity = 0.7\ngkloopsize = 0.3\n" +
            pulses(*[2.0 + k for k in range(10)], name="gkfilestate"))
    (x, _) = run("programs", 13, auto)
    specs = []
    for k in range(11):
        f, p = psd(x, 1.3 + k + 0.2, 1.3 + k + 0.9, n=8192)
        m = (f > 20) & (f < 10000)
        q = np.log10(p[m] + 1e-14)
        specs.append(q - q.mean())
    dist = [float(np.sqrt(np.mean((specs[k] - specs[k + 1]) ** 2))) for k in range(10)]
    check("File: each program changes the sound (each step's spectrum > 0.15 decades apart)", min(dist) > 0.15,
          " ".join("%.2f" % d for d in dist))
    sub = near_peak(x, 2.5, 3.2, C2 / 2, tol=0.01)[1] - near_peak(x, 1.5, 2.2, C2 / 2, tol=0.01)[1]
    check("sub-oscillators: an octave down appears (> 12 dB)", sub > 12, "%+.1f dB" % sub)


def sc_filter():
    print("filter")
    (x, _) = run("filt", 7, "gksource = 1\ngkloopsize = 0.3\n" + steps("gkwindow", (0, 1), (4, 0.4)))
    a, b = hi(x, 1.5, 3.9, lo=500), hi(x, 4.5, 6.9, lo=500)
    check("Window: darker anticlockwise (the share above 500 Hz down > 15 dB)", a - b > 15, "%+.1f -> %+.1f dB" % (a, b))


def sc_delay():
    print("delay")
    auto = "gkrecord = (kt > 1.5 && kt < 1.8 ? 1 : 0)\ngkloopsize = 0.3\n"
    alts = ALTS.replace("size_alt=0", "size_alt=0.5")
    (x, _) = run("dly0", 6, auto, alts=alts)
    (y, _) = run("dly1", 6, auto + "gkoverlap = 0.7\n", alts=alts)
    a, b = db(rms(x, 4.5, 5.9)), db(rms(y, 4.5, 5.9))
    check("Overlap past noon: the delay runs on after the touch (> 40 dB over none)", b - a > 40, "%.1f -> %.1f dB" % (a, b))


def sc_bite():
    print("bite")
    (x, _) = run("bite", 7, "gksource = 1\n" + steps("gkblend", (0, 0), (4, 0.8)))
    a = near_peak(x, 1.5, 3.9, 3 * C2, tol=0.01)[1] - near_peak(x, 1.5, 3.9, C2, tol=0.01)[1]
    b = near_peak(x, 4.5, 6.9, 3 * C2, tol=0.01)[1] - near_peak(x, 4.5, 6.9, C2, tol=0.01)[1]
    check("Blend: the bite adds harmonics (3rd > 15 dB up, from the saturated mix)", b - a > 15, "%+.1f -> %+.1f dB" % (a, b))


def sc_lfo():
    print("lfo")
    auto = "gksource = 1\ngkloopsize = 0.3\ngkwindow = 0.55\n" + steps("gkspeed", (0, 0.5), (5, 0.75))
    (x, _) = run("lfo", 10, auto)
    c1 = [hi(x, a, a + 0.1, n=2048, lo=500) for a in np.arange(2, 4.8, 0.1)]
    c2 = [hi(x, a, a + 0.1, n=2048, lo=500) for a in np.arange(6, 9.8, 0.1)]
    s1, s2 = np.std(c1), np.std(c2)
    check("Speed: steady between the clicks, the cutoff moving past them (sd x3, > 1.5 dB)", s2 > 3 * s1 and s2 > 1.5,
          "%.2f -> %.2f dB" % (s1, s2))


def sc_input():
    print("input")
    (x, _) = run("input", 4, "", wav="in_sine.wav")
    a = near_peak(x, 1.5, 3.9, 440)[1]
    (y, _) = run("input0", 4, "")
    b = near_peak(y, 1.5, 3.9, 440)[1]
    check("your input comes through (440 Hz > 40 dB over without)", a - b > 40, "%+.1f dB" % (a - b))


def sc_reverb():
    print("reverb")
    (x, _) = run("rev0", 5, "gksource = 1\n")
    (y, _) = run("rev1", 5, "gksource = 1\n", alts=ALTS.replace("blend_alt=0", "blend_alt=1"))

    def corr(z):
        return float(np.corrcoef(seg(z, 2, 4.9, 0), seg(z, 2, 4.9, 1))[0, 1])
    a, b = corr(x), corr(y)
    check("alt Blend: a stereo reverb (L/R correlation 1 -> < 0.95)", a > 0.99 and b < 0.95, "%.3f -> %.3f" % (a, b))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkblend = frac(kt * 0.04)\n"
            "gkrecord = (frac(kt * 0.7) > 0.4 ? 1 : 0)\ngkreset = (frac(kt * 0.45) > 0.5 ? 1 : 0)\n"
            "gkfreeze = (frac(kt * 0.3) > 0.4 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.3 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.5) < 0.02 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\ngkdensity_alt = frac(kt * 0.04)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkoverlap_alt = frac(kt * 0.03)\ngkblend_alt = frac(kt * 0.02)\n"
            "gkpitch_alt = frac(kt * 0.035)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_sine.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes, every program)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    # the heaviest case: all four voices on, unison (three oscillators each)
    (_, cpuw) = run("worst", 62, "gkrecord = 1\ngkreset = 1\ngkfreeze = 1\ngksource = 1\ngkdensity = 0.7\n"
                    "gkoverlap = 0.6\ngkblend = 0.5\n", alts=ALTS.replace("blend_alt=0", "blend_alt=0.5"))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_sine.wav"), "looper")
    print("  CPU for 62 s: quartet %.1f s (all four voices, unison: %.1f s), factory looper %.1f s (%.2fx, %.2fx)"
          % (cpu, cpuw, cpul, cpu / cpul, cpuw / cpul))
    check("CPU within 1.2x the factory looper, worst case included (with the reverb)", max(cpu, cpuw) < 1.2 * cpul,
          "%.2fx, worst %.2fx" % (cpu / cpul, cpuw / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 4, BASE + "gksource = 1\n", sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "4", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f = near_peak(x, 1.5, 3.9, C2)[0]
    check("6.09: compiles, voice 4 at C2 (within 0.3 %)", ok and abs(f / C2 - 1) < 0.003 and not np.isnan(x).any(),
          "%.2f Hz, rms %.3f" % (f, rms(x, 1.5, 3.9)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["drone", "touch", "envelope", "chromatic", "wave", "programs", "filter", "delay", "bite",
                            "lfo", "input", "reverb", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
