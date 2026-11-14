#!/usr/bin/env python3
"""Offline tests of instr/scan.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609, from
Windows Python).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/scan_sim.py [scenario ...]
  python tools/scan_sim.py m609

  strike   Reset strikes: sound appears, pitched at C3 (click), then dies away; Pitch 0.8 = C4
  decay    Window anticlockwise rings longer than clockwise
  timbre   the waveform moves after a strike (spectral centroid changes over time)
  bow      Record (latched) sustains the string for seconds
  input    Source: the audio input drives the string; off = silent
  freeze   Freeze holds the waveform: level steady while the string would have decayed
  sweep    every knob at its extremes with strikes, bowing and input for 60 s: bounded, no NaN, no blow-up;
           CPU against the factory granular looper
  m609     Csound 6.09.1: compiles, a strike sounds at C3
Renders go to firmware/dist/scan_sim/.
"""
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "scan_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "scan.instr")
SR = 48000
BASE = ("gkspeed = 0.5\ngkloopstart = 0.3\ngkloopsize = 0.4\ngkdensity = 0.5\ngkwindow = 0.4\ngkoverlap = 0.3\n"
        "gkblend = 1\ngkpitch = 0.6\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\n")
ALTS = "start_alt=0.5 size_alt=0.5 density_alt=0.3 window_alt=0.5 overlap_alt=0.5 blend_alt=0.0 pitch_alt=0.5"
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def stereo(path, l, r):
    data = (np.clip(np.stack([l, r], axis=1), -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    n = 70 * SR
    stereo(os.path.join(OUT, "silence.wav"), np.zeros(n), np.zeros(n))
    rng = np.random.default_rng(2)
    t = np.arange(n) / SR
    nz = 0.3 * rng.standard_normal(n) * (np.sin(2 * np.pi * 0.25 * t) > 0)
    stereo(os.path.join(OUT, "noise.wav"), nz, nz)
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def strike_at(*ts):
    return "gkreset = (" + " || ".join("(kt > %g && kt < %g)" % (t, t + 0.01) for t in ts) + " ? 1 : 0)\n"


def run(name, secs, auto, live="silence.wav"):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=ALTS, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, live), name)


def rms(x, t0, t1):
    s = x[int(t0 * SR):int(t1 * SR), 0]
    return float(np.sqrt(np.mean(s ** 2)))


def fundamental(x, t0, t1):
    s = x[int(t0 * SR):int(t1 * SR), 0] * np.hanning(int((t1 - t0) * SR))
    sp = np.abs(np.fft.rfft(s, 1 << 17))
    f = np.fft.rfftfreq(1 << 17, 1 / SR)
    m = (f > 60) & (f < 2000)
    # the lowest strong partial (> 30 % of the strongest)
    pk = sp[m].max()
    idx = np.nonzero(m)[0]
    for i in idx:
        if sp[i] > 0.3 * pk and sp[i] >= sp[i - 1] and sp[i] >= sp[i + 1]:
            return f[i]
    return 0.0


def centroid(x, t0, t1):
    s = x[int(t0 * SR):int(t1 * SR), 0]
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s))))
    f = np.fft.rfftfreq(len(s), 1 / SR)
    return float((sp * f).sum() / (sp.sum() + 1e-12))


def sc_strike():
    print("strike")
    (x, _) = run("strike", 9, strike_at(2.0, 6.0) + "gkpitch = (kt < 5 ? 0.6 : 0.8)\n")
    a0, a1, a2 = rms(x, 1.5, 1.95), rms(x, 2.05, 2.5), rms(x, 4.5, 5.0)
    print("  levels: before %.4f, after %.4f, later %.4f" % (a0, a1, a2))
    check("a strike sounds", a1 > 0.05 and a1 > 20 * a0, "%.3f (before %.4f)" % (a1, a0))
    check("... and dies away", a2 < 0.5 * a1, "%.3f -> %.3f" % (a1, a2))
    f1, f2 = fundamental(x, 2.1, 2.6), fundamental(x, 6.1, 6.6)
    # the strike's two waves run round the ring in opposite directions: each partial is split a few Hz either side
    # (scanned synthesis' natural chorus), so allow 5 %
    check("pitched at C3 (Pitch click), C4 at Pitch 0.8 (within 5 %)",
          abs(f1 / 130.81 - 1) < 0.05 and abs(f2 / 261.63 - 1) < 0.05,
          "%.1f Hz, %.1f Hz" % (f1, f2))
    check("peak in range", float(np.abs(x).max()) < 1.0, "%.3f" % float(np.abs(x).max()))


def t_decay(x, t0):
    """Seconds after t0 until the level falls 20 dB under its peak (50 ms windows)."""
    s = x[int(t0 * SR):, 0]
    w = int(0.05 * SR)
    r = np.array([np.sqrt(np.mean(s[i:i + w] ** 2)) for i in range(0, len(s) - w, w)])
    pk = r.max()
    j = int(np.argmax(r))
    below = np.nonzero(r[j:] < pk * 0.1)[0]
    return (j + (below[0] if len(below) else len(r))) * 0.05


def sc_decay():
    print("decay")
    (x0, _) = run("decay_long", 12, strike_at(1.5) + "gkwindow = 0.1\n")
    (x1, _) = run("decay_short", 12, strike_at(1.5) + "gkwindow = 0.9\n")
    d0, d1 = t_decay(x0, 1.5), t_decay(x1, 1.5)
    check("Window CCW rings longer than CW (-20 dB times)", d0 > 2 * d1, "%.2f s vs %.2f s" % (d0, d1))


def sc_timbre():
    print("timbre")
    (x, _) = run("timbre", 6, strike_at(1.5) + "gkwindow = 0.2\n")
    cs = [centroid(x, 1.6 + 0.2 * k, 1.8 + 0.2 * k) for k in range(8)]
    spread = (max(cs) - min(cs)) / np.mean(cs)
    check("the waveform moves after a strike (centroid varies > 15 %)", spread > 0.15,
          " ".join("%.0f" % c for c in cs))


def sc_bow():
    print("bow")
    (x, _) = run("bow", 12, "gkrecord = (kt > 2 ? 1 : 0)\ngkwindow = 0.5\n")
    a = [rms(x, t, t + 0.5) for t in (4, 6, 8, 10)]
    check("Record bows: sustained for seconds", min(a) > 0.03 and max(a) < 3 * min(a), " ".join("%.3f" % v for v in a))


def sc_input():
    print("input")
    (x, _) = run("input", 10, "gksource = (kt > 5 ? 1 : 0)\n", live="noise.wav")
    a, b = rms(x, 2, 4.8), rms(x, 6, 9.5)
    check("Source off: the input doesn't reach the string; on: it drives it", a < 0.01 and b > 0.03,
          "%.4f -> %.3f" % (a, b))


def sc_freeze():
    print("freeze")
    (x, _) = run("freeze", 10, strike_at(1.5) + "gkfreeze = (kt > 1.8 ? 1 : 0)\ngkwindow = 0.8\n")
    a = [rms(x, t, t + 0.4) for t in (2.0, 4.0, 6.0, 8.0)]
    check("Freeze holds the waveform (level steady)", min(a) > 0.03 and max(a) < 1.2 * min(a),
          " ".join("%.3f" % v for v in a))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = 0.1 + frac(kt * 0.05) * 1.1\n"
            "gkspeed = frac(kt * 0.09)\ngkrecord = (frac(kt / 15) > 0.5 ? 1 : 0)\ngksource = (kt > 30 ? 1 : 0)\n"
            "gkfreeze = (frac(kt / 7) > 0.85 ? 1 : 0)\ngkloopstart_alt = 1\ngkdensity_alt = 1\ngkblend_alt = 0.5\n"
            + "gkreset = (frac(kt * 2) < 0.02 ? 1 : 0)\n"
            + "gkloopsize = (kt > 45 ? 0 : gkloopsize)\ngkdensity = (kt > 45 ? 1 : gkdensity)\n"
            + "gkwindow = (kt > 45 ? 0 : gkwindow)\ngkoverlap = (kt > 45 ? 1 : gkoverlap)\n")
    (x, cpu) = run("sweep", 62, auto, live="noise.wav")
    seg = x[SR:]
    nan = int(np.isnan(seg).sum())
    late = [rms(x, t, t + 1) for t in range(46, 61, 3)]
    check("bounded, no NaN (60 s of extremes; 45-60 s lightest + stiffest + least damped)",
          nan == 0 and float(np.nanmax(np.abs(seg))) <= 1.0, "peak %.3f, NaN %d, late rms %s"
          % (float(np.nanmax(np.abs(seg))), nan, " ".join("%.2f" % v for v in late)))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "noise.wav"), "looper")
    print("  CPU for 62 s: scan %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.8x the factory looper", cpu < 1.8 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 6, BASE + strike_at(2.0), sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "6", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    a1 = rms(x, 2.05, 2.5)
    f1 = fundamental(x, 2.1, 2.6)
    check("6.09: compiles, a strike sounds at C3", ok and a1 > 0.05 and abs(f1 / 130.81 - 1) < 0.05,
          "rms %.3f, %.1f Hz" % (a1, f1))


def main():
    make_inputs()
    want = sys.argv[1:] or ["strike", "decay", "timbre", "bow", "input", "freeze", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
