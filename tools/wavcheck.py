#!/usr/bin/env python3
"""Sample-level checks on test renders (32-bit float WAVs from the sim/ tests). Channel 1 only.

  python tools/wavcheck.py beats  f.wav [start=0.9] [beat=0.5]   peaks per 50 ms, one row per beat (+NaN count)
  python tools/wavcheck.py clicks f.wav [t0] [t1] [thr=0.07]       sample-to-sample jumps above thr
  python tools/wavcheck.py freq   f.wav t0 t1 [win=0.04]          zero-crossing frequency + peak per window
  python tools/wavcheck.py holds  f.wav t0 t1 [step=256]           hold-run lengths (decimation) + grid check (bitcrush)
  python tools/wavcheck.py spec   f.wav t0 t1 [win=0.25]          rms, top 3 spectral peaks, octave-band dB (numpy)

Notes: a full-scale 440 Hz sine moves at most ~0.058/sample, so 'clicks' at 0.07 only flags real discontinuities
(lower thr for quieter or higher signals). WAV time 0 = DSP start (= logical 0.3 s in the test scripts).
"""
import math
import sys

from wavpeaks import readwav


def ch1(path):
    ch, sr, v = readwav(path)
    return sr, v[0::ch]


def beats(path, start=0.9, beat=0.5):
    sr, x = ch1(path)
    print(path, f"{len(x) / sr:.2f}s", "NaN:", sum(1 for t in x if math.isnan(t)))
    seg = int(beat / 10 * sr)
    b = 0
    while int((start + b * beat) * sr) < len(x):
        s0 = int((start + b * beat) * sr)
        row = [max((abs(t) for t in x[s0 + k * seg:s0 + (k + 1) * seg]), default=0) for k in range(10)]
        print(f"{start + b * beat:6.2f}s", " ".join(f"{r:.2f}" for r in row))
        b += 1


def clicks(path, t0=0.0, t1=None, thr=0.07):
    sr, x = ch1(path)
    t1 = len(x) / sr if t1 is None else t1
    hits = [(i / sr, abs(x[i] - x[i - 1])) for i in range(max(1, int(t0 * sr)), min(len(x), int(t1 * sr)))
            if abs(x[i] - x[i - 1]) > thr]
    print(f"{path} {t0}-{t1}s: {len(hits)} jumps > {thr}")
    for t, d in hits[:20]:
        print(f"  {t:.4f}s jump {d:.3f}")


def freq(path, t0, t1, win=0.04):
    sr, x = ch1(path)
    t = t0
    while t + win <= t1:
        seg = x[int(t * sr):int((t + win) * sr)]
        zc = sum(1 for i in range(1, len(seg)) if seg[i - 1] < 0 <= seg[i])
        pk = max(abs(s) for s in seg)
        print(f"  {t:.3f}s {zc / win:6.0f} Hz  peak {pk:.3f}")
        t += win


def holds(path, t0, t1, step=256):
    sr, x = ch1(path)
    x = x[int(t0 * sr):int(t1 * sr)]
    runs, r = {}, 1
    for a, b in zip(x, x[1:]):
        if a == b:
            r += 1
        else:
            runs[r] = runs.get(r, 0) + 1
            r = 1
    print("hold-run histogram (len: count):", dict(sorted(runs.items())[:12]))
    vals = [abs(t) * step for t in x if t != 0]
    off = sum(1 for s in vals if abs(s - round(s)) > 1e-3)
    print(f"samples {len(x)}, off the 1/{step} grid: {off} of {len(vals)}")


def spec(path, t0, t1, win=0.25):
    import numpy as np
    sr, x = ch1(path)
    x = np.asarray(x, dtype=float)
    edges = [62.5 * 2 ** k for k in range(9)]          # octave bands 62.5 Hz .. 16 kHz
    print("  time    rms   peaks (Hz)            octave bands dB from " + " ".join(f"{e:g}" for e in edges[:-1]))
    t = t0
    while t + win <= t1 + 1e-9:
        seg = x[int(t * sr):int((t + win) * sr)]
        mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        fr = np.fft.rfftfreq(len(seg), 1 / sr)
        pk = [i for i in range(1, len(mag) - 1) if mag[i] >= mag[i - 1] and mag[i] > mag[i + 1]]
        top = sorted(pk, key=lambda i: -mag[i])[:3]
        db = [10 * np.log10(np.sum(mag[(fr >= a) & (fr < b)] ** 2) + 1e-12) for a, b in zip(edges, edges[1:])]
        rms = float(np.sqrt(np.mean(seg ** 2)))
        print(f"  {t:5.2f}s {rms:.3f}  " + " ".join(f"{fr[i]:6.0f}" for i in sorted(top)).ljust(22)
              + " ".join(f"{d:5.0f}" for d in db))
        t += win


if __name__ == "__main__":
    cmd, path, *rest = sys.argv[1:]
    args = [float(a) for a in rest]
    {"beats": beats, "clicks": clicks, "freq": freq, "holds": holds, "spec": spec}[cmd](path, *args)
