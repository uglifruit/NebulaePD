#!/usr/bin/env python3
"""Offline tests of instr/chorale.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609, from
Windows Python).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/chorale_sim.py [scenario ...]
  python tools/chorale_sim.py m609

  pitch    one voice, no spread, no vibrato: C2 at the Pitch click, C3 at Pitch 0.8
  vowel    Start: "ah" has its 2nd formant near 1 kHz, "ee" near 1.75 kHz and its 1st low (bass register)
  register File: bass -> tenor -> alto -> soprano, the formants climb
  shift    Size clockwise: the formants move up
  voices   Density 1 = 8 voices: a wider spread round each harmonic; the level stays within 4 dB
  chord    Source + Reset (major): E sounds; Source off: it doesn't
  drift    Speed past a click: the vowel wanders; between the clicks and with Freeze: it holds
  breathe  Record: the voices drop out for breaths (the level dips now and then)
  breath   Overlap: air between the harmonics
  sweep    every knob at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609     Csound 6.09.1: compiles, sings at C2
Renders go to firmware/dist/chorale_sim/.
"""
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "chorale_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "chorale.instr")
SR = 48000
BASE = ("gkspeed = 0.5\ngkloopstart = 0\ngkloopsize = 0.5\ngkdensity = 0.5\ngkwindow = 0.4\n"
        "gkoverlap = 0\ngkblend = 1\ngkpitch = 0.6\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\n")
ALTS = "start_alt=0.7 size_alt=0.3 density_alt=0.5 window_alt=0.6 overlap_alt=0.5 blend_alt=0 pitch_alt=0"
DRY = ALTS.replace("size_alt=0.3", "size_alt=0")                    # no vibrato
RESULTS = []
C2 = 65.406


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    data = np.zeros((70 * SR, 2), "<i2")
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


def seg(x, t0, t1):
    return x[int(t0 * SR):int(t1 * SR)].mean(axis=1)


def rms(x, t0, t1):
    return float(np.sqrt(np.mean(seg(x, t0, t1) ** 2)))


def db(v):
    return 20 * np.log10(v + 1e-12)


def spectrum(x, t0, t1):
    s = seg(x, t0, t1)
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)), 1 << 18))
    return np.fft.rfftfreq(1 << 18, 1 / SR), sp


def fundamental(x, t0, t1):
    f, sp = spectrum(x, t0, t1)
    df = f[1]
    m = sp[(f > 30) & (f < 4000)]
    ac = np.correlate(m, m, "full")[len(m) - 1:]
    lo, hi = int(40 / df), int(400 / df)
    return (lo + int(np.argmax(ac[lo:hi]))) * df


def env_db(x, t0, t1, f_lo, f_hi):
    """Mean power (dB) of the harmonic peaks between f_lo and f_hi (the spectral envelope there)."""
    f, sp = spectrum(x, t0, t1)
    m = (f > f_lo) & (f < f_hi)
    return float(10 * np.log10(np.mean(np.sort(sp[m] ** 2)[-20:]) + 1e-20))


def centroid(x, t0, t1):
    f, sp = spectrum(x, t0, t1)
    m = (f > 100) & (f < 6000)
    return float((sp[m] * f[m]).sum() / sp[m].sum())


def sc_pitch():
    print("pitch")
    (x, _) = run("pitch", 6, "gkdensity = 0\ngkwindow = 0\ngkpitch = (kt < 3.5 ? 0.6 : 0.8)\n", alts=DRY)
    f1, f2 = fundamental(x, 1.5, 3.4), fundamental(x, 4.0, 5.9)
    check("one voice at C2 (click), C3 at 0.8 (within 1 %)", abs(f1 / C2 - 1) < 0.01 and abs(f2 / (2 * C2) - 1) < 0.01,
          "%.2f Hz, %.2f Hz" % (f1, f2))
    pk = float(np.abs(x[SR:]).max())
    check("level: rms over 0.08, peak under 1", rms(x, 1.5, 3.4) > 0.08 and pk < 1.0,
          "rms %.3f, peak %.3f" % (rms(x, 1.5, 3.4), pk))


def sc_vowel():
    print("vowel")
    (x, _) = run("vowel", 7, "gkdensity = 0\ngkwindow = 0\ngkloopstart = (kt < 4 ? 0 : 0.5)\n", alts=DRY)
    # bass "a": F1 600, F2 1040; "i": F1 250, F2 1750
    a_hi = env_db(x, 1.5, 3.9, 1550, 1950) - env_db(x, 1.5, 3.9, 900, 1200)
    i_hi = env_db(x, 4.5, 6.9, 1550, 1950) - env_db(x, 4.5, 6.9, 900, 1200)
    a_lo = env_db(x, 1.5, 3.9, 200, 300) - env_db(x, 1.5, 3.9, 500, 700)
    i_lo = env_db(x, 4.5, 6.9, 200, 300) - env_db(x, 4.5, 6.9, 500, 700)
    check("ee against ah: 2nd formant up (1.55-1.95 kHz over 0.9-1.2 kHz, +10 dB)", i_hi - a_hi > 10,
          "ah %+.1f dB, ee %+.1f dB" % (a_hi, i_hi))
    check("ee against ah: 1st formant down (200-300 Hz over 500-700 Hz, +10 dB)", i_lo - a_lo > 10,
          "ah %+.1f dB, ee %+.1f dB" % (a_lo, i_lo))


def sc_register():
    print("register")
    (x, _) = run("register", 11, "gkdensity = 0\ngkwindow = 0\n" + pulses(3.5, 6.0, 8.5, name="gkfilestate"),
                 alts=DRY)
    # the strongest harmonic between 350 Hz and 1 kHz follows formant 1 of "ah": bass 600, tenor 650, alto and
    # soprano 800 Hz (the centroid is ruled by the low harmonics and hardly moved)
    fs = [strongest(x, t, t + 1.8, 350, 1000) for t in (1.5, 4.0, 6.5, 9.0)]
    check("File: bass -> tenor -> alto -> soprano, formant 1 climbs (600 -> 800 Hz)",
          fs[0] < fs[1] <= fs[2] and fs[3] >= fs[2] and fs[3] > 1.2 * fs[0], " ".join("%.0f" % v for v in fs) + " Hz")


def sc_shift():
    print("shift")
    (x, _) = run("shift", 7, "gkdensity = 0\ngkwindow = 0\ngkloopsize = (kt < 4 ? 0.1 : 0.9)\n", alts=DRY)
    a, b = centroid(x, 1.5, 3.9), centroid(x, 4.5, 6.9)
    check("Size clockwise: the formants move up (centroid x1.2)", b > 1.2 * a, "%.0f -> %.0f Hz" % (a, b))


def strongest(x, t0, t1, lo, hi):
    f, sp = spectrum(x, t0, t1)
    m = (f > lo) & (f < hi)
    return float(f[m][np.argmax(sp[m])])


def spread_round(x, t0, t1, f0, n=4):
    """Energy-weighted spread (cents) round each of the first n harmonics' own centre (a single detuned voice is
    a narrow line, wherever it sits)."""
    f, sp = spectrum(x, t0, t1)
    out = []
    for h in range(1, n + 1):
        c = h * f0
        m = (f > c * 2 ** (-0.5 / 12)) & (f < c * 2 ** (0.5 / 12))
        cents = 1200 * np.log2(f[m] / c)
        p = sp[m] ** 2
        mu = (p * cents).sum() / p.sum()
        out.append(np.sqrt((p * (cents - mu) ** 2).sum() / p.sum()))
    return float(np.mean(out))


def sc_voices():
    print("voices")
    (x, _) = run("voices", 8, "gkwindow = 0.7\ngkdensity = (kt < 4.5 ? 0 : 1)\n", alts=DRY)
    a, b = spread_round(x, 1.5, 4.4, C2), spread_round(x, 5.0, 7.9, C2)
    la, lb = db(rms(x, 1.5, 4.4)), db(rms(x, 5.0, 7.9))
    check("Density 1: 8 voices spread round each harmonic (x1.5)", b > 1.5 * a, "%.1f -> %.1f cents" % (a, b))
    check("the level stays within 4 dB", abs(la - lb) < 4, "%.1f -> %.1f dB" % (la, lb))


def line(x, t0, t1, f0, bw=1.0):
    f, sp = spectrum(x, t0, t1)
    return float(db(sp[(f > f0 - bw) & (f < f0 + bw)].max()))


def sc_chord():
    print("chord")
    auto = "gkdensity = 0.43\ngkwindow = 0\ngksource = (kt > 4 ? 1 : 0)\n" + pulses(1.5)    # 4 voices; major
    (x, _) = run("chord", 8, auto, alts=DRY)
    e2 = C2 * 2 ** (4 / 12)
    off = line(x, 2.0, 3.9, e2) - line(x, 2.0, 3.9, C2)
    on = line(x, 5.0, 7.9, e2) - line(x, 5.0, 7.9, C2)
    check("Source + Reset (major): E2 sounds (its line against C2's)", on > -12 and off < -30,
          "off %.0f dB, on %.0f dB" % (off, on))


def env_change(x, a, b):
    bands = [(200, 400), (400, 700), (700, 1100), (1100, 1600), (1600, 2400), (2400, 3500)]
    va = np.array([env_db(x, a[0], a[1], lo, hi) for lo, hi in bands])
    vb = np.array([env_db(x, b[0], b[1], lo, hi) for lo, hi in bands])
    return float(np.max(np.abs((va - va.mean()) - (vb - vb.mean()))))


def sc_drift():
    print("drift")
    auto = ("gkdensity = 0\ngkwindow = 0\ngkloopstart = 0.4\n"
            "gkspeed = (kt < 10 ? 1 : 0.55)\ngkfreeze = (kt > 18 && kt < 26 ? 1 : 0)\n"
            "gkspeed = (kt > 18 ? 1 : gkspeed)\n")
    (x, _) = run("drift", 26, auto, alts=DRY)
    mv = max(env_change(x, (1.5, 3.0), (t, t + 1.5)) for t in (4.0, 6.0, 8.0))
    still = env_change(x, (12.5, 14.0), (15.5, 17.0))
    held = env_change(x, (19.0, 20.5), (23.5, 25.0))
    check("Speed past a click: the vowel wanders (formant bands move > 6 dB)", mv > 6, "%.1f dB" % mv)
    check("between the clicks: it holds (< 1.5 dB)", still < 1.5, "%.1f dB" % still)
    check("Freeze: it holds while Speed would move it (< 1.5 dB)", held < 1.5, "%.1f dB" % held)


def sc_breathe():
    print("breathe")
    auto = "gkdensity = 1\ngkrecord = (kt > 6 ? 1 : 0)\n"
    (x, _) = run("breathe", 22, auto, alts=DRY)
    w = int(0.1 * SR)

    def dips(t0, t1):
        s = seg(x, t0, t1)
        r = np.array([np.sqrt(np.mean(s[i:i + w] ** 2)) for i in range(0, len(s) - w, w)])
        return float(db(r.max()) - db(r.min()))
    a, b = dips(1.5, 5.9), dips(7.0, 21.9)
    check("Record: the voices take breaths (the level dips > 1.5 dB more)", b > a + 1.5, "%.1f -> %.1f dB" % (a, b))


def sc_breath():
    print("breath")
    (x, _) = run("breath", 7, "gkdensity = 0\ngkwindow = 0\ngkoverlap = (kt < 4 ? 0 : 1)\n", alts=DRY)

    def floor(t0, t1):
        f, sp = spectrum(x, t0, t1)
        mids = [(h + 0.5) * C2 for h in range(8, 20)]
        return float(np.mean([db(sp[(f > m - 3) & (f < m + 3)].mean()) for m in mids]))
    a, b = floor(1.5, 3.9), floor(4.5, 6.9)
    check("Overlap: air between the harmonics (+15 dB)", b - a > 15, "%+.1f dB" % (b - a))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkrecord = (frac(kt / 15) > 0.5 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.5 ? 1 : 0)\n"
            "gkfreeze = (frac(kt / 7) > 0.6 ? 1 : 0)\ngkreset = (frac(kt * 0.7) < 0.03 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.3) < 0.03 ? 1 : 0)\n"
            "gkloopsize_alt = frac(kt * 0.05)\ngkloopstart_alt = frac(kt * 0.06)\ngkblend_alt = 0.6\n")
    (x, cpu) = run("sweep", 62, auto)
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "silence.wav"), "looper")
    print("  CPU for 62 s: chorale %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.8x the factory looper", cpu < 1.8 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 5, BASE + "gkdensity = 0\ngkwindow = 0\n", sets=DRY, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "5", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f1 = fundamental(x, 1.5, 4.5)
    check("6.09: compiles, sings at C2", ok and abs(f1 / C2 - 1) < 0.01 and rms(x, 1.5, 4.5) > 0.05,
          "%.2f Hz, rms %.3f" % (f1, rms(x, 1.5, 4.5)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["pitch", "vowel", "register", "shift", "voices", "chord", "drift", "breathe", "breath",
                            "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
