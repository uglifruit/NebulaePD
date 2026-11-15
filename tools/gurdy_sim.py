#!/usr/bin/env python3
"""Offline tests of instr/gurdy.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/gurdy_sim.py [scenario ...]
  python tools/gurdy_sim.py m609

  drones    Source off: the bourdon (C2), mouche (G2) and trompette (C3) at the Pitch click, in tune
  melody    Source on, drones down: Start steps the major scale from C3 (C3, E3, G3, C4)
  mode      File x3 -> minor: the mouche moves to the octave, the scale's third to E flat
  crank     Speed: silent stopped, sounding at noon, louder and brighter fast
  trompette Reset strokes and Record buzz the trompette (energy at 1.5-4 kHz)
  surge     a quick turn of Speed buzzes it too; a slow one doesn't
  freeze    Freeze holds the melody note while Start moves
  pressure  Size: more scratch (high partials) at high bow pressure
  body      Window: a darker, larger body clockwise
  sympathy  Overlap: the sympathetic strings ring on after the wheel stops
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles, the bourdon sounds at C2
Renders go to firmware/dist/gurdy_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "gurdy_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "gurdy.instr")
SR = 48000
C2 = 65.406
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0\ngkloopsize = 0.4\ngkdensity = 0.7\ngkwindow = 0.5\n"
        "gkoverlap = 0\ngkblend = 1\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\n")
ALTS = "start_alt=0.6 size_alt=0 density_alt=0 window_alt=0.5 overlap_alt=0.5 blend_alt=0 pitch_alt=0"
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    import wave
    with wave.open(os.path.join(OUT, "in_silence.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.zeros((70 * SR, 2), "<i2").tobytes())
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def run(name, secs, auto, alts=ALTS):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=alts, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, "in_silence.wav"), name)


def near_peak(x, t0, t1, f0, tol=0.04):
    """The strongest frequency within +-tol of f0 (parabolic interpolation) and its level in dB."""
    s = seg(x, t0, t1)
    n = 1 << 19
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)), n))
    f = np.fft.rfftfreq(n, 1 / SR)
    m = np.flatnonzero((f > f0 * (1 - tol)) & (f < f0 * (1 + tol)))
    i = m[np.argmax(sp[m])]
    a, b, c = np.log(sp[i - 1:i + 2] + 1e-20)
    return float(f[i] + 0.5 * (a - c) / (a - 2 * b + c) * (f[1] - f[0])), float(db(sp[i]))


def hf(x, t0, t1, lo=1500, hi=4000):
    f, p = psd(x, t0, t1, n=2048 if t1 - t0 < 0.4 else 8192)
    return float(10 * np.log10(band(f, p, lo, hi) / band(f, p, 50, 1000)))


def centroid(x, t0, t1):
    f, p = psd(x, t0, t1)
    m = (f > 40) & (f < 12000)
    return float(np.sum(f[m] * p[m]) / np.sum(p[m]))


def sc_drones():
    print("drones")
    (x, _) = run("drones", 5, "gkdensity = 1\n")
    want = [C2, C2 * 1.4983, C2 * 2]
    got = [near_peak(x, 2.0, 4.9, w)[0] for w in want]
    check("bourdon, mouche, trompette at C2, G2, C3 (within 0.5 %)",
          all(abs(g / w - 1) < 0.005 for g, w in zip(got, want)),
          " ".join("%.2f" % g for g in got) + "  (want " + " ".join("%.2f" % w for w in want) + ")")
    check("level: rms > 0.05, peak under 1", rms(x, 2, 4.9) > 0.05 and float(np.abs(x).max()) < 1,
          "rms %.3f, peak %.3f" % (rms(x, 2, 4.9), float(np.abs(x).max())))


def sc_melody():
    print("melody")
    # Start -> degree int(Start * 15): 0, 2, 4, 7 = C3, E3, G3, C4
    auto = "gksource = 1\ngkdensity = 0\n" + steps("gkloopstart", (0, 0.01), (3.5, 2.5 / 15), (6, 4.5 / 15),
                                                      (8.5, 7.5 / 15))
    (x, _) = run("melody", 11, auto)
    want = [C2 * 2, C2 * 2 * 2 ** (4 / 12), C2 * 2 * 2 ** (7 / 12), C2 * 4]
    got = [near_peak(x, a + 0.5, a + 2.3, w)[0] for a, w in zip((1, 3.5, 6, 8.5), want)]
    check("Start plays C3, E3, G3, C4 (within 0.5 %)", all(abs(g / w - 1) < 0.005 for g, w in zip(got, want)),
          " ".join("%.2f" % g for g in got) + "  (want " + " ".join("%.2f" % w for w in want) + ")")


def sc_mode():
    print("mode")
    auto = ("gksource = 1\ngkdensity = 1\ngkloopstart = 2.5 / 15\n" +
            pulses(1.5, 1.8, 2.1, name="gkfilestate"))
    (x, _) = run("mode", 6, auto)
    g5 = near_peak(x, 3.0, 5.9, C2 * 1.4983, tol=0.01)[1]
    c3 = near_peak(x, 3.0, 5.9, C2 * 2, tol=0.01)[1]
    eb = near_peak(x, 3.0, 5.9, C2 * 2 * 2 ** (3 / 12), tol=0.015)
    check("minor: no mouche on G2 (> 18 dB under C3: the bow's noise floor), the third on E flat 3 (within 0.5 %)",
          c3 - g5 > 18 and abs(eb[0] / (C2 * 2 * 2 ** (3 / 12)) - 1) < 0.005,
          "G2 %+.1f dB under C3, third %.2f Hz" % (c3 - g5, eb[0]))


def sc_crank():
    print("crank")
    auto = steps("gkspeed", (0, 0), (4, 0.5), (8, 1))
    (x, _) = run("crank", 12, auto)
    a, b, c = rms(x, 2.5, 3.9), rms(x, 6, 7.9), rms(x, 10, 11.9)
    check("stopped: silent; noon: sounding; fast: louder", a < 1e-3 and b > 0.05 and c > b,
          "rms %.4f, %.3f, %.3f" % (a, b, c))
    cb, cc = centroid(x, 6, 7.9), centroid(x, 10, 11.9)
    check("fast: brighter (centroid up > 15 %)", cc > 1.15 * cb, "%.0f -> %.0f Hz" % (cb, cc))


def sc_trompette():
    print("trompette")
    auto = pulses(3.0, 3.5, 4.0, 4.5) + "gkrecord = (kt > 7 ? 1 : 0)\n"
    (x, _) = run("trompette", 10, auto)
    q = hf(x, 2.0, 2.9)
    st = max(hf(x, t + 0.005, t + 0.08) for t in (3.0, 3.5, 4.0, 4.5))
    rec = hf(x, 8, 9.9)
    check("Reset strokes buzz it (1.5-4 kHz up > 6 dB)", st - q > 6, "%+.1f dB" % (st - q))
    check("Record: buzzing all the time (> 6 dB)", rec - q > 6, "%+.1f dB" % (rec - q))


def sc_surge():
    print("surge")
    auto = "gkspeed = (kt < 3 ? 0.35 : (kt < 3.05 ? 0.35 + (kt - 3) * 9 : (kt < 6 ? 0.8 : 0.8 - (kt - 6) * 0.15)))\n"
    (x, _) = run("surge", 8, auto)
    q = hf(x, 2, 2.9)
    s = hf(x, 3.08, 3.2)
    later = hf(x, 4.5, 4.62)
    # (against the same speed later: turning faster brightens the strings by itself)
    check("a quick turn buzzes it: 1.5-4 kHz > 3 dB over the same speed a second later", s - later > 3,
          "%+.1f dB over before, %+.1f dB over later" % (s - q, s - later))


def sc_freeze():
    print("freeze")
    auto = ("gksource = 1\ngkdensity = 0\ngkfreeze = (kt > 2.5 ? 1 : 0)\n" +
            steps("gkloopstart", (0, 4.5 / 15), (3.5, 0.01)))
    (x, _) = run("freeze", 6, auto)
    want = C2 * 2 * 2 ** (7 / 12)
    f = near_peak(x, 4, 5.9, want, tol=0.02)[0]
    c = near_peak(x, 4, 5.9, C2 * 2, tol=0.02)[1]
    g = near_peak(x, 4, 5.9, want, tol=0.02)[1]
    check("Freeze holds G3 while Start goes to C3 (G3 within 0.5 %, C3 > 15 dB under)",
          abs(f / want - 1) < 0.005 and g - c > 15, "%.2f Hz, C3 %+.1f dB under" % (f, g - c))


def sc_pressure():
    print("pressure")
    (x, _) = run("press0", 5, "gkloopsize = 0\n")
    (y, _) = run("press1", 5, "gkloopsize = 1\n")
    a, b = hf(x, 2, 4.9, 2000, 8000), hf(y, 2, 4.9, 2000, 8000)
    check("Size: more high partials at high pressure (> 3 dB)", b - a > 3, "%+.1f dB" % (b - a))


def sc_body():
    print("body")
    (x, _) = run("body0", 5, "gkwindow = 0\n")
    (y, _) = run("body1", 5, "gkwindow = 1\n")
    a, b = centroid(x, 2, 4.9), centroid(y, 2, 4.9)
    check("Window: darker clockwise (centroid down > 10 %)", b < 0.9 * a, "%.0f -> %.0f Hz" % (a, b))


def sc_sympathy():
    print("sympathy")
    auto = "gkspeed = (kt < 4 ? 0.5 : 0)\n"
    (x, _) = run("sym0", 7, auto + "gkoverlap = 0\n")
    (y, _) = run("sym1", 7, auto + "gkoverlap = 1\n")
    a, b = db(rms(x, 5.2, 5.6)), db(rms(y, 5.2, 5.6))
    check("Overlap: the sympathetic strings ring on after the wheel stops (> 10 dB more, 1.2 s later)", b - a > 10,
          "%.1f -> %.1f dB" % (a, b))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkrecord = (frac(kt / 15) > 0.7 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.3 ? 1 : 0)\n"
            "gkfreeze = (frac(kt / 7) > 0.8 ? 1 : 0)\ngkreset = (frac(kt * 3) < 0.02 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.4) < 0.03 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\ngkdensity_alt = frac(kt * 0.04)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkoverlap_alt = frac(kt * 0.03)\ngkblend_alt = frac(kt * 0.02)\n")
    (x, cpu) = run("sweep", 62, auto)
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_silence.wav"), "looper")
    print("  CPU for 62 s: gurdy %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 5, BASE + "gkdensity = 1\n", sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "5", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f = near_peak(x, 2.0, 4.9, C2)[0]
    check("6.09: compiles, the bourdon at C2 (within 0.5 %)", ok and abs(f / C2 - 1) < 0.005,
          "%.2f Hz, rms %.3f" % (f, rms(x, 2.0, 4.9)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["drones", "melody", "mode", "crank", "trompette", "surge", "freeze", "pressure", "body",
                            "sympathy", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
