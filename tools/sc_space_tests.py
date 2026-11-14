#!/usr/bin/env python3
"""Offline tests of sc/08_sc_space.scd: NRT renders in SuperCollider 3.10.4 + sc3-plugins (Greyhole, JPverb).

  python tools/sc_space_tests.py [scenario ...]

  decay    reverb only: the tail's T60 follows Window (about 1.5 s and 12 s), within 50 %
  delays   delays only, no diffusion: echoes Start's time (250 ms) + Greyhole's size offset apart
  freeze   Freeze: the tail holds (within 1.5 dB over 8 s), a new tone doesn't go in; Reset clears a hold
  duck     Record: the space is quieter while the input plays than in its gaps (6 dB more than without)
  clear    Reset: the tail drops by more than 30 dB within 0.3 s; a new burst sounds again
  shimmer  Source: an octave above the input rings in the space
  tone     Pitch clockwise = brighter tail than anticlockwise
  level    everything moving: bounded, no NaN; NRT time against 04_sc_cloud
Renders go to firmware/dist/sc_tests/.
"""
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sc_nrt_tests as N   # noqa: E402
import sctest              # noqa: E402

SR = 48000
FAILS = []
PATCH = os.path.join(ROOT, "sc", "08_sc_space.scd").replace("\\", "/")
CLOUD = os.path.join(ROOT, "sc", "04_sc_cloud.scd").replace("\\", "/")


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


def make_inputs():
    os.makedirs(N.OUT, exist_ok=True)
    rng = np.random.default_rng(7)
    n = 30 * SR
    t = np.arange(n) / SR

    def burst(at, dur=0.05, amp=0.5):
        x = np.zeros(n)
        a = int(at * SR)
        x[a:a + int(dur * SR)] = amp * rng.standard_normal(int(dur * SR))
        return x
    N.write_wav(N.OUT + "/spin_burst.wav", [(burst(1.0) + burst(5.0)).astype(np.float32)] * 2)
    fr = 0.3 * rng.standard_normal(n) * (t < 3) + 0.3 * np.sin(2 * np.pi * 1000 * t) * ((t > 4) & (t < 10))
    N.write_wav(N.OUT + "/spin_freeze.wav", [fr.astype(np.float32)] * 2)
    du = 0.3 * rng.standard_normal(n) * ((t % 1) < 0.5)
    N.write_wav(N.OUT + "/spin_duck.wav", [du.astype(np.float32)] * 2)
    si = 0.3 * np.sin(2 * np.pi * 440 * t) * ((t > 1) & (t < 3))
    N.write_wav(N.OUT + "/spin_sine.wav", [si.astype(np.float32)] * 2)
    mx = 0.3 * rng.standard_normal(n) * ((t % 2) < 0.3) + 0.2 * np.sin(2 * np.pi * 220 * t)
    N.write_wav(N.OUT + "/spin_mix.wav", [mx.astype(np.float32)] * 2)


def render(name, init, events, dur, inp, patch=PATCH, synth="~neb.name"):
    wav = "%s/%s.wav" % (N.OUT, name)
    if os.path.exists(wav):
        os.remove(wav)
    args = "".join(", \\%s, %r" % (k, float(v)) for k, v in init.items())
    rows = ["[0.0, ['/d_recv', ~neb.def.asBytes]]", "[0.001, [\\s_new, %s, 1000, 0, 0%s]]" % (synth, args)]
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
SystemClock.sched(200, { "SCNRT timeout".postln; 1.exit; nil });
""" % (patch, ",\n".join(rows), wav, "%s/%s" % (N.OUT, inp), float(dur))
    path = "%s/%s.scd" % (N.OUT, name)
    open(path, "w").write(scd)
    t0 = time.time()
    code, out = sctest.sclang(path, 240)
    el = time.time() - t0
    open("%s/%s.log" % (N.OUT, name), "w").write(out)
    if not os.path.exists(wav) or "ERROR" in out:
        print(out[-1500:])
        raise SystemExit("no render for " + name)
    return N.read_wav(wav)[0], el


BASE = dict(blend=1, speed=0.5, pitch=0.6, start=0.5, size=0.5, density=0.6, overlap=0.4, window=0.5,
            start_alt=0.5, size_alt=1, density_alt=0.7, window_alt=0.4, overlap_alt=0.5, blend_alt=0.4)


def env_db(x, w=0.02):
    m = x.mean(axis=1)
    n = int(w * SR)
    k = len(m) // n
    return 10 * np.log10((m[:k * n].reshape(k, n) ** 2).mean(axis=1) + 1e-20)


def t60(x, t0, t1):
    """Schroeder backward integration from t0 to t1; the slope between -5 and -25 dB, as a T60."""
    m = x[int(t0 * SR):int(t1 * SR)].mean(axis=1) ** 2
    edc = np.cumsum(m[::-1])[::-1]
    edc = 10 * np.log10(edc / edc[0] + 1e-30)
    a, b = np.searchsorted(-edc, 5), np.searchsorted(-edc, 25)
    if b <= a:
        return float("nan")
    return 60 * (b - a) / SR / 20


def rms_db(x, t0, t1):
    return 10 * np.log10(np.mean(N.seg(x, t0, t1) ** 2) + 1e-20)


def level_at(x, t0, t1, f0, bw=6):
    m = N.seg(x, t0, t1).mean(axis=1)
    sp = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1 / SR)
    return 20 * np.log10(sp[(f > f0 - bw) & (f < f0 + bw)].max() + 1e-12)


def centroid(x, t0, t1):
    m = N.seg(x, t0, t1).mean(axis=1)
    sp = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1 / SR)
    return float((sp * f).sum() / sp.sum())


def sc_decay():
    print("[decay]")
    res = []
    for w, nominal, dur in ((0.3, 0.3 * 200 ** 0.3, 6), (0.7, 0.3 * 200 ** 0.7, 16)):
        x, _ = render("sp_decay%d" % int(w * 10), dict(BASE, window=w, start_alt=1), [], dur, "spin_burst.wav")
        r = t60(x, 1.1, 4.9 if dur == 6 else dur - 0.1)
        res.append(r)
        check(0.5 * nominal < r < 1.5 * nominal, f"Window {w}: T60 {r:.2f} s (nominal {nominal:.2f})")
    check(res[1] > 4 * res[0], f"Window clockwise rings much longer ({res[0]:.2f} -> {res[1]:.2f} s)")


def sc_delays():
    print("[delays]")
    # Greyhole: echoes delayTime + about 0.065 s x size apart (size 0.5 -> 1.58: +0.1 s); Start -> 0.25 s
    st = np.log(0.25 / 0.02) / np.log(1.4 / 0.02)
    x, _ = render("sp_delays", dict(BASE, start=st, start_alt=0, density=0, overlap=0.5), [], 4.5, "spin_burst.wav")
    e = env_db(N.seg(x, 1.0, 4.5), 0.005)
    pk = [i for i in range(1, len(e) - 1) if e[i] > e[i - 1] and e[i] >= e[i + 1] and e[i] > e.max() - 25]
    # echoes: peaks at least 100 ms apart
    ech = []
    for i in pk:
        if not ech or i - ech[-1] > 20:
            ech.append(i)
    sp = np.diff(ech[:5]) * 0.005
    check(len(sp) >= 2 and abs(np.median(sp) - 0.35) < 0.05,
          f"echo spacing {np.round(sp, 3).tolist()} s (Start = 250 ms, + Greyhole's 0.1 s at this size)")


def sc_freeze():
    print("[freeze]")
    x, _ = render("sp_freeze", dict(BASE, window=0.4, start_alt=0.8),
                  [(2.8, dict(freeze=1)), (14.0, dict(freeze=0)), (16.0, dict(freeze=1, t_reset=1))], 20,
                  "spin_freeze.wav")
    a, b = rms_db(x, 4.0, 5.0), rms_db(x, 12.0, 13.0)
    check(abs(b - a) < 1.5 and a > -40, f"held: {a:.1f} dB at 4-5 s, {b:.1f} dB at 12-13 s")
    c = rms_db(x, 17.0, 19.0)
    check(c < a - 40, f"Reset while frozen: the hold lets go and stays clear ({c:.1f} dB)")
    m = N.seg(x, 6, 10).mean(axis=1)
    sp = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1 / SR)
    line = level_at(x, 6, 10, 1000) - 20 * np.log10(np.median(sp[(f > 800) & (f < 1200)]) + 1e-12)
    check(line < 20, f"a new 1 kHz tone doesn't go in (its line {line:.0f} dB over the band)")


def sc_duck():
    print("[duck]")
    res = []
    for rec in (0, 1):
        x, _ = render("sp_duck%d" % rec, dict(BASE, record=rec, density_alt=1, window_alt=0.2, window=0.6), [], 10,
                      "spin_duck.wav")
        on = np.mean([rms_db(x, k + 0.15, k + 0.45) for k in range(3, 9)])
        off = np.mean([rms_db(x, k + 0.65, k + 0.95) for k in range(3, 9)])
        res.append(off - on)
    check(res[1] - res[0] > 6, f"Record: the space ducks under the input (gaps over playing {res[0]:+.1f} dB off, "
                               f"{res[1]:+.1f} dB on)")


def sc_clear():
    print("[clear]")
    x, _ = render("sp_clear", dict(BASE, window=0.9, start_alt=0.8), [(3.0, dict(t_reset=1))], 7, "spin_burst.wav")
    a, b, c = rms_db(x, 2.7, 2.95), rms_db(x, 3.3, 3.4), rms_db(x, 5.1, 5.6)
    check(a - b > 30, f"Reset: the tail drops {a - b:.0f} dB in 0.3 s")
    check(c > a - 6, f"a new burst sounds again ({c:.1f} dB, before the clear {a:.1f})")


def sc_shimmer():
    print("[shimmer]")
    res = []
    for src in (0, 1):
        x, _ = render("sp_shim%d" % src, dict(BASE, source=src, blend_alt=1, window=0.8, start_alt=1), [], 7,
                      "spin_sine.wav")
        res.append(level_at(x, 3.5, 6.5, 880) - level_at(x, 3.5, 6.5, 440))
    check(res[1] - res[0] > 15, f"Source: the octave (880 Hz) rings in the tail ({res[0]:.0f} dB under 440 off, "
                                f"{res[1]:.0f} dB on)")


def sc_tone():
    print("[tone]")
    cs = []
    for p in (0.2, 0.9):
        x, _ = render("sp_tone%d" % int(p * 10), dict(BASE, pitch=p, start_alt=1), [], 5, "spin_burst.wav")
        cs.append(centroid(x, 1.5, 4.5))
    check(cs[1] > 1.5 * cs[0], f"Pitch CW brighter than CCW (centroid {cs[0]:.0f} -> {cs[1]:.0f} Hz)")


def sc_level():
    print("[level]")
    ev = [(0.5 + 0.5 * k, dict(size=(k * 0.13) % 1, density=(k * 0.29) % 1, start=(k * 0.17) % 1,
                               window=(k * 0.23) % 1, overlap=(k * 0.31) % 1, speed=(k * 0.11) % 1,
                               pitch=(k * 0.07) % 1.3 - 0.2, blend=(k * 0.19) % 1, freeze=(k // 5) % 2,
                               source=(k // 4) % 2, record=(k // 3) % 2, size_alt=(k * 0.37) % 1,
                               start_alt=(k * 0.41) % 1, blend_alt=1, overlap_alt=(k * 0.43) % 1,
                               t_reset=1 if k % 9 == 8 else 0)) for k in range(38)]
    ev.append((19.5, dict(overlap=1, density=0.99, window=1, freeze=0, size=1, source=1, blend_alt=1, record=0)))
    x, el = render("sp_level", BASE, ev, 30, "spin_mix.wav")
    check(not np.isnan(x).any() and float(np.abs(x).max()) <= 0.96 and N.rms(x[SR:]) > 0.01,
          f"everything moving (then everything up for 10 s): bounded, no NaN (peak {np.abs(x).max():.3f}, "
          f"rms {N.rms(x[SR:]):.3f})")
    _, elc = render("sp_cloudref", {}, [], 30, "spin_mix.wav", patch=CLOUD)
    print(f"  info NRT time for 30 s: sc_space {el:.1f} s, 04_sc_cloud {elc:.1f} s (both include sclang start-up)")


SCEN = dict(decay=sc_decay, delays=sc_delays, freeze=sc_freeze, duck=sc_duck, clear=sc_clear, shimmer=sc_shimmer,
            tone=sc_tone, level=sc_level)

if __name__ == "__main__":
    make_inputs()
    for n in sys.argv[1:] or list(SCEN):
        SCEN[n]()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
