#!/usr/bin/env python3
"""Offline tests of instr/radiate.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609, from
Windows Python).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/radiate_sim.py [scenario ...]
  python tools/radiate_sim.py m609

  pitch    self-oscillating, one peak: the click = C6 (1046.5 Hz), 1V/oct down and up (C5, C7, C3)
  types    Window: low-pass, band-pass, high-pass, smile (one peak: a notch) on white noise
  shapes   File: even (0 8 16 24 semitones), harmonic (1:2:3:4), octaves, chord (0 7 12 16) at Radiate noon
  density  Density: 1, 2, 3, 4 peaks
  radiate  Radiate: fully anticlockwise all peaks on one; fully clockwise twice the shape
  stereo   alt Overlap (width): the high peaks wide apart, nothing apart at width 0
  ping     Reset: each pulse rings the peak at its frequency; alt Density = ring time
  animate  Speed: no movement between the clicks, movement past either click, Freeze holds it still
  fm       Source: the right input modulates the cutoff (sidebands) and is no longer heard
  normal   a silent right input copies the left; a live one stays its own channel
  dirty    Record: harmonics (even and odd) from a clean sine
  level    noise in: the output level across resonance and output type stays within a range
  sweep    every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609     Csound 6.09.1: compiles, self-oscillates at C6
Renders go to firmware/dist/radiate_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "radiate_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "radiate.instr")
SR = 48000
C6 = 1046.502
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0.5\ngkloopsize = 0.5\ngkdensity = 1\ngkwindow = 0\n"
        "gkoverlap = 0.3\ngkblend = 1\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\n")
ALTS = "start_alt=0.3 size_alt=0.5 density_alt=0.4 window_alt=0.5 overlap_alt=0.6 blend_alt=0.5 pitch_alt=0"
NOW = "start_alt=0.3 size_alt=0.5 density_alt=0.4 window_alt=0.5 overlap_alt=0 blend_alt=0.5 pitch_alt=0"
RESULTS = []
SHAPES = {"even": [0, 8, 16, 24], "harmonic": [0, 12, 19.0196, 24], "octaves": [0, 12, 24, 36],
          "chord": [0, 7, 12, 16]}


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def stereo_wav(name, left, right):
    import wave
    data = (np.clip(np.stack([left, right], axis=1), -1, 1) * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    n = 70 * SR
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    z = np.zeros(n)
    noise = 0.1 * rng.standard_normal(n)
    stereo_wav("in_silence.wav", z, z)
    stereo_wav("in_noise.wav", noise, noise)
    stereo_wav("in_noiseL.wav", noise, z)
    stereo_wav("in_noise_sine.wav", noise, 0.3 * np.sin(2 * np.pi * 200 * t))
    stereo_wav("in_sine.wav", 0.2 * np.sin(2 * np.pi * 200 * t), 0.2 * np.sin(2 * np.pi * 200 * t))
    stereo_wav("in_fm.wav", z, 0.5 * np.sin(2 * np.pi * 100 * t))
    # pink noise (1/f power), closer to music than white: for the level scenario
    sp = np.fft.rfft(rng.standard_normal(n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    sp[1:] /= np.sqrt(fr[1:] / 1000)
    sp[fr < 20] = 0                                  # (no sub-audio: the output's DC blocker would take it)
    pink = np.fft.irfft(sp, n)
    pink *= 0.1 / pink.std()
    stereo_wav("in_pink.wav", pink, pink)
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def pulses(*ts, name="gkreset"):
    return name + " = (" + " || ".join("(kt > %g && kt < %g)" % (t, t + 0.01) for t in ts) + " ? 1 : 0)\n"


def steps(var, *pairs):
    """var takes each value from its time on: steps("gkwindow", (0, 0), (3, 0.33)) -> nested ternaries."""
    expr = "%g" % pairs[-1][1]
    for (t, v), (t2, _) in reversed(list(zip(pairs[:-1], pairs[1:]))):
        expr = "(kt < %g ? %g : %s)" % (t2, v, expr)
    return "%s = %s\n" % (var, expr)


def run(name, secs, auto, wav="in_silence.wav", alts=ALTS):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=alts, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, wav), name)


def seg(x, t0, t1, ch=None):
    s = x[int(t0 * SR):int(t1 * SR)]
    return s.mean(axis=1) if ch is None else s[:, ch]


def rms(x, t0, t1, ch=None):
    return float(np.sqrt(np.mean(seg(x, t0, t1, ch) ** 2)))


def db(v):
    return 20 * np.log10(v + 1e-12)


def psd(x, t0, t1, ch=None, n=8192):
    """Welch average of the power spectrum (Hann, half overlap)."""
    s = seg(x, t0, t1, ch)
    w = np.hanning(n)
    acc = np.zeros(n // 2 + 1)
    k = 0
    for i in range(0, len(s) - n, n // 2):
        acc += np.abs(np.fft.rfft(s[i:i + n] * w)) ** 2
        k += 1
    return np.fft.rfftfreq(n, 1 / SR), acc / max(k, 1)


def band(f, p, lo, hi):
    return float(np.mean(p[(f >= lo) & (f <= hi)]))


def strongest(x, t0, t1, lo=20, hi=20000, ch=None):
    s = seg(x, t0, t1, ch)
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)), 1 << 19))
    f = np.fft.rfftfreq(1 << 19, 1 / SR)
    m = (f > lo) & (f < hi)
    i = np.flatnonzero(m)[np.argmax(sp[m])]
    a, b, c = np.log(sp[i - 1:i + 2] + 1e-20)
    return float(f[i] + 0.5 * (a - c) / (a - 2 * b + c) * (f[1] - f[0]))


def peaks(f, p, count, lo=100, hi=12000, sep=0.04):
    """The strongest `count` local maxima, at least `sep` (relative) apart, parabolic-interpolated, ascending."""
    lp = 10 * np.log10(p + 1e-30)
    cand = [i for i in range(2, len(p) - 2) if lo < f[i] < hi and lp[i] >= lp[i - 1] and lp[i] >= lp[i + 1]]
    cand.sort(key=lambda i: -lp[i])
    got = []
    for i in cand:
        if all(abs(f[i] / f[j] - 1) > sep for j in got):
            got.append(i)
        if len(got) == count:
            break
    out = []
    for i in got:
        a, b, c = lp[i - 1:i + 2]
        out.append(float(f[i] + 0.5 * (a - c) / (a - 2 * b + c) * (f[1] - f[0])))
    return sorted(out)


def sc_pitch():
    print("pitch")
    auto = ("gkloopsize = 1\ngkdensity = 0\n" +
            steps("gkpitch", (0, 0.6), (4.5, 0.4), (7.5, 0.8), (10.5, 0.0)))
    (x, _) = run("pitch", 13.5, auto)
    want = [C6, C6 / 2, C6 * 2, C6 / 8]
    got = [strongest(x, a, a + 1.5) for a in (2.5, 5.5, 8.5, 11.5)]
    check("1V/oct: C6 at the click, C5, C7, C3 (within 0.3 %)",
          all(abs(g / w - 1) < 0.003 for g, w in zip(got, want)),
          " ".join("%.2f" % g for g in got) + "  (want " + " ".join("%.2f" % w for w in want) + ")")
    pk = float(np.abs(x).max())
    check("self-oscillation level: rms > 0.05, peak under 1", rms(x, 2.5, 4) > 0.05 and pk < 1,
          "rms %.3f, peak %.3f" % (rms(x, 2.5, 4), pk))


def sc_types():
    print("types")
    auto = "gkdensity = 0\ngkloopsize = 0.5\n" + steps("gkwindow", (0, 0), (4, 1 / 3), (7, 2 / 3), (10, 1))
    (x, _) = run("types", 13, auto, wav="in_noise.wav")
    res = []
    for a in (1.5, 4.5, 7.5, 10.5):
        f, p = psd(x, a, a + 2.4)
        res.append([db(np.sqrt(band(f, p, lo, hi))) for lo, hi in ((100, 300), (1031, 1062), (4000, 8000))])
    lo_, bp_, hi_, sm_ = res
    check("low-pass (12 dB/octave): lows over highs by > 20 dB", lo_[0] - lo_[2] > 20, "%+.1f dB" % (lo_[0] - lo_[2]))
    check("band-pass: the cutoff over lows and highs by > 10 dB", bp_[1] - bp_[0] > 10 and bp_[1] - bp_[2] > 10,
          "%+.1f, %+.1f dB" % (bp_[1] - bp_[0], bp_[1] - bp_[2]))
    check("high-pass (12 dB/octave): highs over lows by > 20 dB", hi_[2] - hi_[0] > 20, "%+.1f dB" % (hi_[2] - hi_[0]))
    check("smile (one peak): a notch at the cutoff, > 10 dB under lows and highs",
          sm_[0] - sm_[1] > 10 and sm_[2] - sm_[1] > 10, "%+.1f, %+.1f dB" % (sm_[0] - sm_[1], sm_[2] - sm_[1]))


def shape_auto(presses=()):
    return ("gkloopsize = 0.8\ngkwindow = 0.3333\ngkpitch = 0.3\n" +
            (pulses(*presses, name="gkfilestate") if presses else ""))


def sc_shapes():
    print("shapes")
    fc = C6 * 2 ** -1.5
    (x, _) = run("shapes", 14, shape_auto((4.5, 7.5, 10.5)), wav="in_noise.wav", alts=NOW)
    for k, (name, v) in enumerate(SHAPES.items()):
        a = 1.7 + 3 * k
        f, p = psd(x, a, a + 2.6, n=16384)
        got = peaks(f, p, 4, lo=fc * 0.8, hi=fc * 9)
        want = [fc * 2 ** (s / 12) for s in v]
        ok = len(got) == 4 and all(abs(g / w - 1) < 0.025 for g, w in zip(got, want))
        check("%s: peaks at %s (within 2.5 %%: neighbouring peaks pull a little)" % (name, " ".join("%.0f" % w for w in want)), ok,
              " ".join("%.1f" % g for g in got))


def sc_density():
    print("density")
    fc = C6 * 2 ** -1.5
    want = [fc * 2 ** (s / 12) for s in SHAPES["even"]]
    auto = shape_auto() + steps("gkdensity", (0, 0), (4, 0.34), (7, 0.67), (10, 1))
    (x, _) = run("density", 13, auto, wav="in_noise.wav", alts=NOW)
    counts = []
    for a in (1.7, 4.7, 7.7, 10.7):
        f, p = psd(x, a, a + 2.2, n=16384)
        lvl = [db(np.sqrt(band(f, p, w * 0.99, w * 1.01))) for w in want]
        floor = db(np.sqrt(band(f, p, want[0] * 1.15, want[0] * 1.3)))
        counts.append(sum(1 for v in lvl if v > floor + 10))
    check("1, 2, 3, 4 peaks", counts == [1, 2, 3, 4], "%s" % counts)


def sc_radiate():
    print("radiate")
    fc = C6 * 2 ** -2
    auto = "gkloopsize = 0.8\ngkwindow = 0.3333\ngkpitch = 0.2\n" + steps("gkloopstart", (0, 0), (4.5, 1))
    (x, _) = run("radiate", 8, auto, wav="in_noise.wav", alts=NOW)
    f, p = psd(x, 1.7, 4.3, n=16384)
    one = db(np.sqrt(band(f, p, fc * 0.99, fc * 1.01)))
    nxt = db(np.sqrt(band(f, p, fc * 2 ** (8 / 12) * 0.99, fc * 2 ** (8 / 12) * 1.01)))
    check("fully anticlockwise: all on one peak (none 8 semitones up, > 25 dB under)", one - nxt > 25,
          "%+.1f dB" % (one - nxt))
    f, p = psd(x, 5.2, 7.9, n=16384)
    got = peaks(f, p, 4, lo=fc * 0.8, hi=18000)
    want = [fc * 2 ** (s / 6) for s in SHAPES["even"]]
    check("fully clockwise: twice the shape (0 16 32 48 semitones, within 2 %)",
          len(got) == 4 and all(abs(g / w - 1) < 0.02 for g, w in zip(got, want)),
          " ".join("%.0f" % g for g in got) + "  (want " + " ".join("%.0f" % w for w in want) + ")")


def sc_stereo():
    print("stereo")
    fc = C6 * 2 ** -1.5
    want = [fc * 2 ** (s / 12) for s in SHAPES["even"]]
    res = {}
    for w in (0, 1):
        (x, _) = run("stereo%d" % w, 5, shape_auto(), wav="in_noise.wav", alts=ALTS.replace("overlap_alt=0.6",
                                                                                       "overlap_alt=%d" % w))
        lr = []
        for pk in (2, 3):
            fl, pl = psd(x, 1.7, 4.9, ch=0, n=16384)
            fr, pr = psd(x, 1.7, 4.9, ch=1, n=16384)
            lr.append(db(np.sqrt(band(fl, pl, want[pk] * 0.99, want[pk] * 1.01))) -
                      db(np.sqrt(band(fr, pr, want[pk] * 0.99, want[pk] * 1.01))))
        res[w] = lr
    check("full width: peak 3 left, peak 4 right (> 20 dB between their balances)", res[1][0] - res[1][1] > 20,
          "peak 3 L-R %+.1f dB, peak 4 L-R %+.1f dB" % tuple(res[1]))
    check("width 0: both centred (within 1 dB)", max(abs(v) for v in res[0]) < 1,
          "%+.2f, %+.2f dB" % tuple(res[0]))


def t20(x, t0, t1):
    s = seg(x, t0, t1)
    w = int(0.01 * SR)
    r = np.array([np.sqrt(np.mean(s[i:i + w] ** 2)) for i in range(0, len(s) - w, w)])
    ref = r[:5].max()
    below = np.nonzero(r[5:] < ref * 0.1)[0]
    return (5 + below[0]) * 0.01 if len(below) else (t1 - t0)


def sc_ping():
    print("ping")
    auto = "gkdensity = 0\ngkloopsize = 0.5\n" + pulses(2.0, 6.0)
    (x, _) = run("ping0", 9, auto, alts=ALTS.replace("density_alt=0.4", "density_alt=0.2"))
    (y, _) = run("ping1", 9, auto, alts=ALTS.replace("density_alt=0.4", "density_alt=0.8"))
    quiet = rms(x, 1.2, 1.95)
    f = strongest(y, 2.05, 3.0)
    check("silent until the ping, then a tone at the peak (C6 within 0.3 %)", quiet < 1e-4 and abs(f / C6 - 1) < 0.003,
          "before %.1e, tone %.2f Hz, level %.3f" % (quiet, f, rms(y, 2.0, 2.3)))
    a, b = t20(x, 2.0, 5.9), t20(y, 6.0, 8.95)
    check("alt Density: ring time short -> long (-20 dB in < 0.2 s, then > 2 s)", a < 0.2 and b > 2,
          "%.2f s -> %.2f s" % (a, b))


def centroids(x, t0, t1):
    out = []
    for a in np.arange(t0, t1 - 0.25, 0.25):
        f, p = psd(x, a, a + 0.25, n=4096)
        m = (f > 50) & (f < 16000)
        out.append(float(np.sum(f[m] * p[m]) / np.sum(p[m])))
    return np.array(out)


def sc_animate():
    print("animate")
    auto = (shape_auto() + "gkpitch = 0.5\ngkloopsize = 0.7\n" +
            steps("gkspeed", (0, 0.5), (6, 0.9), (16, 0.1)) + "gkfreeze = (kt > 11 && kt < 16 ? 1 : 0)\n")
    (x, _) = run("animate", 21, auto, wav="in_noise.wav", alts=NOW)
    st = [np.std(np.log2(centroids(x, a, b))) for a, b in ((2, 6), (7, 11), (12, 16), (17, 21))]
    check("between the clicks: still (centroid sd < 0.06 octave: the noise's own jitter)", st[0] < 0.06, "%.3f" % st[0])
    check("clockwise: moving (sd > 0.15 octave)", st[1] > 0.15, "%.3f" % st[1])
    check("Freeze: held still (sd < 0.06 octave)", st[2] < 0.06, "%.3f" % st[2])
    check("anticlockwise: wandering (sd > 0.1 octave)", st[3] > 0.1, "%.3f" % st[3])


def sc_fm():
    print("fm")
    auto = "gkdensity = 0\ngkloopsize = 1\n" + steps("gksource", (0, 0), (4.5, 1))
    (x, _) = run("fm", 8, auto, wav="in_fm.wav")

    def lines(a):
        f, p = psd(x, a, a + 2.4, n=16384)
        lp = 10 * np.log10(p + 1e-30)
        m = (f > 50) & (f < 5000)
        top = lp[m].max()
        near = [f[i] for i in range(2, len(p) - 2) if 300 < f[i] < 3000 and lp[i] > top - 20 and
                lp[i] >= lp[i - 1] and lp[i] >= lp[i + 1]]
        m100 = 10 * np.log10(band(f, p, 97, 103) + 1e-30) - top
        return near, m100
    off, m_off = lines(2)
    on, m_on = lines(5.5)
    sp = np.diff(on)
    check("Source off: one line (C6), the right input heard (100 Hz > -30 dB of it)",
          len(off) == 1 and abs(off[0] / C6 - 1) < 0.005 and m_off > -30,
          "lines %s, 100 Hz %+.1f dB" % ([round(v) for v in off], m_off))
    check("Source on: FM sidebands 100 Hz apart (>= 5 within 20 dB), the right input not heard (100 Hz < -40 dB)",
          len(on) >= 5 and np.all(np.abs(sp - 100) < 4) and m_on < -40,
          "%d lines, spacing %.1f..%.1f Hz, 100 Hz %+.1f dB" % (len(on), sp.min(), sp.max(), m_on))


def sc_normal():
    print("normal")
    auto = "gkdensity = 0\ngkloopsize = 0.2\ngkpitch = 1.0\n"     # a wide-open low-pass
    (x, _) = run("normal0", 4, auto, wav="in_noiseL.wav", alts=NOW)
    l, r = db(rms(x, 1.5, 3.9, 0)), db(rms(x, 1.5, 3.9, 1))
    check("silent right input: the left copied (within 1 dB)", abs(l - r) < 1, "L %.1f dB, R %.1f dB" % (l, r))
    (y, _) = run("normal1", 4, auto, wav="in_noise_sine.wav", alts=NOW)
    fl, pl = psd(y, 1.5, 3.9, ch=0)
    fr, pr = psd(y, 1.5, 3.9, ch=1)
    dl = db(np.sqrt(band(fl, pl, 195, 205))) - db(np.sqrt(band(fl, pl, 300, 400)))
    dr = db(np.sqrt(band(fr, pr, 195, 205))) - db(np.sqrt(band(fr, pr, 300, 400)))
    check("a live right input stays its own (200 Hz in R > 30 dB over its floor, not in L)", dr > 30 and dl < 6,
          "R %+.1f dB, L %+.1f dB" % (dr, dl))


def sc_dirty():
    print("dirty")
    auto = "gkdensity = 0\ngkloopsize = 0.2\ngkpitch = 1.2\n" + steps("gkrecord", (0, 0), (4.5, 1))
    (x, _) = run("dirty", 8, auto, wav="in_sine.wav")
    res = []
    for a in (2, 5.5):
        f, p = psd(x, a, a + 2.4, n=16384)
        fund = band(f, p, 197, 203)
        h2 = band(f, p, 397, 403)
        h3 = band(f, p, 597, 603)
        res.append((db(np.sqrt(h2 / fund)), db(np.sqrt(h3 / fund))))
    check("clean: harmonics under -40 dB", max(res[0]) < -40, "2nd %+.1f, 3rd %+.1f dB" % res[0])
    check("dirty: 2nd and 3rd harmonics over -35 dB", min(res[1]) > -35, "2nd %+.1f, 3rd %+.1f dB" % res[1])


def sc_level():
    print("level")
    sizes = (0, 0.4, 0.7, 0.85)
    wins = (0, 1 / 3, 2 / 3, 1)
    pairs = []
    t = 1.0
    for w in wins:
        for s in sizes:
            pairs.append((t, w, s))
            t += 1.5
    auto = ("gkwindow = " + "".join("(kt < %g ? %g : " % (a + 1.5, w) for a, w, _ in pairs[:-1]) +
            "%g" % pairs[-1][1] + ")" * (len(pairs) - 1) + "\n" +
            "gkloopsize = " + "".join("(kt < %g ? %g : " % (a + 1.5, s) for a, _, s in pairs[:-1]) +
            "%g" % pairs[-1][2] + ")" * (len(pairs) - 1) + "\n")
    (x, _) = run("level", t + 0.5, auto, wav="in_pink.wav")
    ref = db(0.1)
    lv = [db(rms(x, a + 0.5, a + 1.45)) - ref for a, _, _ in pairs]
    rows = ["%s %s" % (n, " ".join("%+.1f" % v for v in lv[i * 4:i * 4 + 4]))
            for i, n in enumerate(("LP", "BP", "HP", "smile"))]
    print("  dB against the input (pink noise), Size 0 / 0.4 / 0.7 / 0.85:  " + " | ".join(rows))
    check("every output type and resonance within -8 .. +8 dB of the input", min(lv) > -8 and max(lv) < 8,
          "%.1f .. %+.1f dB" % (min(lv), max(lv)))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkrecord = (frac(kt / 15) > 0.5 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.5 ? 1 : 0)\n"
            "gkfreeze = (frac(kt / 7) > 0.6 ? 1 : 0)\ngkreset = (frac(kt * 3) < 0.02 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.4) < 0.03 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\ngkdensity_alt = frac(kt * 0.04)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkoverlap_alt = frac(kt * 0.03)\ngkblend_alt = 0.5 + 0.5 * frac(kt * 0.02)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_noise_sine.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0,
          "peak %.3f, NaN %d" % (float(np.nanmax(np.abs(s))), nan))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_noise_sine.wav"), "looper")
    print("  CPU for 62 s: radiate %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 4, BASE + "gkdensity = 0\ngkloopsize = 1\n", sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "4", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    f = strongest(x, 2.0, 3.8)
    check("6.09: compiles, self-oscillates at C6 (within 0.3 %)", ok and abs(f / C6 - 1) < 0.003,
          "%.2f Hz, rms %.3f" % (f, rms(x, 2.0, 3.8)))


def main():
    make_inputs()
    want = sys.argv[1:] or ["pitch", "types", "shapes", "density", "radiate", "stereo", "ping", "animate", "fm",
                            "normal", "dirty", "level", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
