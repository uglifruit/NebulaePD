#!/usr/bin/env python3
"""Offline tests of instr/pulsar.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609, from
Windows Python).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/pulsar_sim.py [scenario ...]
  python tools/pulsar_sim.py m609

  pitch    drone at the Pitch click = C3 harmonics; Pitch 0.8 = C4
  formant  formant 1 at 1 kHz / 2.5 kHz: the strongest harmonic sits there, and stays there when the pitch moves
  track    Freeze on: the formant follows the pitch (the strongest harmonic number stays the same)
  duty     Size: a short duty cycle spreads the spectrum wider than a long one
  mask     alt Pitch = a 2 Hz pulse rhythm: Density 1 = every pulse, 0.5 = about half, 0 = none
  pluck    Record on: silent until Reset, a note, then it decays (alt Window)
  sync     Reset restarts the pulse train (a 2 Hz train: a pulse right after each Reset)
  chirp    Speed fully CW: each (long) grain sweeps up 2 octaves; CCW down
  file     File: sine -> saw changes the spectrum; Source: the live input becomes the pulsaret
  fm       Overlap: FM widens the spectrum
  stereo   alt Density: grains alternate left / right
  sweep    every knob at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609     Csound 6.09.1: compiles, the drone sounds at C3
Renders go to firmware/dist/pulsar_sim/.
"""
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "pulsar_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "pulsar.instr")
SR = 48000
BASE = ("gkspeed = 0.5\ngkloopstart = 0.5255\ngkloopsize = 0.35\ngkdensity = 1\ngkwindow = 0.5\n"
        "gkoverlap = 0\ngkblend = 1\ngkpitch = 0.6\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\n")
ALTS = "start_alt=0.4 size_alt=0 density_alt=0 window_alt=0.5 overlap_alt=0.5 blend_alt=0 pitch_alt=0"
RESULTS = []
C3 = 130.8128


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
    t = np.arange(n) / SR
    tone = 0.4 * np.sin(2 * np.pi * 660 * t)
    stereo(os.path.join(OUT, "tone.wav"), tone, tone)
    rng = np.random.default_rng(2)
    nz = 0.3 * rng.standard_normal(n)
    stereo(os.path.join(OUT, "noise.wav"), nz, nz)
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def pulses_at(*ts, name="gkreset"):
    return name + " = (" + " || ".join("(kt > %g && kt < %g)" % (t, t + 0.01) for t in ts) + " ? 1 : 0)\n"


def run(name, secs, auto, live="silence.wav", alts=ALTS):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=alts, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, live), name)


def seg(x, t0, t1, ch=0):
    return x[int(t0 * SR):int(t1 * SR), ch]


def rms(x, t0, t1, ch=0):
    s = seg(x, t0, t1, ch)
    return float(np.sqrt(np.mean(s ** 2)))


def spectrum(x, t0, t1, ch=0):
    s = seg(x, t0, t1, ch)
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)), 1 << 17))
    return np.fft.rfftfreq(1 << 17, 1 / SR), sp


def fundamental(x, t0, t1):
    """The harmonic spacing: the strongest peak of the spectrum's autocorrelation, 50 .. 1000 Hz."""
    f, sp = spectrum(x, t0, t1)
    df = f[1]
    m = sp[(f > 30) & (f < 8000)]
    ac = np.correlate(m, m, "full")[len(m) - 1:]
    lo, hi = int(50 / df), int(1000 / df)
    k = lo + int(np.argmax(ac[lo:hi]))
    # refine: the first strong partial near a multiple of that spacing
    return k * df


def strongest(x, t0, t1):
    f, sp = spectrum(x, t0, t1)
    m = (f > 50) & (f < 10000)
    return float(f[m][np.argmax(sp[m])])


def spread(x, t0, t1):
    f, sp = spectrum(x, t0, t1)
    p = sp ** 2
    c = (p * f).sum() / p.sum()
    return float(np.sqrt((p * (f - c) ** 2).sum() / p.sum()))


def onsets(x, t0, t1, thr=0.05):
    s = np.abs(seg(x, t0, t1))
    w = int(0.002 * SR)
    e = np.convolve(s, np.ones(w) / w, "same")
    on = np.flatnonzero((e[1:] > thr * e.max()) & (e[:-1] <= thr * e.max()))
    out = []
    for i in on:
        if not out or i - out[-1] > 0.1 * SR:
            out.append(i)
    return [t0 + i / SR for i in out]


def sc_pitch():
    print("pitch")
    (x, _) = run("pitch", 6, "gkpitch = (kt < 3 ? 0.6 : 0.8)\n")
    f1, f2 = fundamental(x, 1.0, 2.8), fundamental(x, 4.0, 5.8)
    check("drone at C3 (click), C4 at Pitch 0.8 (within 1 %)", abs(f1 / C3 - 1) < 0.01 and abs(f2 / (2 * C3) - 1) < 0.01,
          "%.1f Hz, %.1f Hz" % (f1, f2))
    pk = float(np.abs(x[SR:]).max())
    check("level: rms over 0.12, peak under 1", 0.12 < rms(x, 1, 2.8) and pk < 1.0,
          "rms %.3f, peak %.3f" % (rms(x, 1, 2.8), pk))


def sc_formant():
    print("formant")
    s25 = np.log(2500 / 100) / 4.382
    # Size 0.7 = duty 0.35: grains a few formant cycles long (at the default duty a 1 kHz grain is under one
    # cycle, and its spectrum has no clear peak)
    (x, _) = run("formant", 9, "gkloopsize = 0.7\ngkloopstart = (kt < 3 ? 0.5255 : %g)\n"
                 "gkpitch = (kt < 6 ? 0.6 : 0.65)\n" % s25)
    a, b, c = strongest(x, 1, 2.8), strongest(x, 4, 5.8), strongest(x, 7, 8.8)
    check("formant 1 kHz: strongest partial within a harmonic of 1 kHz", abs(a - 1000) < C3, "%.0f Hz" % a)
    check("formant 2.5 kHz: within a harmonic", abs(b - 2500) < C3, "%.0f Hz" % b)
    check("Pitch up a fifth: the formant stays (within a harmonic of 2.5 kHz)", abs(c - 2500) < C3 * 1.5,
          "%.0f Hz" % c)


def sc_track():
    print("track")
    (x, _) = run("track", 6, "gkfreeze = 1\ngkloopstart = 0.4\ngkpitch = (kt < 3 ? 0.6 : 0.8)\n")
    r = 0.5 * np.exp(0.4 * 3.4657)
    a, b = strongest(x, 1, 2.8) / C3, strongest(x, 4, 5.8) / (2 * C3)
    check("Freeze on: formant = %.1fx the pitch; the strongest harmonic number stays" % r,
          round(a) == round(b) and abs(a - r) < 1.5, "harmonic %.2f, then %.2f" % (a, b))


def sc_duty():
    print("duty")
    (x, _) = run("duty", 6, "gkloopsize = (kt < 3 ? 0.05 : 0.95)\n")
    a, b = spread(x, 1, 2.8), spread(x, 4, 5.8)
    check("short duty spreads the spectrum wider than long (x1.5)", a > 1.5 * b, "%.0f Hz vs %.0f Hz" % (a, b))


def sc_mask():
    print("mask")
    alts = ALTS.replace("pitch_alt=0", "pitch_alt=0.75")       # 6 octaves down: 2.04 Hz
    (x, _) = run("mask", 31, "gkdensity = (kt < 11 ? 1 : (kt < 21 ? 0.5 : 0))\ngkloopsize = 0.2\n", alts=alts)
    n1, n2, n3 = len(onsets(x, 1, 11)), len(onsets(x, 11, 21)), len(onsets(x, 21.5, 31))
    check("Density 1: every pulse (about 20 in 10 s)", 19 <= n1 <= 21, str(n1))
    check("Density 0.5: about half (6 .. 14)", 6 <= n2 <= 14, str(n2))
    check("Density 0: none", n3 == 0 and rms(x, 21.5, 31) < 1e-4, "%d, rms %.5f" % (n3, rms(x, 21.5, 31)))


def sc_pluck():
    print("pluck")
    (x, _) = run("pluck", 8, "gkrecord = 1\n" + pulses_at(3.0), alts=ALTS.replace("window_alt=0.5", "window_alt=0.4"))
    # alt Window 0.4 = a 0.17 s decay (to -60 dB)
    a0, a1, a2 = rms(x, 1.5, 2.9), rms(x, 3.0, 3.05), rms(x, 6.5, 7.5)
    check("Record on: silent, a note on Reset, then decays", a0 < 1e-4 and a1 > 0.05 and a2 < 0.01 * a1,
          "%.5f, %.3f, %.5f" % (a0, a1, a2))


def sc_sync():
    print("sync")
    alts = ALTS.replace("pitch_alt=0", "pitch_alt=0.75")
    ts = [3.13, 4.71, 6.37]
    # Window fully CW: a sharp grain attack, so the onset shows where the grain starts
    (x, _) = run("sync", 8, pulses_at(*ts) + "gkloopsize = 0.1\ngkwindow = 1\n", alts=alts)
    on = onsets(x, 2.5, 7.9)
    near = [min(abs(o - t) for o in on) for t in ts]
    check("a pulse within 5 ms of each Reset", max(near) < 0.005, " ".join("%.1f ms" % (1000 * v) for v in near))


def inst_freq(x, t0, t1):
    s = seg(x, t0, t1)
    zc = np.flatnonzero((s[1:] > 0) & (s[:-1] <= 0))
    return SR / np.mean(np.diff(zc)) if len(zc) > 3 else 0.0


def sc_chirp():
    print("chirp")
    alts = ALTS.replace("pitch_alt=0", "pitch_alt=0.75")      # 2.04 Hz, duty 1: grains ~490 ms
    auto = ("gkloopsize = 1\ngkwindow = 0.0\ngkloopstart = 0.5255\n" + pulses_at(2.0, 6.0)
            + "gkspeed = (kt < 5 ? 1 : 0)\n")
    (x, _) = run("chirp", 9, auto, alts=alts)
    up = inst_freq(x, 2.43, 2.47) / inst_freq(x, 2.03, 2.07)
    dn = inst_freq(x, 6.43, 6.47) / inst_freq(x, 6.03, 6.07)
    check("Speed CW: a grain sweeps up (end / start > 2.5)", up > 2.5, "%.2f" % up)
    check("Speed CCW: down (< 0.4)", dn < 0.4, "%.2f" % dn)


def sc_file():
    print("file")
    (x, _) = run("file", 7, pulses_at(3.0, name="gkfilestate") + "gkloopsize = 0.5\n")
    a, b = spread(x, 1, 2.8), spread(x, 4, 6.8)
    check("File: sine -> saw changes the spectrum (spread x1.3)", b > 1.3 * a, "%.0f -> %.0f Hz" % (a, b))
    (y, _) = run("source", 7, "gksource = (kt > 3 ? 1 : 0)\ngkloopsize = 1\ngkloopstart = 0.5\n", live="tone.wav")
    f, sp = spectrum(y, 4, 6.8)
    band = sp[(f > 600) & (f < 720)].sum() / sp[(f > 50) & (f < 5000)].sum()
    check("Source: the live 660 Hz tone becomes the pulsaret (most energy around 660 Hz)", band > 0.4,
          "%.0f %% in 600-720 Hz, rms %.3f" % (100 * band, rms(y, 4, 6.8)))


def sc_fm():
    print("fm")
    (x, _) = run("fm", 6, "gkoverlap = (kt < 3 ? 0 : 1)\n")
    a, b = spread(x, 1, 2.8), spread(x, 4, 5.8)
    check("Overlap: FM widens the spectrum (x1.3)", b > 1.3 * a, "%.0f -> %.0f Hz" % (a, b))


def sc_stereo():
    print("stereo")
    alts = ALTS.replace("density_alt=0", "density_alt=1").replace("pitch_alt=0", "pitch_alt=0.75")
    (x, _) = run("stereo", 6, "gkloopsize = 0.2\n", alts=alts)
    l, r = seg(x, 1, 5.8, 0), seg(x, 1, 5.8, 1)
    c = float(np.corrcoef(l, r)[0, 1])
    check("alt Density 1: grains alternate left / right (correlation < 0.2)", c < 0.2 and rms(x, 1, 5.8, 1) > 0.01,
          "%.2f" % c)


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkrecord = (frac(kt / 15) > 0.5 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.5 ? 1 : 0)\n"
            "gkfreeze = (frac(kt / 7) > 0.5 ? 1 : 0)\ngkfilestate = (frac(kt / 3) > 0.9 ? 1 : 0)\n"
            "gkreset = (frac(kt * 3) < 0.02 ? 1 : 0)\ngkpitch_alt = (kt > 40 ? frac(kt * 0.1) : 0)\n"
            "gkloopsize_alt = frac(kt * 0.05)\ngkdensity_alt = frac(kt * 0.06)\ngkblend_alt = 0.5\n")
    (x, cpu) = run("sweep", 62, auto, live="noise.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "noise.wav"), "looper")
    print("  CPU for 62 s: pulsar %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.8x the factory looper", cpu < 1.8 * cpul, "%.2fx" % (cpu / cpul))
    # the default (a C3 drone, duty 0.35) on its own
    (_, cpud) = run("cpu_default", 62, "")
    print("  CPU for 62 s at the defaults: %.1f s (%.2fx the looper)" % (cpud, cpud / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 5, BASE, sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "5", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f1 = fundamental(x, 1.0, 4.5)
    check("6.09: compiles, the drone sounds at C3", ok and rms(x, 1, 4.5) > 0.05 and abs(f1 / C3 - 1) < 0.01,
          "rms %.3f, %.1f Hz" % (rms(x, 1, 4.5), f1))


def main():
    make_inputs()
    want = sys.argv[1:] or ["pitch", "formant", "track", "duty", "mask", "pluck", "sync", "chirp", "file", "fm",
                            "stereo", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
