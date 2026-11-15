#!/usr/bin/env python3
"""Offline tests of instr/cauldron.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/cauldron_sim.py [scenario ...]
  python tools/cauldron_sim.py m609

  pitch     Time on Pitch, 1V/oct: a click rings at 50 Hz at the click, 100 Hz an octave up
  echo      File (the long range): a burst echoes 160 ms later at the click
  decay     Decay: a handful of repeats -> for ever
  filter    Filter darkens, Absorb thins the lows (noise in)
  level     Start: more input into the experiment
  wow       Record (Wow & Flutter): the activity bends the echoes' pitch
  noise     Source (Noise): interference shakes Absorb
  wind      Reset (Wind & Wave): with a slow clock it feeds itself (from silence, its own noise grows)
  hold      Freeze: rings on, takes nothing new
  speed     Speed: steady between the clicks, the echoes wobble past them
  reverb    alt Blend: a stereo reverb
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles, the click rings at 50 Hz
Renders go to firmware/dist/cauldron_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "cauldron_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "cauldron.instr")
SR = 48000
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0.5\ngkloopsize = 0.7\ngkdensity = 0.5\ngkwindow = 0.9\n"
        "gkoverlap = 0.05\ngkblend = 1\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\ngkreset = 0\n")
ALTS = "window_alt=0.6 blend_alt=0"
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    import wave
    n = 70 * SR
    t = np.arange(n) / SR
    rng = np.random.default_rng(5)
    click = np.zeros(n)
    for c in (1.5, 4.5):
        click[int(c * SR):int(c * SR) + 24] = 0.8
    burst = 0.4 * np.sin(2 * np.pi * 300 * t) * ((t > 1.5) & (t < 1.53))
    sigs = {"in_silence.wav": np.zeros(n), "in_click.wav": click, "in_burst.wav": burst,
            "in_sine.wav": 0.3 * np.sin(2 * np.pi * 440 * t), "in_noise.wav": 0.1 * rng.standard_normal(n),
            "in_late.wav": burst + 0.3 * np.sin(2 * np.pi * 440 * t) * (t > 3)}
    for name, sig in sigs.items():
        with wave.open(os.path.join(OUT, name), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(np.stack([sig, sig], 1), -1, 1) * 32767).astype("<i2").tobytes())
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def run(name, secs, auto, alts=ALTS, wav="in_silence.wav"):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=alts, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, wav), name)


def near_peak(x, t0, t1, f0, tol=0.06):
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


def offline(x, t0, t1, f0):
    """Energy away from f0 and its harmonics, against on them (dB): pitch wobble spreads it."""
    f, p = psd(x, t0, t1, n=16384)
    m = (f > 100) & (f < 6000)
    k = np.abs(f / f0 - np.round(f / f0)) < 0.01
    return float(10 * np.log10(np.sum(p[m & ~k]) / np.sum(p[m & k])))


def sc_pitch():
    print("pitch")
    # (separate runs: changing Time while the loop rings carries the old ring along, Doppler-shifted)
    got = []
    for name, p, want in (("pitch0", 0.6, 50.0), ("pitch1", 0.8, 100.0), ("pitch2", 1.0, 200.0)):
        (x, _) = run(name, 4, "gkdensity = 0.97" + chr(10) + "gkpitch = %g" % p + chr(10), wav="in_click.wav")
        got.append((near_peak(x, 1.6, 3.9, want)[0], want))
    check("a click rings at 1 / Time: 50 Hz at the click, 100 Hz and 200 Hz up (within 2 %)",
          all(abs(g / w - 1) < 0.02 for g, w in got), ", ".join("%.2f" % g for g, _ in got) + " Hz")


def sc_echo():
    print("echo")
    auto = "gkdensity = 0.5\n" + pulses(1.1, name="gkfilestate")
    (x, _) = run("echo", 3.5, auto, wav="in_burst.wav")
    s = np.abs(seg(x, 1.5, 3.4))
    w = int(0.004 * SR)
    e = np.convolve(s, np.ones(w) / w, "same")
    e = e - e.mean()
    ac = np.correlate(e, e, "full")[len(e) - 1:]
    lo, hi_ = int(0.08 * SR), int(0.4 * SR)
    lag = (lo + int(np.argmax(ac[lo:hi_]))) / SR
    check("File (long range): echoes 160 ms apart at the click (within 5 %)", abs(lag / 0.16 - 1) < 0.05,
          "%.3f s" % lag)


def sc_decay():
    print("decay")
    auto = pulses(1.1, name="gkfilestate")
    (x, _) = run("decay0", 7, auto + "gkdensity = 0.3\n", wav="in_burst.wav")
    (y, _) = run("decay1", 7, auto + "gkdensity = 1\n", wav="in_burst.wav")
    ref = db(rms(y, 1.6, 2.0))
    a, b = db(rms(x, 5.5, 6.9)), db(rms(y, 5.5, 6.9))
    check("Decay: gone in a few repeats -> still ringing 4 s later (> -15 dB of its start)",
          a < ref - 40 and b > ref - 15, "low %.1f, full %.1f dB (start %.1f)" % (a, b, ref))


def sc_filter():
    print("filter")
    (x, _) = run("filt", 7, steps("gkwindow", (0, 0.9), (4, 0.3)), wav="in_noise.wav")
    a, b = hi(x, 2, 3.9), hi(x, 5, 6.9)
    check("Filter: darker anticlockwise (the share above 1 kHz down > 15 dB)", a - b > 15, "%+.1f -> %+.1f dB" % (a, b))
    (y, _) = run("absorb", 7, steps("gkoverlap", (0, 0), (4, 0.9)), wav="in_noise.wav")
    l0 = -hi(y, 2, 3.9, lo=300)
    l1 = -hi(y, 5, 6.9, lo=300)
    f, p = psd(y, 2, 3.9)
    a0 = band(f, p, 40, 250) / band(f, p, 40, 10000)
    f, p = psd(y, 5, 6.9)
    a1 = band(f, p, 40, 250) / band(f, p, 40, 10000)
    check("Absorb: the lows thin out (40-250 Hz share down > 10 dB)", 10 * np.log10(a0 / a1) > 10,
          "%+.1f dB" % (10 * np.log10(a1 / a0)))


def sc_level():
    print("level")
    (x, _) = run("level", 7, "gkblend = 1\ngkdensity = 0.3\n" + steps("gkloopstart", (0, 0), (4, 1)),
                 wav="in_noise.wav")
    a, b = db(rms(x, 2, 3.9)), db(rms(x, 5, 6.9))
    check("Start: more input into the experiment (> 15 dB louder fully clockwise)", b - a > 15, "%.1f -> %.1f dB" % (a, b))


def sc_wow():
    print("wow")
    auto = "gkdensity = 0.75\ngkloopsize = 1\ngkpitch = 0.45\n"
    (x, _) = run("wow0", 6, auto, wav="in_sine.wav")
    (y, _) = run("wow1", 6, auto + "gkrecord = 1\n", wav="in_sine.wav")
    a, b = offline(x, 2, 5.9, 440), offline(y, 2, 5.9, 440)
    check("Record (Wow & Flutter): the echoes' pitch bends (energy off 440 Hz > 6 dB up)", b - a > 6,
          "%+.1f -> %+.1f dB" % (a, b))


def sc_noise():
    print("noise")
    auto = "gkdensity = 0.75\ngkloopsize = 1\ngkoverlap = 0.4\n"
    (x, _) = run("noi0", 6, auto, wav="in_sine.wav")
    (y, _) = run("noi1", 6, auto + "gksource = 1\n", wav="in_sine.wav")
    a, b = offline(x, 2, 5.9, 440), offline(y, 2, 5.9, 440)
    check("Source (Noise): interference shakes Absorb (energy off 440 Hz > 6 dB up)", b - a > 6,
          "%+.1f -> %+.1f dB" % (a, b))


def sc_wind():
    print("wind")
    # the long range at Pitch 0.4: Time 0.32 s, a slow (3.2 kHz) clock with its own noise
    auto = ("gkdensity = 0.85\ngkloopsize = 1\ngkpitch = 0.4\n" + pulses(1.1, name="gkfilestate") +
            "gkreset = (kt > 5 ? 1 : 0)\n")
    (x, _) = run("wind", 10, auto)
    a, b = db(rms(x, 3, 4.9)), db(rms(x, 8, 9.9))
    check("Reset (Wind & Wave): from silence, a slow clock feeds itself (> 15 dB up)", b - a > 15,
          "%.1f -> %.1f dB" % (a, b))


def sc_hold():
    print("hold")
    auto = "gkdensity = 0.4\ngkfreeze = (kt > 1.6 ? 1 : 0)\n" + pulses(1.1, name="gkfilestate")
    (x, _) = run("hold", 7, auto, wav="in_burst.wav")
    a, b = db(rms(x, 1.6, 2.0)), db(rms(x, 6, 6.9))
    check("Freeze: rings on (> -15 dB of its start 4.5 s later, at a low Decay)", b > a - 15, "%.1f -> %.1f dB" % (a, b))
    # a 300 Hz burst at 1.5 s, the hold from 2 s, a 440 Hz sine from 3 s: the 440 must stay out
    (y, _) = run("hold_in", 7, "gkfreeze = (kt > 2 ? 1 : 0)" + chr(10), wav="in_late.wav")
    (z, _) = run("hold_in0", 7, "", wav="in_late.wav")
    d = near_peak(y, 4, 6.9, 440, tol=0.01)[1] - near_peak(z, 4, 6.9, 440, tol=0.01)[1]
    check("and takes nothing new (a sine arriving after the hold: > 30 dB under the same run unheld)", d < -30,
          "%+.1f dB" % d)


def sc_speed():
    print("speed")
    auto = "gkdensity = 0.75\ngkloopsize = 0\ngkpitch = 0.45\n"
    (x, _) = run("spd0", 6, auto, wav="in_sine.wav")
    (y, _) = run("spd1", 6, auto + "gkspeed = 0.85\n", wav="in_sine.wav")
    a, b = offline(x, 2, 5.9, 440), offline(y, 2, 5.9, 440)
    check("Speed: past the click the echoes wobble (energy off 440 Hz > 6 dB up)", b - a > 6,
          "%+.1f -> %+.1f dB" % (a, b))


def sc_reverb():
    print("reverb")
    (x, _) = run("rev0", 5, "", wav="in_noise.wav")
    (y, _) = run("rev1", 5, "", alts="window_alt=0.6 blend_alt=1", wav="in_noise.wav")

    def tail_corr(z):
        return float(np.corrcoef(seg(z, 2, 4.9, 0), seg(z, 2, 4.9, 1))[0, 1])
    a, b = tail_corr(x), tail_corr(y)
    check("alt Blend: a stereo reverb (L/R correlation drops by > 0.1)", a - b > 0.1, "%.3f -> %.3f" % (a, b))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkblend = frac(kt * 0.04)\n"
            "gkrecord = (frac(kt * 0.07) > 0.5 ? 1 : 0)\ngkfreeze = (frac(kt * 0.045) > 0.8 ? 1 : 0)\n"
            "gksource = (frac(kt / 11) > 0.5 ? 1 : 0)\ngkreset = (frac(kt / 13) > 0.5 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.1) < 0.02 ? 1 : 0)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkblend_alt = frac(kt * 0.02)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_noise.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_noise.wav"), "looper")
    print("  CPU for 62 s: cauldron %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper (with the reverb)", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    out = os.path.join(OUT, "m609.wav")
    csd = S.make_csd(INSTR, "m609", 4, BASE + "gkdensity = 0.97\n", sets=ALTS, wav="dummy.wav")
    # (the wasm harness has no live input: the click comes from the automation, into the experiment's input bus)
    src = open(csd).read().replace("ain, ainr inch 1, 2", "ain = (timeinsts() > 0.5 && timeinsts() < 0.5006 ? 0.8 : 0)\nainr = ain"
                                   if False else "ain, ainr inch 1, 2")
    open(csd, "w").write(src)
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "4", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    check("6.09: compiles and runs (no NaN; no input here, so silence is right)", ok and not np.isnan(x).any(),
          "peak %.4f" % float(np.abs(x).max()))


def main():
    make_inputs()
    want = sys.argv[1:] or ["pitch", "echo", "decay", "filter", "level", "wow", "noise", "wind", "hold", "speed",
                            "reverb", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
