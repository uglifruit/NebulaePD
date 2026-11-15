#!/usr/bin/env python3
"""Offline tests of instr/tanpura.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609, from
Windows Python).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/tanpura_sim.py [scenario ...]
  python tools/tanpura_sim.py m609

  strings  clocked plucks, one string at a time: Pa (98.1 Hz), Sa, Sa (130.8), low Sa (65.4) at the Pitch click
  tuning   Start zones: the first string at Pa / Ma / Ni / Sa (x 3/2, 4/3, 15/8, 2 of low Sa)
  self     it plays itself: a pluck every second at Speed noon (4 s cycle), four a second fully clockwise
  clock    Reset pulses: a pluck on each one; 2 s after the last pulse it plays itself again
  pause    Record: no new plucks, the strings ring on
  freeze   Freeze: the strings ring on (level held), against a normal decay
  ring     Window: ring time short (about 2 s) -> long (several times longer)
  jawari   Density: more buzz (high partials) that lasts as the note rings
  octave   Source: everything an octave up
  sweep    every knob at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609     Csound 6.09.1: compiles, a clocked pluck sounds at low Sa
Renders go to firmware/dist/tanpura_sim/.
"""
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "tanpura_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "tanpura.instr")
SR = 48000
BASE = ("gkspeed = 0.5\ngkloopstart = 0.1\ngkloopsize = 0.5\ngkdensity = 0.5\ngkwindow = 0.5\n"
        "gkoverlap = 0\ngkblend = 1\ngkpitch = 0.6\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\n")
ALTS = "start_alt=0.6 size_alt=0.4 density_alt=0.5 window_alt=0.6 overlap_alt=0.5 blend_alt=0 pitch_alt=0"
RESULTS = []
C2 = 65.406


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    n = 70 * SR
    data = np.zeros((n, 2), "<i2")
    with wave.open(os.path.join(OUT, "silence.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def pulses(*ts, name="gkreset"):
    return name + " = (" + " || ".join("(kt > %g && kt < %g)" % (t, t + 0.01) for t in ts) + " ? 1 : 0)\n"


def run(name, secs, auto, alts=ALTS):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=alts, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, "silence.wav"), name)


def seg(x, t0, t1, ch=None):
    s = x[int(t0 * SR):int(t1 * SR)]
    return s.mean(axis=1) if ch is None else s[:, ch]


def rms(x, t0, t1):
    return float(np.sqrt(np.mean(seg(x, t0, t1) ** 2)))


def db(v):
    return 20 * np.log10(v + 1e-12)


def spectrum(x, t0, t1):
    s = seg(x, t0, t1)
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)), 1 << 18))
    return np.fft.rfftfreq(1 << 18, 1 / SR), sp


def lowest_strong(x, t0, t1, lo=40, hi=1500, rel=0.1):
    """The lowest spectral peak within rel of the strongest (the fundamental of a plucked string)."""
    f, sp = spectrum(x, t0, t1)
    m = np.flatnonzero((f > lo) & (f < hi))
    top = sp[m].max()
    for i in m:
        if sp[i] > rel * top and sp[i] >= sp[i - 1] and sp[i] >= sp[i + 1]:
            return float(f[i])
    return 0.0


def onsets(x, t0, t1):
    """Plucks: jumps in the 2-8 kHz band (the pluck's noise burst). The full-band level also swells as the strings
    beat against each other, which looked like plucks."""
    s = seg(x, t0, t1)
    S_ = np.fft.rfft(s)
    f = np.fft.rfftfreq(len(s), 1 / SR)
    S_[(f < 2000) | (f > 8000)] = 0
    s = np.fft.irfft(S_, len(s))
    w = int(0.005 * SR)
    e = np.sqrt(np.convolve(s ** 2, np.ones(w) / w, "valid")[::w])
    out = []
    for i in range(4, len(e)):
        if e[i] > 4 * e[i - 3] + 1e-5 and e[i] > 0.05 * e.max():
            t = t0 + i * 0.005
            if t > t1 - 0.06:                         # the band filter rings at the window's end
                break
            if not out or t - out[-1] > 0.08:
                out.append(t)
    return out


def sc_strings():
    print("strings")
    # (the instrument starts at 1 s and plucks by itself at 1.3 s: the first pulse comes before that)
    ts = [1.15, 2.95, 4.75, 6.55]
    (x, _) = run("strings", 8.8, pulses(*ts) + "gkwindow = 0\n")
    want = [C2 * 1.5, C2 * 2, C2 * 2, C2]
    got = [lowest_strong(x, t + 0.1, t + 1.0) for t in ts]
    check("one string per pulse: Pa, Sa, Sa, low Sa (within 0.5 %)",
          all(abs(g / w_ - 1) < 0.005 for g, w_ in zip(got, want)),
          " ".join("%.1f" % g for g in got) + "  (want " + " ".join("%.1f" % w_ for w_ in want) + ")")
    check("level: a pluck at rms > 0.05, peak under 1", float(np.abs(x).max()) < 1.0 and rms(x, 1.2, 1.7) > 0.05,
          "peak %.3f, rms after a pluck %.3f" % (float(np.abs(x).max()), rms(x, 1.2, 1.7)))


def sc_tuning():
    print("tuning")
    ts = [1.15 + 1.5 * k for k in range(13)]          # string 1 on pulses 1, 5, 9, 13
    auto = (pulses(*ts) + "gkwindow = 0\n"
            "gkloopstart = (kt < 6.5 ? 0.1 : (kt < 12.5 ? 0.35 : (kt < 18.5 ? 0.6 : 0.9)))\n")
    (x, _) = run("tuning", 20.5, auto)
    got = [lowest_strong(x, ts[i] + 0.1, ts[i] + 1.0) / C2 for i in (0, 4, 8, 12)]
    want = [1.5, 4 / 3, 15 / 8, 2.0]
    check("Start zones: first string x 3/2, 4/3, 15/8, 2 of low Sa (within 0.5 %)",
          all(abs(g / w_ - 1) < 0.005 for g, w_ in zip(got, want)), " ".join("%.3f" % g for g in got))


def sc_self():
    print("self")
    (x, _) = run("self", 21, "gkspeed = (kt < 12 ? 0.5 : 1)\ngkwindow = 0.2\n")
    a = onsets(x, 1.2, 11.9)
    b = onsets(x, 13.0, 20.9)
    ia, ib = np.median(np.diff(a)), np.median(np.diff(b))
    # the plucks come at 1.3 s (the instrument starts at 1 s) and every second after (Overlap 0: no sway); the
    # buzz adds a few extra detections, so check that each expected pluck is found
    miss = [t for t in (1.3 + k for k in range(10)) if min(abs(o - t) for o in a) > 0.03]
    check("noon: a pluck every second (4 s cycle)", abs(ia - 1.0) < 0.03 and not miss,
          "median gap %.3f s, missing %s" % (ia, miss))
    check("fully clockwise: four a second", abs(ib - 0.25) < 0.02, "median gap %.3f s" % ib)


def sc_clock():
    print("clock")
    ts = [2.0 + 0.37 * k for k in range(12)]           # 2.0 .. 6.07
    (x, _) = run("clock", 12, pulses(*ts) + "gkwindow = 0.2\n")
    on = onsets(x, 1.95, 6.5)
    near = [min(abs(o - t) for o in on) for t in ts]
    check("a pluck on every pulse (within 25 ms: the detector steps 5 ms)", max(near) < 0.025, "worst %.1f ms" % (1000 * max(near)))
    extra = [o for o in on if min(abs(o - t) for t in ts) > 0.05]
    check("nothing else while clocked", not extra, "extra plucks at %s" % [round(e, 2) for e in extra])
    late = onsets(x, 8.3, 11.9)
    check("2 s after the last pulse it plays itself again", len(late) >= 3, "%d plucks in 8.3-11.9 s" % len(late))


def sc_pause():
    print("pause")
    (x, _) = run("pause", 10, "gkrecord = (kt > 3 ? 1 : 0)\ngkwindow = 0.8\n")
    late = onsets(x, 3.2, 9.5)                         # (the band filter rings at the window's ends)
    check("Record: no new plucks, the strings ring on", not late and rms(x, 3.5, 4.0) > 0.3 * rms(x, 2.5, 3.0),
          "%d plucks; level %.3f -> %.3f" % (len(late), rms(x, 2.5, 3.0), rms(x, 3.5, 4.0)))


def sc_freeze():
    print("freeze")
    auto = "gkrecord = (kt > 4.2 ? 1 : 0)\ngkwindow = 0.2\n"
    (x, _) = run("freeze0", 12, auto)
    (y, _) = run("freeze1", 12, auto + "gkfreeze = (kt > 4.3 ? 1 : 0)\n")
    a, b = db(rms(y, 5, 6)), db(rms(y, 10, 11))
    c = db(rms(x, 10, 11))
    check("Freeze: held (within 3 dB over 5 s) against a normal decay", abs(b - a) < 3 and c < a - 30,
          "frozen %.1f -> %.1f dB, unfrozen %.1f dB" % (a, b, c))


def t20(x, t0, t1):
    """Seconds from t0 until the level is 20 dB under its level just after t0 (50 ms windows)."""
    s = seg(x, t0, t1)
    w = int(0.05 * SR)
    r = np.array([np.sqrt(np.mean(s[i:i + w] ** 2)) for i in range(0, len(s) - w, w)])
    ref = r[1:4].max()
    below = np.nonzero(r[4:] < ref * 0.1)[0]
    return (4 + below[0]) * 0.05 if len(below) else (t1 - t0)


def sc_ring():
    print("ring")
    auto = "gkrecord = (kt > 1.6 ? 1 : 0)\n"           # one clocked pluck, then paused (no self-playing)
    (x, _) = run("ring0", 8, pulses(1.5) + auto + "gkwindow = 0\n")
    (y, _) = run("ring1", 20, pulses(1.5) + auto + "gkwindow = 0.6\n")
    a, b = t20(x, 1.5, 7.9), t20(y, 1.5, 19.9)
    check("Window: rings longer clockwise (-20 dB times x3)", b > 3 * a, "%.2f s -> %.2f s" % (a, b))


def hf_ratio(x, t0, t1):
    f, sp = spectrum(x, t0, t1)
    p = sp ** 2
    return float(p[(f > 1500) & (f < 8000)].sum() / p[(f > 40) & (f < 1500)].sum())


def sc_jawari():
    print("jawari")
    auto = pulses(1.5) + "gkrecord = (kt > 1.6 ? 1 : 0)\ngkwindow = 0.5\n"
    (x, _) = run("jaw0", 6.5, auto + "gkdensity = 0\n")
    (y, _) = run("jaw1", 6.5, auto + "gkdensity = 1\n")
    # (hf_ratio is a power ratio: 10 log10. Right after the pluck its noise burst fills the top in both)
    e1 = (db(hf_ratio(y, 2.3, 2.8)) - db(hf_ratio(x, 2.3, 2.8))) / 2
    e2 = (db(hf_ratio(y, 4.0, 5.0)) - db(hf_ratio(x, 4.0, 5.0))) / 2
    check("Density: more buzz (energy over 1.5 kHz) 1 s and 3 s after the pluck (> +4, > +8 dB)",
          e1 > 4 and e2 > 8, "%+.1f dB, %+.1f dB" % (e1, e2))
    f0 = lowest_strong(y, 1.7, 2.7)
    check("the buzz doesn't detune the string (Pa within 0.5 %)", abs(f0 / (1.5 * C2) - 1) < 0.005, "%.2f Hz" % f0)


def sc_octave():
    print("octave")
    (x, _) = run("octave", 4.5, pulses(1.5) + "gkrecord = (kt > 1.6 ? 1 : 0)\ngkwindow = 0\ngksource = 1\n")
    f = lowest_strong(x, 1.6, 2.5)
    check("Source: an octave up (Pa at 196.2 Hz)", abs(f / (3 * C2) - 1) < 0.005, "%.1f Hz" % f)


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkrecord = (frac(kt / 15) > 0.8 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.5 ? 1 : 0)\n"
            "gkfreeze = (frac(kt / 7) > 0.6 ? 1 : 0)\ngkreset = (kt > 40 && frac(kt * 4) < 0.02 ? 1 : 0)\n"
            "gkloopsize_alt = frac(kt * 0.05)\ngkloopstart_alt = frac(kt * 0.06)\ngkblend_alt = 0.6\n")
    (x, cpu) = run("sweep", 62, auto)
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "silence.wav"), "looper")
    print("  CPU for 62 s: tanpura %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.8x the factory looper", cpu < 1.8 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 7, BASE + pulses(1.15, 2.35, 3.55, 4.75) + "gkwindow = 0\n", sets=ALTS,
                     wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "7", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f4 = lowest_strong(x, 4.85, 5.75)
    check("6.09: compiles, the 4th pluck sounds at low Sa", ok and abs(f4 / C2 - 1) < 0.005,
          "%.2f Hz, rms %.3f" % (f4, rms(x, 4.85, 5.75)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["strings", "tuning", "self", "clock", "pause", "freeze", "ring", "jawari", "octave",
                            "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
