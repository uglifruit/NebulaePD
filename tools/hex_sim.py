#!/usr/bin/env python3
"""Offline tests of instr/hex.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/hex_sim.py [scenario ...]
  python tools/hex_sim.py m609

  tonic     the tones alone (Blend 0): C3 at the click, C4 at +0.2
  tones     Start: a subharmonic at f/2, then f/3, then folding (brighter)
  activate  Freeze (momentary) pours the tones into the experiment; nothing pours in without it (constant 0)
  time      Time (Size): a short burst echoes at the set time
  decay     Decay: a handful of repeats -> rings for ever
  filter    Filter (Window) darkens the experiment; Absorb (Overlap) thins its lows
  agitate   Speed: steady between the clicks, agitated (the filter moving) past them
  interfere Record (momentary): the experiment bends the tonic (sidebands)
  source    Source: your input goes into the experiment
  hold      File: the experiment keeps ringing and takes nothing new
  reverb    alt Blend: a stereo reverb (left and right decorrelate)
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles, the tonic at C3
Renders go to firmware/dist/hex_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "hex_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "hex.instr")
SR = 48000
C3 = 130.813
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0\ngkloopsize = 0.55\ngkdensity = 0.5\ngkwindow = 0.7\n"
        "gkoverlap = 0.1\ngkblend = 1\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\n")
ALTS = "start_alt=0 size_alt=0 density_alt=0 window_alt=0.6 overlap_alt=0 blend_alt=0 pitch_alt=0"
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
    m = (f > 30) & (f < 14000)
    return float(np.sum(f[m] * p[m]) / np.sum(p[m]))


def hi(x, t0, t1, n=8192, lo=1000):
    f, p = psd(x, t0, t1, n=n)
    m = (f > 30) & (f < 14000)
    return float(10 * np.log10(np.sum(p[m & (f > lo)]) / np.sum(p[m]) + 1e-12))


def sc_tonic():
    print("tonic")
    (x, _) = run("tonic", 7, "gkblend = 0\n" + steps("gkpitch", (0, 0.6), (4, 0.8)))
    a, b = near_peak(x, 1.5, 3.9, C3)[0], near_peak(x, 4.5, 6.9, 2 * C3)[0]
    check("the tones alone: C3 at the click, C4 at +0.2 (within 0.3 %)",
          abs(a / C3 - 1) < 0.003 and abs(b / (2 * C3) - 1) < 0.003, "%.2f, %.2f Hz" % (a, b))
    check("level: rms > 0.05, peak under 1", rms(x, 1.5, 3.9) > 0.05 and float(np.abs(x).max()) < 1,
          "rms %.3f, peak %.3f" % (rms(x, 1.5, 3.9), float(np.abs(x).max())))


def sc_tones():
    print("tones")
    auto = "gkblend = 0\n" + steps("gkloopstart", (0, 0), (3, 0.24), (5, 0.5), (7, 0.95))
    (x, _) = run("tones", 9, auto)
    s2 = [near_peak(x, a, a + 1.4, C3 / 2, tol=0.01)[1] - near_peak(x, a, a + 1.4, C3, tol=0.01)[1]
          for a in (1.5, 3.5)]
    s3 = [near_peak(x, a, a + 1.4, C3 / 3, tol=0.01)[1] - near_peak(x, a, a + 1.4, C3, tol=0.01)[1]
          for a in (3.5, 5.5)]
    c0, c3 = centroid(x, 1.5, 2.9), centroid(x, 7.5, 8.9)
    check("Start: a subharmonic at f/2 comes in (> 20 dB up)", s2[1] - s2[0] > 20, "%+.1f -> %+.1f dB" % tuple(s2))
    check("then f/3 (> 20 dB up)", s3[1] - s3[0] > 20, "%+.1f -> %+.1f dB" % tuple(s3))
    check("then folding: brighter (centroid x1.5)", c3 > 1.5 * c0, "%.0f -> %.0f Hz" % (c0, c3))


def sc_activate():
    print("activate")
    auto = "gkfreeze = (kt > 3 && kt < 5 ? 1 : 0)\n"
    (x, _) = run("activate", 6, auto)
    a, b = rms(x, 1.5, 2.9), rms(x, 3.5, 4.9)
    check("Freeze held: the tones pour into the experiment (> 30 dB up from nothing)", db(b) - db(a) > 30,
          "%.1f -> %.1f dB" % (db(a), db(b)))


def sc_time():
    print("time")
    # Size 0.3: Time = 1.5 x 0.001^0.3 = 0.189 s; a 40 ms touch, low decay: echoes 0.189 s apart
    auto = "gkloopsize = 0.3\ngkdensity = 0.55\ngkfreeze = (kt > 2 && kt < 2.04 ? 1 : 0)\n"
    (x, _) = run("time", 4.5, auto)
    s = np.abs(seg(x, 2.0, 4.0))
    w = int(0.004 * SR)
    e = np.convolve(s, np.ones(w) / w, "same")
    e = e - e.mean()
    ac = np.correlate(e, e, "full")[len(e) - 1:]
    lo, hi = int(0.1 * SR), int(0.4 * SR)
    lag = (lo + int(np.argmax(ac[lo:hi]))) / SR
    want = 1.5 * 0.001 ** 0.3
    check("Time: echoes at the set time (0.189 s, within 5 %)", abs(lag / want - 1) < 0.05, "%.3f s" % lag)


def sc_decay():
    print("decay")
    auto = "gkloopsize = 0.45\ngkfreeze = (kt > 2 && kt < 2.3 ? 1 : 0)\n"
    (x, _) = run("decay0", 7, auto + "gkdensity = 0.3\n")
    (y, _) = run("decay1", 7, auto + "gkdensity = 1\n")
    a, b = db(rms(x, 5.5, 6.9)), db(rms(y, 5.5, 6.9))
    ref = db(rms(y, 2.3, 2.8))
    check("Decay: a handful of repeats (gone 3 s later) -> for ever (still > -12 dB of its start)",
          a < ref - 40 and b > ref - 12, "low %.1f, full %.1f dB (start %.1f)" % (a, b, ref))


def sc_filter():
    print("filter")
    auto = "gkfreeze = 1\n"
    (x, _) = run("filt", 7, auto + "gkloopstart = 0.6\n" + steps("gkwindow", (0, 0.9), (4, 0.3)))
    a, b = hi(x, 2, 3.9), hi(x, 5, 6.9)
    check("Filter: darker anticlockwise (the share above 1 kHz down > 15 dB)", a - b > 15,
          "%+.1f -> %+.1f dB" % (a, b))
    (y, _) = run("absorb", 7, auto + "gkloopstart = 0.3\n" + steps("gkoverlap", (0, 0), (4, 0.9)))
    f, p = psd(y, 2, 3.9)
    l0 = band(f, p, 40, 200) / band(f, p, 40, 8000)
    f, p = psd(y, 5, 6.9)
    l1 = band(f, p, 40, 200) / band(f, p, 40, 8000)
    check("Absorb: the lows thin out (40-200 Hz share down > 10 dB)", 10 * np.log10(l0 / l1) > 10,
          "%+.1f dB" % (10 * np.log10(l1 / l0)))


def sc_agitate():
    print("agitate")
    # (Speed 0.75: about one sweep every 1.5 s; much faster and it averages out inside a 0.1 s window)
    auto = "gkfreeze = 1\ngkwindow = 0.5\ngkloopstart = 0.6\n" + steps("gkspeed", (0, 0.5), (5, 0.75))
    (x, _) = run("agitate", 10, auto, alts=ALTS.replace("overlap_alt=0", "overlap_alt=0.8"))
    c1 = [hi(x, a, a + 0.1, n=2048) for a in np.arange(2, 4.8, 0.1)]
    c2 = [hi(x, a, a + 0.1, n=2048) for a in np.arange(6, 9.8, 0.1)]
    s1, s2 = np.std(c1), np.std(c2)
    check("Speed: steady between the clicks, agitated past them (the share above 1 kHz: sd x3, > 1.5 dB)",
          s2 > 3 * s1 and s2 > 1.5, "%.2f -> %.2f dB" % (s1, s2))


def sc_interfere():
    print("interfere")
    auto = "gkblend = 0.5\ngkfreeze = 1\ngkdensity = 0.7\ngkrecord = (kt > 4.5 ? 1 : 0)\n"
    (x, _) = run("interfere", 8, auto)

    def spread(t0, t1):
        f, p = psd(x, t0, t1, n=16384)
        m = (f > 40) & (f < 4000)
        k = np.abs(f / C3 - np.round(f / C3)) < 0.02
        return 10 * np.log10(np.sum(p[m & ~k]) / np.sum(p[m & k]))
    a, b = spread(2.5, 4.4), spread(5.5, 7.9)
    check("Record held: the experiment bends the tonic (energy between its harmonics > 8 dB up)", b - a > 8,
          "%+.1f -> %+.1f dB" % (a, b))


def sc_source():
    print("source")
    (x, _) = run("source", 7, "gksource = (kt > 4 ? 1 : 0)\n", wav="in_sine.wav")
    a, b = near_peak(x, 2, 3.9, 440)[1], near_peak(x, 5, 6.9, 440)[1]
    check("Source: the input into the experiment (440 Hz > 30 dB up)", b - a > 30, "%+.1f dB" % (b - a))


def sc_hold():
    print("hold")
    auto = ("gkdensity = 0.4\ngkfreeze = (kt > 2 && kt < 3 ? 1 : 0)\n" + pulses(2.9, name="gkfilestate") +
            "gksource = (kt > 4 ? 1 : 0)\n")
    (x, _) = run("hold", 8, auto, wav="in_sine.wav")
    (y, _) = run("hold0", 8, auto.replace(pulses(2.9, name="gkfilestate"), ""), wav="in_sine.wav")
    a, b = db(rms(x, 2.5, 2.9)), db(rms(x, 6.5, 7.9))
    i440 = near_peak(x, 6, 7.9, 440)[1] - near_peak(y, 6, 7.9, 440)[1]
    check("File: the experiment keeps ringing (> -12 dB of its level 4 s on, at a low Decay)", b > a - 12,
          "%.1f -> %.1f dB" % (a, b))
    check("and takes nothing new (the input switched on later: 440 Hz > 30 dB under the same run unheld)",
          i440 < -30, "%+.1f dB" % i440)


def sc_reverb():
    print("reverb")
    auto = "gkfreeze = 1\n"
    (x, _) = run("rev0", 5, auto)
    (y, _) = run("rev1", 5, auto, alts=ALTS.replace("blend_alt=0", "blend_alt=1"))

    def corr(z):
        return float(np.corrcoef(seg(z, 2, 4.9, 0), seg(z, 2, 4.9, 1))[0, 1])
    a, b = corr(x), corr(y)
    check("alt Blend: a stereo reverb (L/R correlation 1 -> < 0.9)", a > 0.99 and b < 0.9, "%.3f -> %.3f" % (a, b))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkblend = frac(kt * 0.04)\n"
            "gkrecord = (frac(kt * 0.7) > 0.6 ? 1 : 0)\ngkfreeze = (frac(kt * 0.45) > 0.4 ? 1 : 0)\n"
            "gksource = (frac(kt / 11) > 0.5 ? 1 : 0)\ngkreset = (frac(kt * 0.5) < 0.02 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.1) < 0.02 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\ngkdensity_alt = frac(kt * 0.04)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkoverlap_alt = frac(kt * 0.03)\ngkblend_alt = frac(kt * 0.02)\n"
            "gkpitch_alt = frac(kt * 0.035)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_sine.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_sine.wav"), "looper")
    print("  CPU for 62 s: hex %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper (with the reverb)", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 4, BASE + "gkblend = 0\n", sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "4", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f = near_peak(x, 1.5, 3.9, C3)[0]
    check("6.09: compiles, the tonic at C3 (within 0.3 %)", ok and abs(f / C3 - 1) < 0.003 and not np.isnan(x).any(),
          "%.2f Hz, rms %.3f" % (f, rms(x, 1.5, 3.9)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["tonic", "tones", "activate", "time", "decay", "filter", "agitate", "interfere",
                            "source", "hold", "reverb", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
