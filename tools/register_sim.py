#!/usr/bin/env python3
"""Offline tests of instr/register.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/register_sim.py [scenario ...]
  python tools/register_sim.py m609

  pitch     the shortest register (a 3-step cycle) sounds at clock / 3: 1395.3 Hz at the click, 1V/oct
  range     File: noise -> tone (/16) -> pattern (/256)
  length    Start: short = a pitched cycle, long = noise
  chance    Overlap: 0 = the register's own repeating sequence, up = random
  lock      Freeze: a random register locks into a loop of Start's length
  divide    Density: /8 is lower and chunkier than the raw bits
  filter    Size: cutoff up; Window: a resonant peak at the cutoff
  steps     Source: the register's value steps the cutoff
  extclock  Reset gates step the register (and nothing else does); Pitch takes over 2 s later
  stereo    Record: the right channel gets its own register
  motion    Speed: still between the clicks, wandering past them
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles, the 3-step cycle at 1395.3 Hz
Renders go to firmware/dist/register_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "register_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "register.instr")
SR = 48000
CLK = 4186.009
# Start for a given length: klen = int(2 + 22 * Start^1.5 + 0.5)
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0\ngkloopsize = 1\ngkdensity = 0\ngkwindow = 0\n"
        "gkoverlap = 0\ngkblend = 1\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\n")
ALTS = "start_alt=0.5 size_alt=0.3 density_alt=0 window_alt=0.5 overlap_alt=0 blend_alt=0.5 pitch_alt=0"
RESULTS = []


def start_for(n):
    return ((n - 2) / 22.0) ** (1 / 1.5)


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


def strongest(x, t0, t1, lo=10, hi=20000, ch=None):
    s = seg(x, t0, t1, ch)
    n = 1 << 19
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)), n))
    f = np.fft.rfftfreq(n, 1 / SR)
    m = np.flatnonzero((f > lo) & (f < hi))
    i = m[np.argmax(sp[m])]
    a, b, c = np.log(sp[i - 1:i + 2] + 1e-20)
    return float(f[i] + 0.5 * (a - c) / (a - 2 * b + c) * (f[1] - f[0]))


def flatness(x, t0, t1):
    f, p = psd(x, t0, t1)
    m = (f > 100) & (f < 10000)
    q = p[m] + 1e-20
    return float(np.exp(np.mean(np.log(q))) / np.mean(q))


def centroid(x, t0, t1, n=8192):
    f, p = psd(x, t0, t1, n=n)
    m = (f > 20) & (f < 16000)
    return float(np.sum(f[m] * p[m]) / np.sum(p[m]))


def autocorr(x, t0, t1, lag):
    s = seg(x, t0, t1)
    s = s - s.mean()
    a, b = s[:-lag], s[lag:]
    return float(np.sum(a * b) / np.sqrt(np.sum(a * a) * np.sum(b * b)))


def sc_pitch():
    print("pitch")
    (x, _) = run("pitch", 7, steps("gkpitch", (0, 0.6), (4, 0.4)))
    a, b = strongest(x, 1.5, 3.9), strongest(x, 4.5, 6.9)
    check("a 3-step cycle at clock / 3: 1395.3 Hz at the click, 697.7 an octave down (within 0.3 %)",
          abs(a / (CLK / 3) - 1) < 0.003 and abs(b / (CLK / 6) - 1) < 0.003, "%.1f, %.1f Hz" % (a, b))


def sc_range():
    print("range")
    (x, _) = run("range", 9, pulses(4.0, name="gkfilestate"))
    (y, _) = run("range2", 9, pulses(4.0, 4.2, name="gkfilestate"))
    a = strongest(x, 5, 8.9, hi=5000)
    b = strongest(y, 5, 8.9, lo=2, hi=200)
    check("File: tone range = /16 (87.2 Hz), pattern = /256 (5.45 Hz) for the 3-step cycle (within 1 %)",
          abs(a / (CLK / 48) - 1) < 0.01 and abs(b / (CLK / 768) - 1) < 0.01, "%.2f, %.2f Hz" % (a, b))


def sc_length():
    print("length")
    (x, _) = run("length", 7, steps("gkloopstart", (0, 0), (4, 1)))
    a, b = flatness(x, 1.5, 3.9), flatness(x, 4.5, 6.9)
    # (clocked at 4.2 kHz, the noise is stepped: its spectrum dips at each multiple of the clock, so not flat)
    check("Start: short = pitched (flatness < 0.01), long = noise (> 0.1)", a < 0.01 and b > 0.1,
          "%.3f -> %.3f" % (a, b))


def sc_chance():
    print("chance")
    # a 4-bit register: its own sequence repeats every 15 steps; tone range clock 261.6 Hz -> period 57.3 ms
    lag = int(round(SR * 15 / (CLK / 16)))
    auto = ("gkloopstart = %g\n" % start_for(4) + pulses(1.1, name="gkfilestate") +
            steps("gkoverlap", (0, 0), (5, 1)))
    (x, _) = run("chance", 9, auto)
    a, b = autocorr(x, 2, 4.9, lag), autocorr(x, 6, 8.9, lag)
    check("Overlap 0: repeats every 15 steps (autocorrelation > 0.9); Overlap 1: random (< 0.3)",
          a > 0.9 and b < 0.3, "%.2f -> %.2f" % (a, b))


def sc_lock():
    print("lock")
    n = 8
    lag = int(round(SR * n / (CLK / 16)))
    auto = ("gkloopstart = %g\ngkoverlap = 1\n" % start_for(n) + pulses(1.1, name="gkfilestate") +
            "gkfreeze = (kt > 5 ? 1 : 0)\n")
    (x, _) = run("lock", 9, auto)
    a, b = autocorr(x, 2, 4.9, lag), autocorr(x, 5.5, 8.9, lag)
    check("Freeze: a random 8-bit register locks into an 8-step loop (autocorrelation < 0.3 -> > 0.9)",
          a < 0.3 and b > 0.9, "%.2f -> %.2f" % (a, b))


def sc_divide():
    print("divide")
    (x, _) = run("divide", 7, "gkloopstart = 1\n" + steps("gkdensity", (0, 0), (4, 1)))
    a, b = centroid(x, 1.5, 3.9), centroid(x, 4.5, 6.9)
    check("Density: /8 lower than the raw bits (centroid / 3)", b < a / 3, "%.0f -> %.0f Hz" % (a, b))


def sc_filter():
    print("filter")
    (x, _) = run("filter", 7, "gkloopstart = 1\n" + steps("gkloopsize", (0, 0.3), (4, 0.8)))
    a, b = centroid(x, 1.5, 3.9), centroid(x, 4.5, 6.9)
    check("Size: cutoff up (centroid x4)", b > 4 * a, "%.0f -> %.0f Hz" % (a, b))
    fc = 40 * 400 ** 0.6
    (y, _) = run("reso", 7, "gkloopstart = 1\ngkloopsize = 0.6\n" + steps("gkwindow", (0, 0), (4, 0.9)))

    def peak(z, t0, t1):
        f, p = psd(z, t0, t1)
        return 10 * np.log10(band(f, p, fc * 0.85, fc * 1.15) / band(f, p, fc * 0.3, fc * 0.5))
    pa, pb = peak(y, 1.5, 3.9), peak(y, 4.5, 6.9)
    check("Window: a resonant peak at the cutoff (> 8 dB more, and > 6 dB over the passband)", pb - pa > 8 and pb > 6,
          "%+.1f -> %+.1f dB" % (pa, pb))


def sc_steps():
    print("steps")
    # pattern range (clock 16.4 Hz): Source makes the cutoff step with the register
    # high resonance: each bit change rings the filter at its cutoff, so the ring's pitch per step shows the cutoff
    auto = ("gkloopstart = 1\ngkloopsize = 0.55\ngkwindow = 0.85\n" + pulses(1.1, 1.3, name="gkfilestate") +
            "gksource = (kt > 6 ? 1 : 0)\n")
    (x, _) = run("steps", 11, auto, alts=ALTS.replace("start_alt=0.5", "start_alt=1"))
    a = [strongest(x, t, t + 0.058, lo=60, hi=8000) for t in np.arange(2.5, 5.8, 0.061)]
    b = [strongest(x, t, t + 0.058, lo=60, hi=8000) for t in np.arange(7, 10.8, 0.061)]
    sa, sb = np.std(np.log2(a)), np.std(np.log2(b))
    check("Source: the cutoff steps with the register (the ring's pitch: sd < 0.1 -> > 0.3 octave)",
          sa < 0.1 and sb > 0.3, "%.2f -> %.2f octave" % (sa, sb))


def sc_extclock():
    print("extclock")
    ts = [3.0 + 0.4 * k for k in range(8)]
    # (the 2-bit register: 1 1 0 repeating, so two of every three steps show as a jump)
    auto = ("gkloopstart = 0\ngkloopsize = 1\n" + pulses(1.1, 1.3, name="gkfilestate") + pulses(*ts))
    (x, _) = run("extclock", 9, auto)
    s = seg(x, 0, 9)
    d = np.abs(np.diff(s))
    ev = np.flatnonzero(d > 0.3) / SR
    clocked = [e for e in ev if 2.95 < e < 6.0]
    stray = [e for e in clocked if min(abs(e - t) for t in ts) > 0.05]
    late = [e for e in ev if 7.2 < e < 8.9]
    check("Reset gates step it: steps only at the gates (within 50 ms), then Pitch's clock again after 2 s",
          len(clocked) >= 3 and not stray and len(late) >= 10,
          "%d steps at gates, %d stray, %d steps after 7.2 s" % (len(clocked), len(stray), len(late)))


def sc_stereo():
    print("stereo")
    (x, _) = run("stereo", 7, "gkloopstart = 1\ngkrecord = (kt > 4 ? 1 : 0)\n")

    def corr(t0, t1):
        a, b = seg(x, t0, t1, 0), seg(x, t0, t1, 1)
        return float(np.corrcoef(a, b)[0, 1])
    a, b = corr(1.5, 3.9), corr(4.5, 6.9)
    check("Record: the right channel its own (L/R correlation 1 -> < 0.3)", a > 0.99 and b < 0.3,
          "%.2f -> %.2f" % (a, b))


def sc_motion():
    print("motion")
    (x, _) = run("motion", 12, steps("gkspeed", (0, 0.5), (5, 0.95)))
    a = [strongest(x, t, t + 0.25) for t in np.arange(1.5, 4.7, 0.25)]
    b = [strongest(x, t, t + 0.25) for t in np.arange(6, 11.7, 0.25)]
    sa, sb = np.std(np.log2(a)), np.std(np.log2(b))
    check("Speed: still between the clicks (pitch sd < 0.01 octave), wandering past them (> 0.1)",
          sa < 0.01 and sb > 0.1, "%.3f -> %.3f octave" % (sa, sb))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkrecord = (frac(kt / 15) > 0.5 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.5 ? 1 : 0)\n"
            "gkfreeze = (frac(kt / 7) > 0.6 ? 1 : 0)\ngkreset = (kt > 40 && frac(kt * 3) < 0.02 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.2) < 0.02 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkblend_alt = frac(kt * 0.02)\n")
    (x, cpu) = run("sweep", 62, auto)
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    # the worst case for CPU: both registers at the top of the noise range
    (_, cpuw) = run("worst", 62, "gkloopstart = 1\ngkpitch = 1.3\ngkrecord = 1\ngkoverlap = 0.5\n")
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_silence.wav"), "looper")
    print("  CPU for 62 s: register %.1f s (worst case %.1f s), factory looper %.1f s (%.2fx, worst %.2fx)"
          % (cpu, cpuw, cpul, cpu / cpul, cpuw / cpul))
    check("CPU within 1.2x the factory looper, worst case included", max(cpu, cpuw) < 1.2 * cpul,
          "%.2fx, worst %.2fx" % (cpu / cpul, cpuw / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 4, BASE, sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "4", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f = strongest(x, 1.5, 3.9)
    check("6.09: compiles, the 3-step cycle at 1395.3 Hz (within 0.3 %)",
          ok and abs(f / (CLK / 3) - 1) < 0.003 and not np.isnan(x).any(), "%.1f Hz, rms %.3f" % (f, rms(x, 1.5, 3.9)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["pitch", "range", "length", "chance", "lock", "divide", "filter", "steps", "extclock",
                            "stereo", "motion", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
