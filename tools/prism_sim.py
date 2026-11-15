#!/usr/bin/env python3
"""Offline tests of instr/prism.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/prism_sim.py [scenario ...]
  python tools/prism_sim.py m609

  tune      chromatic, spread 1: odd bands (left) on C, D, E; even (right) on C#, D#, F
  pitch     Pitch transposes, 1V/oct
  scale     File: the next scale (major)
  spread    Start: the bands 4 steps apart
  rotate    Reset rotates up (the notes cross sides), Freeze down
  climb     Record: scale rotation (every band steps along the scale)
  lock      Source: the odd bands hold while the even ones rotate
  morph     Density: a short morph lands at once, a long one takes its time
  auto      Speed: no rotation between the clicks; past them it rotates, up and down
  pulse     the Pulse jack: a gate on each step
  nudge     Window: odd bands up, even down
  tilt      Overlap: high bands louder clockwise
  q         Size: higher Q, sharper peaks
  blend     Blend at 0: the dry input
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles and sounds
Renders go to firmware/dist/prism_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "prism_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "prism.instr")
SR = 48000
C3 = 130.813


def st(n):
    return C3 * 2 ** (n / 12)


# a plain start: chromatic, spread 1, high Q, wet, no nudge or tilt, no auto-rotation
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0\ngkloopsize = 0.85\ngkdensity = 0\ngkwindow = 0.5\n"
        "gkoverlap = 0.5\ngkblend = 1\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\ngkreset = 0\n")
ALTS = "speed_alt=0.5"
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    import wave
    rng = np.random.default_rng(7)
    noise = 0.1 * rng.standard_normal(70 * SR)
    tt = np.arange(70 * SR) / SR
    chord = sum(0.02 * np.sin(2 * np.pi * st(n) * tt + n) for n in range(24))   # every chromatic note, steady
    for name, sig in (("in_noise.wav", noise), ("in_silence.wav", np.zeros_like(noise)), ("in_chord.wav", chord)):
        with wave.open(os.path.join(OUT, name), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.stack([sig, sig], 1) * 32767).astype("<i2").tobytes())
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def run(name, secs, auto="", alts=ALTS, wav="in_noise.wav"):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=alts, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, wav), name)


def lvl(x, t0, t1, f, ch=0):
    """The level (dB) at f: the spectrum's peak within half a percent."""
    s = seg(x, t0, t1, ch)
    n = 1 << 20
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)), n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    m = (fr > f * 0.995) & (fr < f * 1.005)
    return float(db(np.max(sp[m]) + 1e-20))


def has(x, t0, t1, fs, ch, others):
    """Every frequency in fs stands > 15 dB over every one in others (on that channel)."""
    a = [lvl(x, t0, t1, f, ch) for f in fs]
    b = [lvl(x, t0, t1, f, ch) for f in others]
    return min(a) > max(b) + 15, a, b


ODD0 = [st(0), st(2), st(4)]
EVEN0 = [st(1), st(3), st(5)]


def sc_tune():
    print("tune")
    (x, _) = run("tune", 3)
    okl, a, b = has(x, 1.5, 3, ODD0, 0, EVEN0)
    okr, c, d = has(x, 1.5, 3, EVEN0, 1, ODD0)
    check("chromatic, spread 1: left on C3 D3 E3, right on C#3 D#3 F3 (> 15 dB over the other side's)", okl and okr,
          "left %s vs %s, right %s vs %s" % ([round(v) for v in a], [round(v) for v in b], [round(v) for v in c],
                                            [round(v) for v in d]))


def sc_pitch():
    print("pitch")
    (x, _) = run("pitch", 3, "gkpitch = 0.8\n")
    ok, a, b = has(x, 1.5, 3, [2 * f for f in ODD0], 0, ODD0)
    check("Pitch transposes, 1V/oct (+1 octave)", ok, "%s vs %s dB" % ([round(v) for v in a], [round(v) for v in b]))


def sc_scale():
    print("scale")
    (x, _) = run("scale", 3, pulses(1.1, name="gkfilestate"))
    ok, a, b = has(x, 1.5, 3, [st(0), st(4), st(7)], 0, [st(2), st(5)])
    check("File: the next scale, major (left on C E G)", ok, "%s vs %s dB" % ([round(v) for v in a], [round(v) for v in b]))


def sc_spread():
    print("spread")
    (x, _) = run("spread", 3, "gkloopstart = 1\n")
    ok, a, b = has(x, 1.5, 3, [st(0), st(8), st(16)], 0, [st(2), st(4)])
    check("Start: the bands 4 steps apart (left on C3 G#3 E4)", ok, "%s vs %s dB" % ([round(v) for v in a], [round(v) for v in b]))


def sc_rotate():
    print("rotate")
    (x, _) = run("rotup", 4, pulses(1.5))
    (y, _) = run("rotdn", 4, "gkfreeze = (kt > 1.5 && kt < 1.51 ? 1 : 0)\n")
    oku, a, b = has(x, 2.5, 4, EVEN0, 0, ODD0)                 # up: the left bands take the next notes (C# D# F)
    okd, c, d = has(y, 2.5, 4, [st(5), st(1), st(3)], 0, [st(0), st(2), st(4)])
    okr, e, f = has(x, 2.5, 4, [st(2), st(4), st(0)], 1, [st(1), st(3), st(5)])
    check("Reset rotates up: the notes cross sides (left now C# D# F, right C D E)", oku and okr,
          "left %s vs %s" % ([round(v) for v in a], [round(v) for v in b]))
    check("Freeze rotates down (left takes F C# D#)", okd, "%s vs %s" % ([round(v) for v in c], [round(v) for v in d]))


def sc_climb():
    print("climb")
    (x, _) = run("climb", 4, "gkrecord = 1\n" + pulses(1.5))
    ok, a, b = has(x, 2.5, 4, [st(2), st(4), st(6)], 1, [st(1), st(3), st(5)])
    check("Record (scale rotation): every band steps along the scale (right climbs to D E F#)", ok,
          "%s vs %s" % ([round(v) for v in a], [round(v) for v in b]))


def sc_lock():
    print("lock")
    (x, _) = run("lock", 4, "gksource = 1\n" + pulses(1.5))
    okl, a, b = has(x, 2.5, 4, ODD0, 0, EVEN0)
    okr, c, d = has(x, 2.5, 4, [st(2), st(4), st(0)], 1, [st(1), st(3), st(5)])
    check("Source (lock): the left bands hold (C D E) while the right rotate on", okl and okr,
          "left %s, right %s" % ([round(v) for v in a], [round(v) for v in c]))


def env_at(x, f, ch=0, win=0.06):
    """The level at f over time: demodulated, then a moving average."""
    s = x[:, ch]
    t = np.arange(len(s)) / SR
    z = s * np.exp(-2j * np.pi * f * t)
    w = int(win * SR)
    c = np.cumsum(np.concatenate([[0], z]))
    return np.abs((c[w:] - c[:-w]) / w)


def rise(x, f, t0):
    e = env_at(x, f)
    fin = np.mean(e[int((t0 + 2.5) * SR):int((t0 + 3) * SR)])
    i = np.flatnonzero(e[int(t0 * SR):] > fin * 0.9)
    return i[0] / SR if len(i) else 9


def sc_morph():
    print("morph")
    au = "gkloopstart = 1\ngkloopsize = 0.5\n" + pulses(2.0)
    (x, _) = run("morph0", 5.5, au, wav="in_chord.wav")
    (y, _) = run("morph1", 5.5, au + "gkdensity = 0.8\n", wav="in_chord.wav")
    a, b = rise(x, st(4), 2.0), rise(y, st(4), 2.0)          # the left's first band: C3 -> E3
    check("Density: a short morph lands at once (< 0.3 s to 90 %, the filter's own ring-up), a long one takes its "
          "time (> 0.45 s and twice as long)", a < 0.3 and b > 0.45 and b > 2 * a, "%.3f vs %.3f s" % (a, b))


def pulse_log(name, auto, secs=5):
    log = os.path.join(OUT, "pulse_log.txt")
    if os.path.exists(log):
        os.remove(log)
    auto += "kge changed gkeol\nif kge == 1 then\n    fprintks \"pulse_log.txt\", \"%f %d\\n\", kt, gkeol\nendif\n"
    (x, _) = run(name, secs, auto)
    rows = [ln.split() for ln in open(log)] if os.path.exists(log) else []
    return x, [float(t) for t, v in rows if v == "1"]


def sc_auto():
    print("auto")
    _, a = pulse_log("auto0", "gkspeed = 0.56\n")
    x, b = pulse_log("auto1", "gkspeed = 1\n")
    y, c = pulse_log("auto2", "gkspeed = 0\n")
    nb, nc = len([t for t in b if t > 1.5]), len([t for t in c if t > 1.5])
    check("Speed: between the clicks no rotation; past them it rotates (> 5 steps in 3.5 s, both ways)",
          len(a) == 0 and nb > 5 and nc > 5, "steps %d, %d, %d" % (len(a), nb, nc))


def sc_pulse():
    print("pulse")
    _, on = pulse_log("pulse", pulses(2.0) + "gkfreeze = (kt > 3.0 && kt < 3.01 ? 1 : 0)\n")
    ok = len(on) == 2 and abs(on[0] - 2.0) < 0.02 and abs(on[1] - 3.0) < 0.02
    check("the Pulse jack: a gate on each step (Reset at 2 s, Freeze at 3 s)", ok, "on %s" % [round(t, 3) for t in on])


def sc_nudge():
    print("nudge")
    (x, _) = run("nudge", 3, "gkwindow = 1\n")
    okl, a, b = has(x, 1.5, 3, [f * 2 ** (5 / 12) for f in ODD0], 0, ODD0)
    okr, c, d = has(x, 1.5, 3, [f * 2 ** (-5 / 12) for f in EVEN0], 1, EVEN0)
    check("Window: odd bands up 5 semitones, even down 5", okl and okr,
          "left %s vs %s, right %s vs %s" % ([round(v) for v in a], [round(v) for v in b], [round(v) for v in c],
                                            [round(v) for v in d]))


def sc_tilt():
    print("tilt")
    (x, _) = run("tilt0", 3)
    (y, _) = run("tilt1", 3, "gkoverlap = 1\n")
    a = lvl(x, 1.5, 3, st(5), 1) - lvl(x, 1.5, 3, st(1), 1)
    b = lvl(y, 1.5, 3, st(5), 1) - lvl(y, 1.5, 3, st(1), 1)
    check("Overlap: clockwise the high bands get louder (band 6 vs band 2 up > 15 dB)", b > a + 15,
          "%+.1f -> %+.1f dB" % (a, b))


def sc_q():
    print("q")

    def peak(z):
        return lvl(z, 1.5, 3, C3, 0) - lvl(z, 1.5, 3, C3 * 0.9, 0)
    (x, _) = run("q0", 3, "gkloopsize = 0.2\n")
    (y, _) = run("q1", 3, "gkloopsize = 0.9\n")
    a, b = peak(x), peak(y)
    check("Size: higher Q, a sharper peak (C3 over 10 % below it, up > 15 dB)", b > a + 15, "%.1f -> %.1f dB" % (a, b))


def sc_blend():
    print("blend")
    (x, _) = run("blend0", 3, "gkblend = 0\n")
    d = S.read_wav(os.path.join(OUT, "in_noise.wav"))
    n = min(len(x), len(d))
    err = float(np.max(np.abs(x[SR:n, 0] - np.tanh(d[SR:n, 0]))))
    check("Blend at 0: the dry input", err < 0.002, "max difference %.5f" % err)


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkblend = frac(kt * 0.04)\n"
            "gkrecord = (frac(kt * 0.07) > 0.5 ? 1 : 0)\ngkfreeze = (frac(kt * 0.45) < 0.05 ? 1 : 0)\n"
            "gksource = (frac(kt / 11) > 0.5 ? 1 : 0)\ngkreset = (frac(kt * 0.7) < 0.02 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.3) < 0.02 ? 1 : 0)\n")
    (x, cpu) = run("sweep", 62, auto)
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN, ran to the end (60 s of extremes)",
          nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0 and len(x) > 61 * SR,
          "peak %.3f, NaN %d, %.1f s" % (float(np.nanmax(np.abs(s))), nan, len(x) / SR))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_noise.wav"), "looper")
    print("  CPU for 62 s: prism %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 4, BASE + pulses(2.0), sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "4", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    check("6.09: compiles and runs (no NaN; no input here, so silence is right)", ok and not np.isnan(x).any(),
          "peak %.4f" % float(np.max(np.abs(x))))


def main():
    make_inputs()
    want = sys.argv[1:] or ["tune", "pitch", "scale", "spread", "rotate", "climb", "lock", "morph", "auto", "pulse",
                            "nudge", "tilt", "q", "blend", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
