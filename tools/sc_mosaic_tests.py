#!/usr/bin/env python3
"""Offline tests of sc/07_sc_mosaic.scd: NRT renders in SuperCollider 3.10.4 + sc3-plugins (Concat).

  python tools/sc_mosaic_tests.py [scenario ...]

Input: noise bursts (a hat-like rhythm, 4 a second) and silence. Corpus (the "stick file"): a sequence of pure
tones (300..900 Hz) with decays and gaps. So the output can be told apart: made from the corpus it is tonal (low
spectral flatness) where the input is noise.
  follow   the output's level follows the input's (envelope correlation), quiet when the input is
  corpus   the output is made of the corpus: tonal while the input is noise (flatness far below the input's)
  self     Source on: the corpus is the input's own past, so the output is noise-like again
  pitch    Pitch +12: the output's tones an octave up
  freeze   Freeze + Speed centre (stopped corpus): it still answers, from what the store holds
  level    everything moving: bounded, no NaN
Renders go to firmware/dist/sc_tests/.
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sc_nrt_tests as N   # noqa: E402
import sctest              # noqa: E402

SR = 48000
FAILS = []
PATCH = os.path.join(ROOT, "sc", "07_sc_mosaic.scd").replace("\\", "/")
TONES = [300, 420, 560, 700, 900, 360, 480, 640]


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


def make_inputs():
    os.makedirs(N.OUT, exist_ok=True)
    rng = np.random.default_rng(5)
    t = np.arange(20 * SR) / SR
    burst = ((t % 0.25) < 0.06).astype(float) * np.exp(-(t % 0.25) / 0.02)
    bars = ((t % 4) < 3).astype(float)                       # 3 s of rhythm, 1 s of silence
    x = 0.4 * rng.standard_normal(len(t)) * burst * bars
    N.write_wav(N.OUT + "/mos_in.wav", [x.astype(np.float32)] * 2)
    c = np.zeros(10 * SR)
    for i in range(30):
        f = TONES[i % len(TONES)]
        s0 = int(i * 0.33 * SR)
        n = int(0.3 * SR)
        tt = np.arange(n) / SR
        seg = 0.5 * np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.12)
        c[s0:s0 + n] += seg[:max(0, len(c) - s0)]
    N.write_wav(N.OUT + "/mos_corpus.wav", [c.astype(np.float32)])


def render(name, init, events, dur):
    wav = "%s/%s.wav" % (N.OUT, name)
    if os.path.exists(wav):
        os.remove(wav)
    args = "".join(", \\%s, %r" % (k, float(v)) for k, v in init.items())
    rows = ["[0.0, ['/d_recv', ~neb.def.asBytes]]",
            "[0.0, [\\b_allocReadChannel, 0, \"%s/mos_corpus.wav\", 0, 0, 0]]" % N.OUT,
            "[0.001, [\\s_new, ~neb.name, 1000, 0, 0, \\buf, 0%s]]" % args]
    for t, sets in events:
        a = "".join(", \\%s, %r" % (k, float(v)) for k, v in sets.items())
        rows.append("[%r, [\\n_set, 1000%s]]" % (float(t), a))
    rows.append("[%r, [\\c_set, 0, 0]]" % float(dur))
    scd = """~nrtTest = true;
thisProcess.interpreter.executeFile("%s");
~score = Score([
%s
]);
~opts = ServerOptions.new.numOutputBusChannels_(2).numInputBusChannels_(2).memSize_(262144);
~score.recordNRT(outputFilePath: "%s", inputFilePath: "%s", sampleRate: 48000, headerFormat: "WAV",
    sampleFormat: "float", options: ~opts, duration: %r, action: { "SCNRT done".postln; 0.exit });
SystemClock.sched(150, { "SCNRT timeout".postln; 1.exit; nil });
""" % (PATCH, ",\n".join(rows), wav, N.OUT + "/mos_in.wav", float(dur))
    path = "%s/%s.scd" % (N.OUT, name)
    open(path, "w").write(scd)
    code, out = sctest.sclang(path, 200)
    open("%s/%s.log" % (N.OUT, name), "w").write(out)
    if not os.path.exists(wav):
        print(out[-1500:])
        raise SystemExit("no render for " + name)
    return N.read_wav(wav)[0]


BASE = dict(blend=1, speed=0.625, pitch=0.6, start=0.3, size=0.25, density=0.8, overlap=0.4, window=0.8,
            blend_alt=0, size_alt=0)


def env(x, w=0.02):
    m = x.mean(axis=1) if x.ndim == 2 else x
    n = int(w * SR)
    k = len(m) // n
    return np.sqrt((m[:k * n].reshape(k, n) ** 2).mean(axis=1))


def flatness(x):
    m = x.mean(axis=1) if x.ndim == 2 else x
    sp = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2 + 1e-12
    f = np.fft.rfftfreq(len(m), 1 / SR)
    sp = sp[(f > 200) & (f < 5000)]
    return float(np.exp(np.mean(np.log(sp))) / np.mean(sp))


def bursts_only(x, t0, t1):
    """The parts of [t0, t1) where the input rhythm plays (the first 3 s of each 4 s)."""
    parts = [N.seg(x, a, min(a + 3, t1)) for a in np.arange(t0 - (t0 % 4), t1, 4) if a >= t0 - 0.01]
    return np.concatenate(parts) if parts else N.seg(x, t0, t1)


def sc_follow():
    print("[follow]")
    x = render("mos_follow", BASE, [], 16)
    i = N.read_wav(N.OUT + "/mos_in.wav")[0]
    a, b = env(N.seg(x, 4, 15)), env(N.seg(i, 4, 15))
    n = min(len(a), len(b))
    lag = max(range(0, 6), key=lambda L: np.corrcoef(a[L:n], b[:n - L])[0, 1])
    r = np.corrcoef(a[lag:n], b[:n - lag])[0, 1]
    check(r > 0.5, f"the output's level follows the input's (correlation {r:.2f} at {lag * 20} ms)")
    on, off = N.rms(bursts_only(x, 4, 15)), N.rms(N.seg(x, 7.2, 7.9))
    check(off < 0.3 * on, f"quiet when the input is (rms {on:.3f} in the rhythm, {off:.4f} in its gap)")
    return x


def sc_corpus():
    print("[corpus]")
    x = render("mos_follow", BASE, [], 16)
    i = N.read_wav(N.OUT + "/mos_in.wav")[0]
    fo, fi = flatness(bursts_only(x, 4, 15)), flatness(bursts_only(i, 4, 15))
    check(fo < 0.2 * fi, f"made of the corpus: tonal where the input is noise (flatness {fo:.3f} vs {fi:.3f})")


def sc_self():
    print("[self]")
    x = render("mos_self", dict(BASE, source=1), [], 16)
    i = N.read_wav(N.OUT + "/mos_in.wav")[0]
    fo, fi = flatness(bursts_only(x, 4, 15)), flatness(bursts_only(i, 4, 15))
    check(fo > 0.3 * fi and N.rms(bursts_only(x, 4, 15)) > 0.02,
          f"Source on: rebuilt from the input's own past, noise-like (flatness {fo:.3f} vs {fi:.3f})")


def dominant(x):
    m = x.mean(axis=1)
    sp = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1 / SR)
    band = (f > 200) & (f < 2500)
    return f[band][np.argsort(sp[band])[-4:]]


def median_freq(x):
    """The frequency below which half the energy (200..4000 Hz) lies."""
    m = x.mean(axis=1)
    sp = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    band = (f > 200) & (f < 4000)
    c = np.cumsum(sp[band])
    return float(f[band][np.searchsorted(c, c[-1] / 2)])


def sc_pitch():
    print("[pitch]")
    x0 = render("mos_follow", BASE, [], 16)
    x = render("mos_pitch", dict(BASE, pitch=0.8), [], 16)
    a, b = median_freq(bursts_only(x0, 4, 15)), median_freq(bursts_only(x, 4, 15))
    check(abs(b / a - 2) < 0.2, f"Pitch +12: the output an octave up (median frequency {a:.0f} -> {b:.0f} Hz, "
                                f"x{b / a:.2f})")


def sc_freeze():
    print("[freeze]")
    x = render("mos_freeze", BASE, [(5.0, dict(freeze=1, speed=0.5))], 16)
    a, b = N.rms(bursts_only(x, 1.5, 5)), N.rms(bursts_only(x, 8, 15))
    check(b > 0.4 * a, f"Freeze + stopped corpus: it still answers from the store (rms {a:.3f} -> {b:.3f})")


def sc_level():
    print("[level]")
    ev = [(1 + 0.5 * k, dict(size=(k * 0.13) % 1, density=(k * 0.29) % 1, start=(k * 0.17) % 1,
                             window=(k * 0.23) % 1, overlap=(k * 0.31) % 1, speed=(k * 0.11) % 1,
                             pitch=0.3 + (k * 0.07) % 0.7, blend=(k * 0.19) % 1, freeze=(k // 5) % 2,
                             source=(k // 4) % 2, record=(k // 3) % 2, size_alt=(k * 0.37) % 1, blend_alt=0.5,
                             t_reset=1)) for k in range(28)]
    x = render("mos_level", BASE, ev, 16)
    check(not np.isnan(x).any() and float(np.abs(x).max()) <= 0.96 and N.rms(x[SR:]) > 0.01,
          f"everything moving: bounded, no NaN, not silent (peak {np.abs(x).max():.3f}, rms {N.rms(x[SR:]):.3f})")


SCEN = dict(follow=sc_follow, corpus=sc_corpus, self=sc_self, pitch=sc_pitch, freeze=sc_freeze, level=sc_level)

if __name__ == "__main__":
    make_inputs()
    for n in sys.argv[1:] or list(SCEN):
        SCEN[n]()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
