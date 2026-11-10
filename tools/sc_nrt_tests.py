#!/usr/bin/env python3
"""Offline tests of the uf2 SuperCollider instruments (sc/02..04): render each with scripted control changes in
SuperCollider 3.10.4 NRT (the module's version; PC and module renders match, SC probe 2026-11-10), then check the
audio.

  python tools/sc_nrt_tests.py            # all scenarios; WAVs in firmware/dist/sc_tests/

A patch file with ~nrtTest set only defines ~neb.def / ~neb.name, so the same file that runs on the module is
rendered here: every Nebulae control is a synth argument of the same name, set with /n_set at the given times
(reset = t_reset 1).
"""
import math
import os
import struct
import subprocess
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import sctest  # noqa: E402

OUT = os.path.join(REPO, "firmware", "dist", "sc_tests").replace("\\", "/")
SR = 48000
C4 = 261.6256


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def write_wav(path, chans):
    """float32 stereo WAV."""
    data = np.stack(chans, axis=1).astype("<f4").tobytes()
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<IHHIIHH", 16, 3, len(chans), SR, SR * 4 * len(chans), 4 * len(chans), 32))
        f.write(b"data" + struct.pack("<I", len(data)) + data)


def read_wav(path):
    with open(path, "rb") as f:
        b = f.read()
    pos, fmt, data = 12, None, None
    while pos < len(b):
        cid, size = b[pos:pos + 4], struct.unpack("<I", b[pos + 4:pos + 8])[0]
        body = b[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", body[:16])
        elif cid == b"data":
            data = body
        pos += 8 + size + (size & 1)
    tag, ch, sr, _, _, bits = fmt
    a = np.frombuffer(data, dtype="<f4" if bits == 32 and tag in (3, 0xFFFE) else "<i2")
    if a.dtype != np.float32:
        a = a.astype(np.float32) / 32768.0
    return a.reshape(-1, ch), sr


def render(patch, name, events, duration, init=None, input_wav=None):
    """events: [(time, {arg: value})]. Returns the stereo output array."""
    os.makedirs(OUT, exist_ok=True)
    wav = "%s/%s.wav" % (OUT, name)
    if os.path.exists(wav):
        os.remove(wav)
    init = init or {}
    s_new = "[\\s_new, ~neb.name, 1000, 0, 0%s]" % "".join(", \\%s, %r" % (k, float(v)) for k, v in init.items())
    rows = ["[0.0, ['/d_recv', ~neb.def.asBytes]]", "[0.0, %s]" % s_new]
    for t, sets in events:
        args = "".join(", \\%s, %r" % (k, float(v)) for k, v in sets.items())
        rows.append("[%r, [\\n_set, 1000%s]]" % (float(t), args))
    rows.append("[%r, [\\c_set, 0, 0]]" % float(duration))
    scd = """~nrtTest = true;
thisProcess.interpreter.executeFile("%s");
~score = Score([
%s
]);
~opts = ServerOptions.new.numOutputBusChannels_(2).numInputBusChannels_(2).memSize_(65536);
~score.recordNRT(outputFilePath: "%s", inputFilePath: %s, sampleRate: %d, headerFormat: "WAV",
    sampleFormat: "float", options: ~opts, duration: %r,
    action: { "SCNRT done".postln; 0.exit });
SystemClock.sched(120, { "SCNRT timeout".postln; 1.exit; nil });
""" % (os.path.join(REPO, "sc", patch).replace("\\", "/"), ",\n".join(rows), wav,
       '"%s"' % input_wav if input_wav else "nil", SR, float(duration))
    path = "%s/%s.scd" % (OUT, name)
    with open(path, "w") as f:
        f.write(scd)
    code, out = sctest.sclang(path, 150)
    if not os.path.exists(wav):
        print(out[-2000:])
        raise RuntimeError("no render for " + name)
    a, sr = read_wav(wav)
    assert sr == SR
    return a


def seg(a, t0, t1):
    return a[int(t0 * SR):int(t1 * SR)]


def rms(a):
    return float(np.sqrt(np.mean(np.square(a)))) if len(a) else 0.0


def peak_hz(a, lo=40, hi=4000):
    """Strongest spectral peak of the mono mix between lo and hi Hz (parabolic interpolation)."""
    x = a.mean(axis=1) if a.ndim == 2 else a
    x = x * np.hanning(len(x))
    n = 1 << int(math.ceil(math.log2(len(x) * 4)))
    spec = np.abs(np.fft.rfft(x, n))
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    band = (freqs >= lo) & (freqs <= hi)
    i = int(np.argmax(np.where(band, spec, 0)))
    if 0 < i < len(spec) - 1:
        y0, y1, y2 = np.log(spec[i - 1:i + 2] + 1e-12)
        i = i + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    return i * SR / n


def f0_hz(a, lo=60, hi=2000):
    """Fundamental by normalised autocorrelation (a plucked string's strongest partial needn't be the fundamental).
    Takes the first lag whose correlation is within 10 % of the best, so octave-up errors are avoided."""
    x = a.mean(axis=1) if a.ndim == 2 else a
    x = x - x.mean()
    n = len(x)
    spec = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(spec * np.conj(spec))[:n]
    ac = ac / (ac[0] + 1e-12)
    lmin, lmax = int(SR / hi), int(SR / lo)
    best = float(np.max(ac[lmin:lmax]))
    lag = next(l for l in range(lmin, lmax) if ac[l] >= 0.9 * best and ac[l] >= ac[l - 1] and ac[l] >= ac[l + 1])
    y0, y1, y2 = ac[lag - 1], ac[lag], ac[lag + 1]
    return SR / (lag + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2))


def onsets(a, frame=0.01, rise=1.8, floor=0.02):
    """Count note onsets on a 10 ms RMS envelope."""
    x = a.mean(axis=1) if a.ndim == 2 else a
    n = int(frame * SR)
    env = np.sqrt(np.mean(np.square(x[:len(x) // n * n].reshape(-1, n)), axis=1))
    return int(np.sum((env[1:] > rise * env[:-1]) & (env[1:] > floor)))


def cents(f, ref):
    return 1200 * math.log2(f / ref)


class Checks(object):
    def __init__(self):
        self.failed = 0

    def ok(self, cond, msg):
        print("  %s %s" % ("ok  " if cond else "FAIL", msg))
        self.failed += 0 if cond else 1

    def sane(self, a, name):
        self.ok(np.all(np.isfinite(a)), "%s: no NaN/inf" % name)
        self.ok(float(np.max(np.abs(a))) <= 0.96, "%s: peak %.3f <= 0.96 (limiter)" % (name, float(np.max(np.abs(a)))))


def main():
    c = Checks()

    print("02_sc_drift")
    a = render("02_sc_drift.scd", "drift", [
        (3.0, {"pitch": 0.8}),                        # +1 octave
        (5.0, {"freeze": 1}),                         # sub octave on
        (7.0, {"start": 0.5, "density": 0.9, "window": 0.8, "overlap": 0.8, "size": 0.9, "source": 1}),
        (9.0, {"t_reset": 1}),
    ], 11.0, init={"start": 1.0, "density": 0.7, "overlap": 0.0, "size": 0.0})
    c.sane(a, "drift")
    f1 = peak_hz(seg(a, 1.0, 2.8))
    c.ok(abs(cents(f1, C4)) < 10, "drift: sine at pitch 0.6 = %.1f Hz (C4 %.1f, %+.1f cents)" % (f1, C4, cents(f1, C4)))
    f2 = peak_hz(seg(a, 3.3, 4.8))
    c.ok(abs(cents(f2, 2 * C4)) < 10, "drift: pitch 0.8 = %.1f Hz (1 octave up, %+.1f cents)" % (f2, cents(f2, 2 * C4)))
    sub = peak_hz(seg(a, 5.5, 6.8), 100, 400)
    c.ok(abs(cents(sub, C4)) < 15, "drift: freeze adds the sub octave (%.1f Hz = C4 under C5)" % sub)
    c.ok(rms(seg(a, 7.5, 8.9)) > 0.05, "drift: pulse + chord + resonance still sounds (rms %.3f)" % rms(seg(a, 7.5, 8.9)))
    dip = rms(seg(a, 9.02, 9.1)) < 0.6 * rms(seg(a, 8.5, 8.98))
    c.ok(dip and rms(seg(a, 10.6, 11.0)) > 0.6 * rms(seg(a, 8.5, 8.98)), "drift: reset swell dips and comes back")

    print("03_sc_strike")
    a = render("03_sc_strike.scd", "strike", [
        (0.5, {"t_reset": 1}),
        (2.5, {"pitch": 0.7}), (2.6, {"t_reset": 1}),                  # +6 semitones
        (4.5, {"pitch": 0.4}), (4.6, {"t_reset": 1}),                  # -12 semitones
        (6.5, {"pitch": 0.6, "size": 0.0}), (6.6, {"t_reset": 1}),     # short decay
        (8.5, {"size": 0.6, "record": 1, "speed": 0.5}),               # auto-pluck ~2.8 per second
        (11.0, {"record": 0, "freeze": 1}), (11.1, {"t_reset": 1}),    # sustain
    ], 14.0, init={"window": 0.0, "overlap": 0.0, "density": 0.8})
    c.sane(a, "strike")
    c.ok(rms(seg(a, 0.0, 0.45)) < 1e-4, "strike: silent until plucked")
    for t, ref, label in [(0.6, C4, "C4"), (2.7, midi_hz(66), "F#4"), (4.7, midi_hz(48), "C3")]:
        f = f0_hz(seg(a, t + 0.05, t + 0.55))
        c.ok(abs(cents(f, ref)) < 15, "strike: pluck at %.1f s = %.1f Hz (%s, %+.1f cents)" % (t, f, label, cents(f, ref)))
    c.ok(rms(seg(a, 7.6, 8.4)) < 0.1 * rms(seg(a, 6.62, 6.8)), "strike: size 0 = short decay")
    n = onsets(seg(a, 8.6, 10.9))
    c.ok(4 <= n <= 9, "strike: record = auto-pluck at ~2.8 per second (%d onsets in 2.3 s)" % n)
    c.ok(rms(seg(a, 13.0, 14.0)) > 0.3 * rms(seg(a, 11.3, 11.8)), "strike: freeze = sustain (rings on)")

    print("04_sc_cloud")
    inp = "%s/cloud_input.wav" % OUT
    os.makedirs(OUT, exist_ok=True)
    t = np.arange(int(10 * SR)) / SR
    tone = 0.4 * np.sin(2 * np.pi * 440 * t) * (t < 5.0)                # 440 Hz for 5 s, then silence
    write_wav(inp, [tone, tone])
    for freeze, name in [(0, "cloud"), (1, "cloud_freeze")]:
        a = render("04_sc_cloud.scd", name, [
            (2.5, {"pitch": 0.8}),                                       # grains +1 octave
            (4.5, {"pitch": 0.6, "freeze": freeze}),
        ], 9.0, init={"blend": 1.0, "density": 0.6, "size": 0.3, "start": 0.1, "window": 0.1}, input_wav=inp)
        c.sane(a, name)
        if not freeze:
            f = peak_hz(seg(a, 1.0, 2.4), 100, 3000)
            c.ok(abs(cents(f, 440)) < 15, "cloud: grains at pitch 0.6 follow the input (%.1f Hz)" % f)
            f = peak_hz(seg(a, 3.0, 4.4), 100, 3000)
            c.ok(abs(cents(f, 880)) < 15, "cloud: pitch 0.8 = one octave up (%.1f Hz)" % f)
            c.ok(rms(seg(a, 7.5, 9.0)) < 0.01, "cloud: no freeze -> silent once the input has been silent (rms %.4f)"
                 % rms(seg(a, 7.5, 9.0)))
        else:
            c.ok(rms(seg(a, 7.5, 9.0)) > 0.05, "cloud: freeze holds the buffer after the input stops (rms %.3f)"
                 % rms(seg(a, 7.5, 9.0)))

    print("%s" % ("ALL OK" if c.failed == 0 else "%d FAILED" % c.failed))
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
