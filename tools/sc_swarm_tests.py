#!/usr/bin/env python3
"""Offline tests of sc/09_sc_swarm.scd: NRT renders in SuperCollider 3.10.4.

  python tools/sc_swarm_tests.py [scenario ...]

  pitch    one voice, no spread: C2 at the Pitch click, C3 at Pitch 0.8
  spread   Size: the energy spreads round the note (unison narrow, Size 0.6 wide)
  density  Density 0 = one voice, 1 = 32; the level stays within 4 dB
  chord    Source + Start = major: the energy gathers on C, E and G (glides there)
  freeze   Freeze: the spectrum stops changing (wandering held)
  shake    Reset: the oscillators move (the spectrum changes at once)
  wave     Overlap: triangle (odd harmonics only, soft) -> saw (all)
  hush     Record: fades out, and back
  level    everything moving: bounded, no NaN; NRT time against 04_sc_cloud
Renders go to firmware/dist/sc_tests/.
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sc_nrt_tests as N   # noqa: E402
import sc_space_tests as T  # noqa: E402

SR = 48000
FAILS = []
PATCH = os.path.join(ROOT, "sc", "09_sc_swarm.scd").replace("\\", "/")
C2 = 65.406


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


def make_inputs():
    os.makedirs(N.OUT, exist_ok=True)
    N.write_wav(N.OUT + "/swin_silence.wav", [np.zeros(40 * SR, np.float32)] * 2)


def render(name, init, events, dur):
    return T.render(name, init, events, dur, "swin_silence.wav", patch=PATCH, defload=True)


BASE = dict(blend=1, speed=0.5, pitch=0.6, start=0.15, size=0.3, density=0.6, overlap=0.0, window=0.4,
            start_alt=1, size_alt=0, density_alt=0.4, overlap_alt=1)


def spec(x, t0, t1):
    m = N.seg(x, t0, t1).mean(axis=1)
    sp = np.abs(np.fft.rfft(m * np.hanning(len(m)), 1 << 18))
    return np.fft.rfftfreq(1 << 18, 1 / SR), sp


def peak(x, t0, t1, lo=20, hi=2000):
    f, sp = spec(x, t0, t1)
    m = (f > lo) & (f < hi)
    return float(f[m][np.argmax(sp[m])])


def width(x, t0, t1, f0):
    """Energy-weighted spread (cents) round f0, within an octave either side."""
    f, sp = spec(x, t0, t1)
    m = (f > f0 / 2) & (f < f0 * 2)
    c = 1200 * np.log2(f[m] / f0)
    p = sp[m] ** 2
    return float(np.sqrt((p * c ** 2).sum() / p.sum()))


def npeaks(x, t0, t1, f0=C2, db=30):
    """Spectral peaks within an octave of f0 and within db of the strongest, at least 0.5 Hz apart."""
    f, sp = spec(x, t0, t1)
    m = np.flatnonzero((f > f0 / 2) & (f < f0 * 2))
    s = sp[m]
    thr = s.max() * 10 ** (-db / 20)
    pk = [i for i in range(1, len(s) - 1) if s[i] > thr and s[i] >= s[i - 1] and s[i] > s[i + 1]]
    out = []
    for i in pk:
        if not out or f[m][i] - f[m][out[-1]] > 0.5:
            out.append(i)
    return len(out)


def band(x, t0, t1, f0, cents=30):
    f, sp = spec(x, t0, t1)
    m = (f > f0 * 2 ** (-cents / 1200)) & (f < f0 * 2 ** (cents / 1200))
    return float((sp[m] ** 2).sum())


def rms_db(x, t0, t1):
    return 10 * np.log10(np.mean(N.seg(x, t0, t1) ** 2) + 1e-20)


def sc_pitch():
    print("[pitch]")
    x, _ = render("sw_pitch", dict(BASE, size=0, density=0), [(3.0, dict(pitch=0.8))], 6)
    a, b = peak(x, 1, 2.9), peak(x, 4, 5.9)
    check(abs(a / C2 - 1) < 0.005 and abs(b / (2 * C2) - 1) < 0.005, f"C2 at the click, C3 at 0.8: {a:.2f}, {b:.2f} Hz")


def sc_spread():
    print("[spread]")
    x, _ = render("sw_spread", dict(BASE, size=0.05, density=1), [(4.0, dict(size=0.6))], 8)
    a, b = width(x, 1, 3.9, C2), width(x, 5, 7.9, C2)
    check(b > 4 * a and b > 80, f"Size: spread {a:.0f} cents (unison-ish) -> {b:.0f} cents")


def sc_density():
    print("[density]")
    x, _ = render("sw_density", dict(BASE, density=0, size=0.4), [(4.0, dict(density=1))], 8)
    a, b = rms_db(x, 1, 3.9), rms_db(x, 5, 7.9)
    check(abs(a - b) < 4, f"one voice {a:.1f} dB, forty {b:.1f} dB")
    na, nb = npeaks(x, 1, 3.9), npeaks(x, 5, 7.9)
    check(nb > 5 * na, f"forty voices: {nb} spectral peaks round the note, one voice: {na}")


def sc_chord():
    print("[chord]")
    x, _ = render("sw_chord", dict(BASE, start=0.15, size=0.05, density=1, density_alt=0.1), [(3.0, dict(source=1))], 8)
    notes = [C2 * 2 ** (s / 12) for s in (0, 4, 7, 12)]
    off = [band(x, 1, 2.9, f) for f in notes]
    on = [band(x, 5, 7.9, f) for f in notes]
    tot_on = sum(on)
    check(off[1] < 0.05 * off[0] and min(on[1], on[2]) > 0.1 * tot_on,
          "Source: the swarm gathers on C, E, G (E share %.2f -> %.2f, G %.2f)" % (off[1] / sum(off), on[1] / tot_on,
                                                                                  on[2] / tot_on))


def spectral_change(x, t0, t1, t2, t3):
    f, a = spec(x, t0, t1)
    _, b = spec(x, t2, t3)
    m = (f > 40) & (f < 130)
    a, b = a[m] / a[m].max(), b[m] / b[m].max()
    return float(np.abs(a - b).mean() / ((a + b).mean() / 2))


def peak_freqs(x, t0, t1, k=6):
    """The k strongest spectral peaks within an octave of C2 (Hz)."""
    f, sp = spec(x, t0, t1)
    m = np.flatnonzero((f > C2 / 2) & (f < C2 * 2))
    s = sp[m]
    pk = [i for i in range(1, len(s) - 1) if s[i] >= s[i - 1] and s[i] > s[i + 1]]
    pk.sort(key=lambda i: -s[i])
    return np.array(sorted(f[m][pk[:k]]))


def moved(x, a, b):
    """Mean distance (cents) from each strong peak in window a to the nearest one in window b. (Voices beating
    against each other change the magnitude spectrum even when nothing moves, so the peaks' frequencies are
    compared, not the magnitudes.)"""
    pa, pb = peak_freqs(x, *a), peak_freqs(x, *b)
    return float(np.mean([np.min(np.abs(1200 * np.log2(pb / p))) for p in pa]))


def sc_freeze():
    print("[freeze]")
    base = dict(BASE, window=0.9, size=0.5, density=0.15, speed=0.5)
    x, _ = render("sw_freeze", base, [(9.0, dict(freeze=1))], 22)
    mv, hd = moved(x, (1, 4), (5, 8)), moved(x, (10, 13), (18, 21))
    # a 3 s window resolves about 9 cents at C2, and close voices beating move the peaks a little
    check(hd < 5 and mv > 2.5 * hd, f"Freeze: the voices moved {mv:.1f} cents in 4 s while wandering, {hd:.2f} held")


def sc_shake():
    print("[shake]")
    x, _ = render("sw_shake", dict(BASE, window=0.5, size=0.5, density=0.15, freeze=1), [(8.0, dict(t_reset=1))], 16)
    before, across = moved(x, (1, 4), (4.5, 7.5)), moved(x, (4.5, 7.5), (9, 12))
    check(across > 10 and across > 5 * before,
          f"Reset shakes the (frozen) swarm: {before:.2f} cents held, {across:.1f} cents across the shake")


def sc_wave():
    print("[wave]")
    x, _ = render("sw_wave", dict(BASE, size=0, density=0, overlap=0), [(3.0, dict(overlap=1))], 6)
    # a triangle has only odd harmonics (the 3rd 19 dB down); a saw has them all
    h_tri = band(x, 1, 2.9, 2 * C2) / band(x, 1, 2.9, C2)
    h3 = band(x, 1, 2.9, 3 * C2) / band(x, 1, 2.9, C2)
    h_saw = band(x, 4, 5.9, 2 * C2) / band(x, 4, 5.9, C2)
    check(h_tri < 1e-3 and h3 < 0.03 and h_saw > 0.1,
          f"Overlap: triangle (2nd harmonic {h_tri:.1e}, 3rd {h3:.3f} of the fundamental's energy) -> saw (2nd {h_saw:.2f})")


def sc_hush():
    print("[hush]")
    x, _ = render("sw_hush", BASE, [(2.0, dict(record=1)), (12.0, dict(record=0))], 22)
    a, b, c = rms_db(x, 1, 1.9), rms_db(x, 10, 11.9), rms_db(x, 20, 21.9)
    check(b < a - 40 and abs(c - a) < 3, f"Record: {a:.1f} dB -> {b:.1f} dB -> back to {c:.1f} dB")


def sc_level():
    print("[level]")
    ev = [(0.5 + 0.5 * k, dict(size=(k * 0.13) % 1, density=(k * 0.29) % 1, start=(k * 0.17) % 1,
                               window=(k * 0.23) % 1, overlap=(k * 0.31) % 1, speed=(k * 0.11) % 1,
                               pitch=(k * 0.07) % 1.6 - 0.3, freeze=(k // 5) % 2, source=(k // 4) % 2,
                               size_alt=(k * 0.37) % 1, overlap_alt=(k * 0.43) % 1, density_alt=(k * 0.41) % 1,
                               t_reset=1 if k % 3 == 0 else 0)) for k in range(38)]
    x, el = render("sw_level", BASE, ev, 22)
    check(not np.isnan(x).any() and float(np.abs(x).max()) <= 0.96 and N.rms(x[SR:]) > 0.01,
          f"everything moving: bounded, no NaN (peak {np.abs(x).max():.3f}, rms {N.rms(x[SR:]):.3f})")
    # 4 minutes of audio, so sclang's start-up (several seconds, and varying) doesn't swamp the DSP time
    _, e1 = render("sw_cpu1", dict(BASE, density=1, overlap=0.7), [], 1)
    _, e2 = render("sw_cpu241", dict(BASE, density=1, overlap=0.7), [], 241)
    _, c1 = T.render("sw_cloud1", {}, [], 1, "swin_silence.wav", patch=T.CLOUD)
    _, c2 = T.render("sw_cloud241", {}, [], 241, "swin_silence.wav", patch=T.CLOUD)
    print(f"  info NRT time per minute of audio (32 voices): sc_swarm {(e2 - e1) / 4:.2f} s, "
          f"04_sc_cloud {(c2 - c1) / 4:.2f} s")


SCEN = dict(pitch=sc_pitch, spread=sc_spread, density=sc_density, chord=sc_chord, freeze=sc_freeze, shake=sc_shake,
            wave=sc_wave, hush=sc_hush, level=sc_level)

if __name__ == "__main__":
    make_inputs()
    for n in sys.argv[1:] or list(SCEN):
        SCEN[n]()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
