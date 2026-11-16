#!/usr/bin/env python3
"""Offline tests of instr/veil.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/veil_sim.py [scenario ...]
  python tools/veil_sim.py m609

  pitch      the overtone stack on its fundamental: C2 at the click, C3 an octave up
  algos      File steps through six algorithms: each sounds, and each sounds different
  overtones  Start: the overtone stack climbs from the fundamental to high harmonics
  formant    Size: the formant moves up (swarm)
  spread     Density: one sharp line -> spread voices (overtone stack)
  crossmod   Window: FM index up (FM pair)
  vowel      Start on the choir: "a" (F1 high) -> "i" (F1 low, F2 high)
  motion     Speed: still between the clicks, drifting past them; Freeze holds it
  reset      Reset: a new setting, glided to (not a jump)
  source     Source: the input through the chain; the oscillators gone
  space      Overlap: a reverb tail after the input stops
  shimmer    Record: octave-up energy in the tail
  sweep      every control at its extremes for 60 s across all algorithms: bounded, no NaN; CPU vs the looper
  m609       Csound 6.09.1: compiles, sounds at C2
Renders go to firmware/dist/veil_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "veil_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "veil.instr")
SR = 48000
C2 = 65.406
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0.35\ngkloopsize = 0.45\ngkdensity = 0.35\ngkwindow = 0.15\n"
        "gkoverlap = 0\ngkblend = 1\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\n")
ALTS = "start_alt=0.5 size_alt=0.5 density_alt=0.5 window_alt=0.6 overlap_alt=0.4 blend_alt=0.5 pitch_alt=0"
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    import wave
    t = np.arange(70 * SR) / SR
    burst = 0.3 * np.sin(2 * np.pi * 440 * t) * ((t > 1.2) & (t < 3.0))
    for name, sig in (("in_silence.wav", np.zeros_like(t)), ("in_sine.wav", 0.3 * np.sin(2 * np.pi * 440 * t)),
                      ("in_burst.wav", burst)):
        with wave.open(os.path.join(OUT, name), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.stack([sig, sig], 1) * 32767).astype("<i2").tobytes())
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def presses(n, t0=1.2, gap=0.12):
    """n presses of File from t0 (algorithm n + 1)."""
    if n == 0:
        return ""
    return "gkfilestate = (" + " || ".join("(kt > %g && kt < %g)" % (t0 + gap * k, t0 + gap * k + 0.04)
                                           for k in range(n)) + " ? 1 : 0)\n"


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
    m = (f > 30) & (f < 14000)
    return float(np.sum(f[m] * p[m]) / np.sum(p[m]))


def sc_pitch():
    print("pitch")
    auto = presses(2) + "gkloopstart = 0\ngkdensity = 0\ngkwindow = 0\n" + steps("gkpitch", (0, 0.6), (4.5, 0.8))
    (x, _) = run("pitch", 7.5, auto)
    a = near_peak(x, 2.5, 4.4, C2)[0]
    b = near_peak(x, 5.5, 7.4, C2 * 2)[0]
    check("the overtone stack's fundamental: C2 at the click, C3 at +0.2 (within 0.3 %)",
          abs(a / C2 - 1) < 0.003 and abs(b / (2 * C2) - 1) < 0.003, "%.2f, %.2f Hz" % (a, b))


def sc_algos():
    print("algos")
    t0s = [1.5 + 2.5 * k for k in range(6)]
    auto = "gkfilestate = (" + " || ".join("(kt > %g && kt < %g)" % (t + 2.5, t + 2.54) for t in t0s[:-1]) + " ? 1 : 0)\n"
    (x, _) = run("algos", 17, auto)
    lv, sp = [], []
    for t in t0s:
        a = t + 0.9
        lv.append(rms(x, a, a + 1.5))
        f, p = psd(x, a, a + 1.5)
        m = (f > 30) & (f < 8000)
        q = np.log10(p[m] + 1e-12)
        sp.append(q - q.mean())
    d = min(np.sqrt(np.mean((sp[i] - sp[j]) ** 2)) for i in range(6) for j in range(i + 1, 6))
    check("all six sound (rms > 0.03)", min(lv) > 0.03, " ".join("%.3f" % v for v in lv))
    check("and differ (the closest pair's spectra > 0.3 decades apart, rms)", d > 0.3, "%.2f" % d)


def sc_overtones():
    print("overtones")
    auto = presses(2) + "gkdensity = 0\ngkwindow = 0\n" + steps("gkloopstart", (0, 0), (4.5, 1))
    (x, _) = run("overtones", 7.5, auto)
    a, b = centroid(x, 2.5, 4.4), centroid(x, 5.5, 7.4)
    check("Start: the stack climbs (centroid x3)", b > 3 * a, "%.0f -> %.0f Hz" % (a, b))


def sc_formant():
    print("formant")
    (x, _) = run("formant", 7.5, "gkdensity = 0\n" + steps("gkloopsize", (0, 0), (4, 1)))
    a, b = centroid(x, 2, 3.9), centroid(x, 5, 7.4)
    check("Size: the formant up (swarm centroid x1.5)", b > 1.5 * a, "%.0f -> %.0f Hz" % (a, b))


def sharpness(x, t0, t1, f0):
    f, p = psd(x, t0, t1, n=1 << 16)
    near = band(f, p, f0 - 0.6, f0 + 0.6)
    wide = band(f, p, f0 * 0.97, f0 * 1.03)
    return float(10 * np.log10(near / wide))


def sc_spread():
    print("spread")
    auto = presses(2) + "gkloopstart = 0\ngkwindow = 0\n" + steps("gkdensity", (0, 0), (4.5, 1))
    (x, _) = run("spread", 8, auto)
    a, b = sharpness(x, 2.5, 4.4, C2), sharpness(x, 5.6, 7.9, C2)
    check("Density: one sharp line -> spread voices (energy at the exact note falls > 3 dB against nearby)",
          a - b > 3, "%+.1f -> %+.1f dB" % (a, b))


def hi(x, t0, t1, lo=1000):
    f, p = psd(x, t0, t1)
    m = (f > 30) & (f < 14000)
    return float(10 * np.log10(np.sum(p[m & (f > lo)]) / np.sum(p[m])))


def sc_crossmod():
    print("crossmod")
    auto = presses(3) + "gkloopstart = 0.3\ngkloopsize = 1\n" + steps("gkwindow", (0, 0), (4.5, 1))
    (x, _) = run("crossmod", 7.5, auto)
    a, b = hi(x, 2.5, 4.4), hi(x, 5.5, 7.4)
    check("Window: the FM index up (energy over 1 kHz > 8 dB more)", b - a > 8, "%+.1f -> %+.1f dB" % (a, b))


def sc_vowel():
    print("vowel")
    auto = presses(1) + "gkloopsize = 0.5\ngkdensity = 0\ngkwindow = 0\n" + steps("gkloopstart", (0, 0), (4.5, 0.5))
    (x, _) = run("vowel", 7.5, auto)
    f, p = psd(x, 2.5, 4.4)
    a1, a2 = band(f, p, 700, 900), band(f, p, 2100, 2500)
    f, p = psd(x, 5.5, 7.4)
    i1, i2 = band(f, p, 700, 900), band(f, p, 2100, 2500)
    d = 10 * np.log10(a1 / a2) - 10 * np.log10(i1 / i2)
    check('Start on the choir: "a" -> "i" (800 Hz against 2.3 kHz swings > 15 dB)', d > 15, "%+.1f dB" % d)


def sc_motion():
    print("motion")
    # (Density 0: with the voices spread, the swarm beats by itself, which is movement too)
    # Freeze is checked where it acts: the four values the knobs see (logged at 14 s and 17.5 s, both frozen;
    # the sound itself may still beat, because the drift can leave the voices spread)
    log = os.path.join(OUT, "motion_log.txt")
    if os.path.exists(log):
        os.remove(log)
    auto = ("gkdensity = 0\n" + steps("gkspeed", (0, 0.5), (5, 0.95)) + "gkfreeze = (kt > 13 ? 1 : 0)\n" +
            "if (kt > 14 && kt < 14.001) || (kt > 17.5 && kt < 17.501) then\n"
            '    fprintks "motion_log.txt", "%f %f %f %f\\n", gkT, gkF, gkS, gkX\nendif\n')
    (x, _) = run("motion", 18, auto)
    st = [np.std(np.log2([centroid(x, a, a + 0.25, n=4096) for a in np.arange(t0, t0 + 3.5, 0.25)]))
          for t0 in (1.3, 9)]
    check("between the clicks: still (centroid sd < 0.04 octave)", st[0] < 0.04, "%.3f" % st[0])
    check("past the click: drifting (> 0.1 octave)", st[1] > 0.1, "%.3f" % st[1])
    rows = [list(map(float, ln.split())) for ln in open(log) if ln.strip()]
    moved = max(abs(a - b) for a, b in zip(rows[0], rows[-1]))
    check("Freeze: overtones, formant, spread and cross-mod held (change < 0.001 over 3.5 s)",
          len(rows) >= 2 and moved < 0.001, "%d log rows, largest change %.5f" % (len(rows), moved))


def sc_reset():
    print("reset")
    auto = "gkreset = (kt > 4 && kt < 4.02 ? 1 : 0)\n"
    (x, _) = run("reset", 9, auto, alts=ALTS.replace("density_alt=0.5", "density_alt=1"))
    a = centroid(x, 2, 3.9)
    m = centroid(x, 4.05, 4.3, n=4096)
    b = centroid(x, 7, 8.9)
    ch = abs(np.log2(b / a))
    part = abs(np.log2(m / a)) / max(ch, 1e-9)
    check("Reset: a new setting (centroid moves > 0.15 octave), glided (the first 0.25 s < 60 % of the way)",
          ch > 0.15 and part < 0.6, "%.0f -> %.0f Hz (%.2f octave), %.0f %% after 0.25 s" % (a, b, ch, 100 * part))


def sc_source():
    print("source")
    auto = "gksource = (kt > 4.5 ? 1 : 0)\ngkloopsize = 0.5\ngkwindow = 0\ngkloopstart = 0.1\n"
    (x, _) = run("source", 8, auto, wav="in_sine.wav")
    a440, ac2 = near_peak(x, 2.5, 4.4, 440)[1], near_peak(x, 2.5, 4.4, C2, tol=0.02)[1]
    b440, bc2 = near_peak(x, 6, 7.9, 440)[1], near_peak(x, 6, 7.9, C2, tol=0.02)[1]
    check("Source: the input through the chain (440 Hz up > 30 dB), the oscillators gone (C2 down > 30 dB)",
          b440 - a440 > 30 and ac2 - bc2 > 30, "440 %+.1f dB, C2 %+.1f dB" % (b440 - a440, bc2 - ac2))


def sc_spacelevel():
    """The owner (2026-11-16): Space cranked sounded distorted. It drove the output limiter (18 % of samples squashed
    on the louder algorithms). Space full and its longest size, on every algorithm: under 2 % squashed by > 1 dB."""
    print("spacelevel")
    alts = ALTS.replace("window_alt=0.6", "window_alt=1")
    worst = []
    for alg in range(6):
        au = "gkoverlap = 1\n" + (pulses(*[1.2 + 0.3 * i for i in range(alg)], name="gkfilestate") if alg else "")
        (x, _) = run("splev%d" % alg, 9, au, alts=alts)
        pre = np.arctanh(np.clip(seg(x, 5, 9), -0.999999, 0.999999))    # (the output limiter is tanh: undo it)
        worst.append(100 * float(np.mean(np.abs(pre) > 0.5)))
    check("Space full at its longest, every algorithm: the output limiter barely works (< 2 % squashed > 1 dB)",
          max(worst) < 2, " ".join("%.1f" % w for w in worst) + " %")


def sc_space():
    print("space")
    auto = "gksource = 1\ngkwindow = 0\n"
    (x, _) = run("space0", 6, auto, wav="in_burst.wav")
    (y, _) = run("space1", 6, auto + "gkoverlap = 1\n", wav="in_burst.wav")
    a, b = db(rms(x, 3.5, 4.0)), db(rms(y, 3.5, 4.0))
    check("Overlap: a tail after the input stops (> 30 dB over none, 0.5-1 s later)", b - a > 30,
          "%.1f -> %.1f dB" % (a, b))


def sc_shimmer():
    print("shimmer")
    auto = "gksource = 1\ngkwindow = 0\ngkloopstart = 0\ngkoverlap = 0.8\n"
    (x, _) = run("shim0", 7, auto, wav="in_burst.wav")
    (y, _) = run("shim1", 7, auto + "gkrecord = 1\n", wav="in_burst.wav")

    def up(z):
        f, p = psd(z, 3.5, 5.5)
        return 10 * np.log10((band(f, p, 860, 900) + band(f, p, 1740, 1780)) / band(f, p, 420, 460))
    a, b = up(x), up(y)
    check("Record: octave-up energy in the tail (880 + 1760 Hz against 440: > 10 dB more)", b - a > 10,
          "%+.1f -> %+.1f dB" % (a, b))
    # the owner's report (2026-11-16): shimmer on with the drone playing crackled, then went silent (the loop ran
    # away to a full-scale DC). Everything at its most: it must stay alive and below the ceiling
    auto = "gkoverlap = 1\ngkrecord = (kt > 2 ? 1 : 0)\n"
    (z, _) = run("shim_max", 30, auto, alts=ALTS.replace("window_alt=0.6", "window_alt=1").replace(
        "overlap_alt=0.4", "overlap_alt=1"))
    s = seg(z, 20, 30)
    pk, mv = float(np.max(np.abs(s))), float(np.std(np.diff(s)))
    check("Record at its most, with the drone, for 30 s: no runaway (peak < 0.98, still moving, no NaN)",
          pk < 0.98 and mv > 1e-3 and not np.isnan(z).any(), "peak %.3f, movement %.4f" % (pk, mv))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkrecord = (frac(kt / 15) > 0.5 ? 1 : 0)\ngksource = (frac(kt / 13) > 0.8 ? 1 : 0)\n"
            "gkfreeze = (frac(kt / 7) > 0.7 ? 1 : 0)\ngkreset = (frac(kt * 0.5) < 0.02 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.25) < 0.02 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\ngkdensity_alt = frac(kt * 0.04)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkoverlap_alt = frac(kt * 0.03)\ngkblend_alt = frac(kt * 0.02)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_sine.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes, every algorithm)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_sine.wav"), "looper")
    print("  CPU for 62 s: veil %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 6, BASE + presses(2) + "gkloopstart = 0\ngkdensity = 0\ngkwindow = 0\n",
                     sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "6", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f = near_peak(x, 3, 5.9, C2)[0]
    check("6.09: compiles, the overtone stack at C2 (within 0.3 %)",
          ok and abs(f / C2 - 1) < 0.003 and not np.isnan(x).any(), "%.2f Hz, rms %.3f" % (f, rms(x, 3, 5.9)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["pitch", "algos", "overtones", "formant", "spread", "crossmod", "vowel", "motion",
                            "reset", "source", "space", "spacelevel", "shimmer", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
