#!/usr/bin/env python3
"""Offline tests of instr/somnus.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/somnus_sim.py [scenario ...]
  python tools/somnus_sim.py m609

  pitch     the sine (Blend 0): C3 at the click
  sources   Blend: sine, supersaw, wavetable, loop: four different sounds; the supersaw brighter than the sine
  tinyloop  the shortest loop is an oscillator: C3 at 1x, C4 at 2x (Speed fully clockwise)
  varispeed Speed at noon stops the loop (silence from a stopped loop)
  record    Record layers the input into the loop; it plays back after recording stops
  filter    File: low-pass, band-pass, high-pass, comb shape the noise differently
  resonator Window: resonances at the tune, its fifth and octave
  echo      Overlap: a burst echoes (left at T, right at 1.5 T)
  ambience  alt Blend: a tail after a burst
  random    Reset randomises (the sound changes); Freeze undoes it (back to before)
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles, the sine at C3
Renders go to firmware/dist/somnus_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "somnus_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "somnus.instr")
SR = 48000
C3 = 130.813
BASE = ("gkspeed = 0.625\ngkpitch = 0.6\ngkloopstart = 0\ngkloopsize = 1\ngkblend = 0\ngkdensity = 1\n"
        "gkwindow = 0\ngkoverlap = 0\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\ngkreset = 0\n")
ALTS = ("start_alt=0.3 size_alt=0.6 density_alt=0.1 window_alt=0.6 overlap_alt=0.4 blend_alt=0 pitch_alt=0.4 "
        "record_alt=0")
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    import wave
    n = 70 * SR
    t = np.arange(n) / SR
    burst = 0.5 * np.sin(2 * np.pi * 660 * t) * ((t > 2.0) & (t < 2.05))
    for name, sig in (("in_silence.wav", np.zeros(n)), ("in_sine.wav", 0.4 * np.sin(2 * np.pi * 440 * t)),
                      ("in_burst.wav", burst)):
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


def hi(x, t0, t1, lo=1000, n=8192):
    f, p = psd(x, t0, t1, n=n)
    m = (f > 30) & (f < 14000)
    return float(10 * np.log10(np.sum(p[m & (f > lo)]) / np.sum(p[m]) + 1e-12))


def spec(x, t0, t1):
    f, p = psd(x, t0, t1, n=8192)
    m = (f > 20) & (f < 12000)
    q = np.log10(p[m] + 1e-14)
    return q - q.mean()


def sc_pitch():
    print("pitch")
    (x, _) = run("pitch", 4, "")
    f = near_peak(x, 1.5, 3.9, C3)[0]
    check("the sine (Blend 0): C3 at the click (within 0.3 %)", abs(f / C3 - 1) < 0.003, "%.2f Hz" % f)
    check("level: rms > 0.05, peak under 1", rms(x, 1.5, 3.9) > 0.05 and float(np.abs(x).max()) < 1,
          "rms %.3f, peak %.3f" % (rms(x, 1.5, 3.9), float(np.abs(x).max())))


def sc_sources():
    print("sources")
    (x, _) = run("sources", 10, steps("gkblend", (0, 0), (3, 0.3333), (5, 0.6667), (7, 1)))
    sp = [spec(x, a, a + 1.4) for a in (1.5, 3.5, 5.5, 7.5)]
    d = min(np.sqrt(np.mean((sp[i] - sp[j]) ** 2)) for i in range(4) for j in range(i + 1, 4))
    check("Blend: sine, supersaw, wavetable, loop all differ (closest pair > 0.3 decades)", d > 0.3, "%.2f" % d)
    a, b = hi(x, 1.5, 2.9, lo=500), hi(x, 3.5, 4.9, lo=500)
    check("the supersaw is brighter than the sine (> 20 dB more above 500 Hz)", b - a > 20, "%+.1f -> %+.1f dB" % (a, b))


def sc_tinyloop():
    print("tinyloop")
    auto = "gkblend = 1\ngkloopsize = 0\n" + steps("gkspeed", (0, 0.625), (4, 1))
    (x, _) = run("tiny", 7, auto)
    a, b = near_peak(x, 1.5, 3.9, C3, tol=0.02)[0], near_peak(x, 4.5, 6.9, 2 * C3, tol=0.02)[0]
    check("the shortest loop plays C3 at 1x, C4 at 2x (within 0.5 %)",
          abs(a / C3 - 1) < 0.005 and abs(b / (2 * C3) - 1) < 0.005, "%.2f, %.2f Hz" % (a, b))


def sc_varispeed():
    print("varispeed")
    (x, _) = run("vari", 7, "gkblend = 1\n" + steps("gkspeed", (0, 0.625), (4, 0.5)))
    a, b = db(rms(x, 1.5, 3.9)), db(rms(x, 5, 6.9))
    check("Speed at noon stops the loop (> 40 dB quieter)", a - b > 40, "%.1f -> %.1f dB" % (a, b))


def sc_record():
    print("record")
    # a 2 s loop of noise; record the 440 Hz input from 1.5 to 3.7 s (once round), then listen
    auto = "gkblend = 1\ngkloopsize = %g\ngkrecord = (kt > 1.5 && kt < 3.7 ? 1 : 0)\n" % (np.log(2 / 0.0076445) / np.log(654.07))
    (x, _) = run("record", 7, auto, alts=ALTS.replace("size_alt=0.6", "size_alt=0"), wav="in_sine.wav")
    a = near_peak(x, 1.0, 1.45, 440, tol=0.01)[1]
    b = near_peak(x, 4.5, 6.9, 440, tol=0.01)[1]
    check("Record layers the input into the loop: 440 Hz plays back afterwards (> 30 dB up)", b - a > 30,
          "%+.1f dB" % (b - a))


def sc_filter():
    print("filter")
    auto = "gkblend = 1\ngkdensity = 0.55\n" + pulses(3.0, 5.0, 7.0, name="gkfilestate")
    (x, _) = run("filter", 9, auto)
    fc = 30 * 600 ** 0.55
    res = []
    for a in (1.5, 3.5, 5.5, 7.5):
        f, p = psd(x, a, a + 1.3)
        res.append((band(f, p, 40, fc / 3), band(f, p, fc * 0.8, fc * 1.25), band(f, p, fc * 3, 12000)))
    lp, bp, hp, cb = res
    check("low-pass: lows over highs (> 20 dB)", 10 * np.log10(lp[0] / lp[2]) > 20, "%+.1f dB" % (10 * np.log10(lp[0] / lp[2])))
    check("band-pass: the cutoff over both sides (> 6 dB)", bp[1] > 4 * bp[0] and bp[1] > 4 * bp[2],
          "%+.1f, %+.1f dB" % (10 * np.log10(bp[1] / bp[0]), 10 * np.log10(bp[1] / bp[2])))
    check("high-pass: highs over lows (> 20 dB)", 10 * np.log10(hp[2] / hp[0]) > 20, "%+.1f dB" % (10 * np.log10(hp[2] / hp[0])))
    sp = spec(x, 7.5, 8.8)
    check("comb: a different shape again (> 0.3 decades from the low-pass)", float(np.sqrt(np.mean((sp - spec(x, 1.5, 2.8)) ** 2))) > 0.3,
          "%.2f" % float(np.sqrt(np.mean((sp - spec(x, 1.5, 2.8)) ** 2))))


def sc_resonator():
    print("resonator")
    krt = 40 * 17.5 ** 0.4
    (x, _) = run("reso", 7, "gkblend = 1\n" + steps("gkwindow", (0, 0), (4, 1)))
    gains = []
    for r in (1, 1.4983, 2):
        a = near_peak(x, 1.5, 3.9, krt * r, tol=0.01)[1]
        b = near_peak(x, 4.5, 6.9, krt * r, tol=0.01)[1]
        gains.append(b - a)
    check("Window: resonances at the tune (%.0f Hz), its fifth and octave (each > 10 dB up)" % krt,
          min(gains) > 10, " ".join("%+.1f" % g for g in gains) + " dB")


def sc_echo():
    print("echo")
    # a stopped loop (silent) as the source; the burst comes in through Source
    auto = "gkblend = 1\ngkspeed = 0.5\ngksource = 1\ngkoverlap = 0.5\n"
    (x, _) = run("echo", 4.5, auto, wav="in_burst.wav")
    t_echo = 0.05 + 1.45 * 0.16

    def lag(ch):
        s = np.abs(seg(x, 2.0, 4.4, ch))
        w = int(0.004 * SR)
        e = np.convolve(s, np.ones(w) / w, "same")
        i0 = int(0.1 * SR)
        return (i0 + int(np.argmax(e[i0:]))) / SR
    a, b = lag(0), lag(1)
    check("Overlap: echoes, left at T (%.3f s) and right at 1.5 T (within 5 %%)" % t_echo,
          abs(a / t_echo - 1) < 0.05 and abs(b / (1.5 * t_echo) - 1) < 0.05, "%.3f, %.3f s" % (a, b))


def sc_ambience():
    print("ambience")
    auto = "gkblend = 1\ngkspeed = 0.5\ngksource = 1\n"
    (x, _) = run("amb0", 4.5, auto, wav="in_burst.wav")
    (y, _) = run("amb1", 4.5, auto, alts=ALTS.replace("blend_alt=0", "blend_alt=1"), wav="in_burst.wav")
    a, b = db(rms(x, 2.6, 3.2)), db(rms(y, 2.6, 3.2))
    check("alt Blend: a tail after the burst (> 30 dB over none)", b - a > 30, "%.1f -> %.1f dB" % (a, b))


def sc_random():
    print("random")
    auto = "gkblend = 0.6667\ngkdensity = 0.6\ngkwindow = 0.3\n" + pulses(3.0, name="gkreset") + pulses(5.5, name="gkfreeze")
    (x, _) = run("random", 8.6, auto)
    (y, _) = run("random0", 8.6, "gkblend = 0.6667\ngkdensity = 0.6\ngkwindow = 0.3\n")

    def thirds(z, t0, t1):
        """Third-octave band levels, 50 Hz - 10 kHz (dB): steadier than raw bins, whose notches wander."""
        f, p = psd(z, t0, t1, n=8192)
        edges = 50 * 2 ** (np.arange(0, 23) / 3)
        return np.array([10 * np.log10(band(f, p, a, b) + 1e-14) for a, b in zip(edges[:-1], edges[1:])])

    def dist(a, b):
        return float(np.sqrt(np.mean((a - b) ** 2)))
    # the randomised values return exactly on undo (logged); the supersaw's slow beating means windows seconds
    # apart differ anyway, so the reference is the same render without any randomise, over the same windows
    d1 = dist(thirds(x, 3.8, 5.3), thirds(y, 3.8, 5.3))
    d2 = dist(thirds(x, 7.3, 8.5), thirds(y, 7.3, 8.5))   # (after the 1.6 s glide back)
    check("Reset randomises (third-octave bands > 3 dB rms from the unrandomised run); Freeze undoes it (< 1 dB)",
          d1 > 3 and d2 < 1, "randomised %.1f dB, after undo %.2f dB" % (d1, d2))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkblend = frac(kt * 0.04)\n"
            "gkrecord = (frac(kt * 0.07) > 0.6 ? 1 : 0)\ngkreset = (frac(kt * 0.3) < 0.02 ? 1 : 0)\n"
            "gkfreeze = (frac(kt * 0.21) < 0.02 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.5 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.25) < 0.02 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\ngkdensity_alt = frac(kt * 0.04)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkoverlap_alt = frac(kt * 0.03)\ngkblend_alt = frac(kt * 0.02)\n"
            "gkpitch_alt = frac(kt * 0.035)\ngkrecord_alt = (frac(kt / 17) > 0.5 ? 1 : 0)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_sine.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_sine.wav"), "looper")
    print("  CPU for 62 s: somnus %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


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
    f = near_peak(x, 1.5, 3.9, C3)[0]
    check("6.09: compiles, the sine at C3 (within 0.3 %)", ok and abs(f / C3 - 1) < 0.003 and not np.isnan(x).any(),
          "%.2f Hz, rms %.3f" % (f, rms(x, 1.5, 3.9)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["pitch", "sources", "tinyloop", "varispeed", "record", "filter", "resonator", "echo",
                            "ambience", "random", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
