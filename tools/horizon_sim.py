#!/usr/bin/env python3
"""Offline tests of instr/horizon.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/horizon_sim.py [scenario ...]
  python tools/horizon_sim.py m609

  pitch     Feedback up, no input: it rings by itself at the loop's pitch (C4 at the click, 1V/oct)
  start     below sustain it stays silent with no input
  polarity  Source: the loop inverted rings an octave down
  drive     Start: more drive, more harmonics; Freeze (Hyper) more still
  boost     Size / Density: the bass and treble boosts tilt the loop
  dynamics  Overlap: clockwise playing opens the loop; anticlockwise playing ducks it
  vca       File: the VCA out of the loop works the output level (it ducks the clean sound too)
  record    Record: the clean signal before / after the drive
  envelope  Reset: the envelope's decay fast / slow (the Pulse gate's fall)
  pulse     the Pulse jack: a gate while you play
  wobble    Speed: the loop's pitch moves past the clicks, not between them
  reverb    alt Blend: a stereo reverb
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles and sounds
Renders go to firmware/dist/horizon_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "horizon_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "horizon.instr")
SR = 48000
C4 = 261.626
# a plain start: no feedback, flat, Dynamics off, the loop out, no wobble
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0.4\ngkloopsize = 0\ngkdensity = 0\ngkwindow = 0\n"
        "gkoverlap = 0.5\ngkblend = 1\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\ngkreset = 0\n")
ALTS = "window_alt=0.5 blend_alt=0"
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    import wave
    t = np.arange(70 * SR) / SR
    rng = np.random.default_rng(4)
    sine = 0.3 * np.sin(2 * np.pi * 220 * t)
    sigs = {"in_silence.wav": np.zeros_like(t), "in_sine.wav": sine,
            "in_burst.wav": sine * ((t > 2.0) & (t < 3.0)), "in_noise.wav": 0.05 * rng.standard_normal(len(t))}
    for name, sig in sigs.items():
        with wave.open(os.path.join(OUT, name), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.stack([sig, sig], 1) * 32767).astype("<i2").tobytes())
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def run(name, secs, auto, alts=ALTS, wav="in_silence.wav"):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=alts, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, wav), name)


def spec(x, t0, t1):
    s = seg(x, t0, t1)
    n = 1 << 19
    return np.fft.rfftfreq(n, 1 / SR), np.abs(np.fft.rfft(s * np.hanning(len(s)), n))


def peak_in(x, t0, t1, lo, hi):
    f, sp = spec(x, t0, t1)
    m = np.flatnonzero((f > lo) & (f < hi))
    i = m[np.argmax(sp[m])]
    return float(f[i]), float(db(sp[i] + 1e-20))


def thd(x, t0, t1, f0=220):
    """Harmonics 2..10 against the fundamental, dB."""
    f, sp = spec(x, t0, t1)

    def pk(fr):
        m = (f > fr * 0.98) & (f < fr * 1.02)
        return float(np.max(sp[m]) ** 2)
    return float(10 * np.log10(sum(pk(f0 * k) for k in range(2, 11)) / pk(f0) + 1e-20))


def sc_pitch():
    print("pitch")
    got = []
    for p, f0 in ((0.6, C4), (0.8, 2 * C4), (0.4, C4 / 2)):
        (x, _) = run("pitch%g" % p, 3, "gkwindow = 0.85\ngkpitch = %g\n" % p)
        got.append((f0, peak_in(x, 2, 3, f0 * 0.75, f0 * 1.3)[0]))
    ok = all(abs(g / f0 - 1) < 0.03 for f0, g in got)
    check("Feedback up, no input: it rings at the loop's pitch, C4 at the click, 1V/oct (within 3 %)", ok,
          ", ".join("%.1f (want %.1f)" % (g, f0) for f0, g in got))


def sc_start():
    print("start")
    (x, _) = run("start_hi", 3, "gkwindow = 0.85\n")
    (y, _) = run("start_lo", 3, "gkwindow = 0.5\n")
    a, b = db(rms(x, 2, 3)), db(rms(y, 2, 3))
    check("it starts by itself past sustain (> -30 dB), not below it (< -70 dB)", a > -30 and b < -70,
          "%.1f vs %.1f dB" % (a, b))


def sc_polarity():
    print("polarity")
    (x, _) = run("pol", 3, "gkwindow = 0.85\ngksource = 1\n")
    lo, hi = peak_in(x, 2, 3, C4 * 0.4, C4 * 0.6), peak_in(x, 2, 3, C4 * 0.9, C4 * 1.1)
    check("Source: inverted, it rings an octave down (C3's peak > 10 dB over C4's)", lo[1] > hi[1] + 10 and
          abs(lo[0] / (C4 / 2) - 1) < 0.04, "%.1f Hz %.1f dB vs %.1f Hz %.1f dB" % (lo[0], lo[1], hi[0], hi[1]))


def sc_drive():
    print("drive")
    au = "gkblend = 0\ngkrecord = 1\n"
    r = [thd(run("drv%d" % i, 2.5, au + s, wav="in_sine.wav")[0], 1.5, 2.5)
         for i, s in enumerate(("gkloopstart = 0\n", "gkloopstart = 0.6\n", "gkloopstart = 0.6\ngkfreeze = 1\n"))]
    check("Start: more drive, more harmonics; Hyper more still (THD up > 10 dB each)",
          r[1] > r[0] + 10 and r[2] > r[1] + 3, "%.1f -> %.1f -> %.1f dB" % tuple(r))


def sc_boost():
    print("boost")
    au = "gkwindow = 0.5\n"
    (x, _) = run("bst0", 3, au, wav="in_noise.wav")
    (y, _) = run("bstb", 3, au + "gkloopsize = 1\n", wav="in_noise.wav")
    (z, _) = run("bstt", 3, au + "gkdensity = 1\n", wav="in_noise.wav")

    def share(w, lo, hi):
        f, p = psd(w, 1.5, 3)
        mid = (f > 300) & (f < 1500)
        return float(10 * np.log10(np.mean(p[(f > lo) & (f < hi)]) / np.mean(p[mid])))
    b0, b1 = share(x, 20, 180), share(y, 20, 180)
    t0, t1 = share(x, 3500, 16000), share(z, 3500, 16000)
    check("Size boosts the bass, Density the treble (each band against the mids up > 6 dB)", b1 > b0 + 6 and t1 > t0 + 6,
          "bass %.1f -> %.1f, treble %.1f -> %.1f dB" % (b0, b1, t0, t1))


def sc_dynamics():
    print("dynamics")
    au = "gkwindow = 0.85\n"
    (x, _) = run("dyn_cw", 4, au + "gkoverlap = 1\n", wav="in_burst.wav")
    (y, _) = run("dyn_ccw", 4, au + "gkoverlap = 0\n", wav="in_burst.wav")
    a0, a1 = db(rms(x, 1.0, 1.9)), db(rms(x, 2.3, 2.9))
    b0 = peak_in(y, 1.2, 1.9, C4 * 0.95, C4 * 1.05)[1]
    b1 = peak_in(y, 2.2, 2.9, C4 * 0.95, C4 * 1.05)[1]
    check("Overlap clockwise: silent until you play, then it opens (> 40 dB up)", a1 > a0 + 40, "%.1f -> %.1f dB" % (a0, a1))
    check("Overlap anticlockwise: your playing ducks the loop's scream (> 20 dB down)", b1 < b0 - 20,
          "%.1f -> %.1f dB" % (b0, b1))


def sc_vca():
    print("vca")
    au = "gkwindow = 0.85\ngkoverlap = 0\ngkblend = 0.5\n"
    (x, _) = run("vca_in", 4, au, wav="in_burst.wav")
    (y, _) = run("vca_out", 4, au + pulses(1.1, name="gkfilestate"), wav="in_burst.wav")
    a, b = db(rms(x, 2.3, 2.9)), db(rms(y, 2.3, 2.9))
    check("File: the VCA out of the loop ducks the whole output (the clean sound too: > 15 dB under in the loop)",
          b < a - 15, "%.1f vs %.1f dB" % (b, a))


def sc_record():
    print("record")
    au = "gkblend = 0\ngkloopstart = 0.8\n"
    a = thd(run("rec0", 2.5, au, wav="in_sine.wav")[0], 1.5, 2.5)
    b = thd(run("rec1", 2.5, au + "gkrecord = 1\n", wav="in_sine.wav")[0], 1.5, 2.5)
    check("Record: the clean signal from before the drive (pure) or after it (driven: THD > 20 dB more)",
          a < -40 and b > a + 20, "%.1f vs %.1f dB" % (a, b))


def gate_log(name, auto):
    log = os.path.join(OUT, "pulse_log.txt")
    if os.path.exists(log):
        os.remove(log)
    auto += "kge changed gkeol\nif kge == 1 then\n    fprintks \"pulse_log.txt\", \"%f %d\\n\", kt, gkeol\nendif\n"
    run(name, 5, auto, wav="in_burst.wav")
    rows = [ln.split() for ln in open(log)] if os.path.exists(log) else []
    return [float(t) for t, v in rows if v == "1"], [float(t) for t, v in rows if v == "0"]


def sc_envelope():
    print("envelope")
    _, offs = gate_log("env_slow", "")
    _, offf = gate_log("env_fast", "gkreset = 1\n")
    ok = len(offs) >= 1 and len(offf) >= 1 and offs[-1] > offf[-1] + 0.15
    check("Reset: a fast envelope lets go sooner (the Pulse gate falls > 150 ms earlier)", ok,
          "off slow %s, fast %s" % ([round(t, 3) for t in offs], [round(t, 3) for t in offf]))


def sc_pulse():
    print("pulse")
    on, off = gate_log("pulse", "")
    ok = len(on) == 1 and abs(on[0] - 2.0) < 0.03 and len(off) >= 1 and 3.0 < off[-1] < 4.0
    check("the Pulse jack: high as you start playing, low after you stop (one gate, no chatter)", ok,
          "on %s, off %s" % ([round(t, 3) for t in on], [round(t, 3) for t in off]))


def sc_wobble():
    print("wobble")
    res = []
    for sp in (0.55, 1.0, 0.0):
        (x, _) = run("wob%g" % sp, 5, "gkwindow = 0.85\ngkspeed = %g\n" % sp)
        fs = [peak_in(x, t, t + 0.12, C4 * 0.8, C4 * 1.25)[0] for t in np.arange(2, 4.8, 0.12)]
        res.append(float(np.std(fs) / np.mean(fs)))
    check("Speed: none between the clicks (< 0.3 %); past them it moves (> 1 %, both ways)",
          res[0] < 0.003 and res[1] > 0.01 and res[2] > 0.01, "spread %.2f, %.2f, %.2f %%" % tuple(100 * r for r in res))


def sc_reverb():
    print("reverb")
    au = "gkblend = 0\n"
    (x, _) = run("rev0", 4.5, au, wav="in_burst.wav")
    (y, _) = run("rev1", 4.5, au, alts="window_alt=0.5 blend_alt=1", wav="in_burst.wav")
    a, b = db(rms(x, 3.3, 3.8)), db(rms(y, 3.3, 3.8))
    lr = np.corrcoef(seg(y, 3.3, 3.8, 0), seg(y, 3.3, 3.8, 1))[0, 1]
    check("alt Blend: a stereo reverb tail after you stop (> 30 dB over none; left and right differ)",
          b > a + 30 and lr < 0.9, "%.1f vs %.1f dB, L/R correlation %.2f" % (b, a, lr))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkblend = frac(kt * 0.04)\n"
            "gkrecord = (frac(kt * 0.07) > 0.5 ? 1 : 0)\ngkfreeze = (frac(kt * 0.045) > 0.6 ? 1 : 0)\n"
            "gksource = (frac(kt / 11) > 0.5 ? 1 : 0)\ngkreset = (frac(kt * 0.03) > 0.5 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.1) < 0.02 ? 1 : 0)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkblend_alt = frac(kt * 0.02)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_sine.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN, ran to the end (60 s of extremes)",
          nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0 and len(x) > 61 * SR,
          "peak %.3f, NaN %d, %.1f s" % (float(np.nanmax(np.abs(s))), nan, len(x) / SR))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_sine.wav"), "looper")
    print("  CPU for 62 s: horizon %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper (with the reverb)", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 4, BASE + "gkwindow = 0.85\n", sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "4", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    check("6.09: compiles and rings by itself (rms > 0.02, no NaN)",
          ok and rms(x, 2, 3.9) > 0.02 and not np.isnan(x).any(), "rms %.3f" % rms(x, 2, 3.9))


def main():
    make_inputs()
    want = sys.argv[1:] or ["pitch", "start", "polarity", "drive", "boost", "dynamics", "vca", "record", "envelope",
                            "pulse", "wobble", "reverb", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
