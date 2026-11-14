#!/usr/bin/env python3
"""Offline tests of instr/morph.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (wasm, from
Windows Python: the m609 scenario).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/morph_sim.py [scenario ...]
  python tools/morph_sim.py m609

Inputs: live.wav (left = A, right = the right input) and a stick file b.wav (a 660 Hz tone, 10 s); for m609 the
file is b44.wav (44.1 kHz). Uses tools/stretch_sim.py's CSD builder (the module's own wrapping, the file arrays).
  morph    Blend 0 -> A (440 Hz), 1 -> B (660 Hz); Speed centre freezes B (still sounds)
  cross    Blend 0 + Overlap 1: A's partials (a 220 Hz saw) shaped by B's amplitudes (noise gated on/off)
  freeze   Freeze holds A (440) while the input moves on to 880
  pitch    Pitch 0.8 = +12 on the morph (A 440 -> 880)
  source   Source on: B = the right input (330 Hz)
  grab     Record: B = the last seconds of A (550 Hz) after A moved on (770 Hz)
  full     everything moving: level, NaN, clicks; CPU against the factory granular looper
  m609     Csound 6.09.1: compiles, B from a 44.1 kHz file in tune (the module's mincer reads tables at sr)
Renders go to firmware/dist/morph_sim/.
"""
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "morph_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "morph.instr")
SR = 48000
BASE = ("gkspeed = 0.625\ngkloopstart = 0\ngkloopsize = 1\ngkpitch = 0.6\ngkdensity = 1\ngkwindow = 0\n"
        "gkoverlap = 0\ngkfreeze = 0\ngksource = 0\n")
ALTS = "start_alt=0.5 size_alt=0.3 density_alt=0.5 window_alt=0.5 overlap_alt=0.5 blend_alt=0.0 pitch_alt=0.5"
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def stereo(path, l, r, sr=SR):
    data = (np.clip(np.stack([l, r], axis=1), -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def sine(f, t0, t1, n, amp=0.4):
    t = np.arange(n) / SR
    return np.where((t >= t0) & (t < t1), amp * np.sin(2 * np.pi * f * t), 0.0)


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    n = 20 * SR
    t = np.arange(10 * SR) / SR
    S.write_wav(os.path.join(OUT, "b.wav"), 0.4 * np.sin(2 * np.pi * 660 * t), SR)
    t44 = np.arange(10 * 44100) / 44100
    S.write_wav(os.path.join(OUT, "b44.wav"), 0.4 * np.sin(2 * np.pi * 660 * t44), 44100)
    stereo(os.path.join(OUT, "a440.wav"), sine(440, 0, 20, n), sine(330, 0, 20, n))
    stereo(os.path.join(OUT, "afrz.wav"), sine(440, 0, 4, n) + sine(880, 4, 20, n), np.zeros(n))
    stereo(os.path.join(OUT, "agrab.wav"), sine(550, 0, 4, n) + sine(770, 4, 20, n), np.zeros(n))
    tt = np.arange(n) / SR
    saw = 0.3 * (2 * ((tt * 220) % 1) - 1)
    stereo(os.path.join(OUT, "asaw.wav"), saw, np.zeros(n))
    # B for cross: noise gated 0.5 s on / 0.5 s off
    rng = np.random.default_rng(1)
    gate = ((t % 1) < 0.5).astype(float)
    S.write_wav(os.path.join(OUT, "bnoise.wav"), 0.3 * rng.standard_normal(len(t)) * gate, SR)
    # a broadband B for the full run: a saw chord + noise with a slow swell (cross-synthesis needs an envelope)
    tb = np.arange(10 * SR) / SR
    chord = sum(2 * ((tb * f) % 1) - 1 for f in (110, 138.6, 164.8))
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * tb)
    S.write_wav(os.path.join(OUT, "bbusy.wav"), (0.1 * chord + 0.05 * rng.standard_normal(len(tb))) * swell, SR)
    busy = saw * 0.5 + 0.05 * rng.standard_normal(n)
    stereo(os.path.join(OUT, "abusy.wav"), np.tile(busy, 4)[:70 * SR], np.tile(busy[::-1], 4)[:70 * SR])


def clicks(x, t0, t1):
    """Isolated discontinuities: the 2nd difference above 6x its own local rms (50 ms) - noise-like (bright)
    material passes, a step or spike doesn't. (stretch_sim's fixed threshold flags any bright signal.)"""
    seg = x[int(t0 * SR):int(t1 * SR), 0]
    d2 = np.abs(np.diff(seg, 2))
    loc = np.sqrt(np.convolve(d2 ** 2, np.ones(2400) / 2400, "same")) + 1e-3
    return int(np.sum(d2 > 6 * loc))


def run(name, secs, auto, live, wav="b.wav"):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=ALTS, wav=wav)
    return S.render(csd, os.path.join(OUT, live), name)


def pf(x, t0, t1, lo=100, hi=2500):
    return S.peak_freq(x, t0, t1, lo, hi)[0]


def near(f, g, tol=0.03):
    return abs(f - g) <= tol * g


def sc_morph():
    print("morph")
    (x, _) = run("morph", 10, "gkblend = (kt < 4 ? 0 : 1)\ngkspeed = (kt < 7 ? 0.625 : 0.5)\n", "a440.wav")
    a, b, c = pf(x, 2.5, 3.8), pf(x, 5.0, 6.8), pf(x, 8.0, 9.8)
    check("Blend 0 = A (440 Hz)", near(a, 440), "%.1f" % a)
    check("Blend 1 = B (660 Hz)", near(b, 660), "%.1f" % b)
    lv = float(np.sqrt(np.mean(x[int(8 * SR):int(9.8 * SR), 0] ** 2)))
    check("Speed centre: B frozen, still sounding", near(c, 660) and lv > 0.05, "%.1f Hz, rms %.3f" % (c, lv))


def sc_cross():
    print("cross")
    (x, _) = run("cross", 8, "gkblend = 0\ngkoverlap = 1\n", "asaw.wav", wav="bnoise.wav")
    seg = x[int(2 * SR):int(7 * SR), 0]
    env = np.sqrt(np.convolve(seg ** 2, np.ones(2400) / 2400, "same"))
    on = np.mean(env[[int((k + 0.25) * SR) for k in range(4)]])
    off = np.mean(env[[int((k + 0.75) * SR) for k in range(4)]])
    check("B's amplitudes gate A (on/off follows B), at a usable level", on > 4 * off and on > 0.05,
          "on %.3f, off %.4f" % (on, off))
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    harm = sum(sp[(f > 220 * k - 3) & (f < 220 * k + 3)].sum() for k in range(1, 8))
    tot = sp[(f > 150) & (f < 1700)].sum()
    check("... with A's partials (220 Hz harmonics carry the energy)", harm > 0.3 * tot, "%.2f of 150-1700 Hz"
          % (harm / tot))
    # B is gated hard on/off (by design of the test file): look inside the "on" halves only
    # the saw's own edges trip any 2nd-difference detector: compare with the input's count
    n = sum(clicks(x, k + 0.1, k + 0.4) for k in range(2, 7))
    a = S.read_wav(os.path.join(OUT, "asaw.wav"))
    na = sum(clicks(a, k + 0.1, k + 0.4) for k in range(2, 7))
    check("no extra discontinuities in cross-synthesis (vs the saw input itself)", n <= 1.05 * na + 5, "%d (input %d)" % (n, na))


def sc_freeze():
    print("freeze")
    (x, _) = run("freeze", 9, "gkblend = 0\ngkfreeze = (kt > 3 ? 1 : 0)\n", "afrz.wav")
    a, b = pf(x, 2.0, 2.9), pf(x, 5.0, 8.5)
    check("Freeze holds A's 440 after the input moves to 880", near(a, 440) and near(b, 440), "%.1f -> %.1f" % (a, b))


def sc_pitch():
    print("pitch")
    (x, _) = run("pitch", 6, "gkblend = 0\ngkpitch = (kt < 3 ? 0.6 : 0.8)\n", "a440.wav")
    a, b = pf(x, 1.5, 2.8), pf(x, 4.0, 5.8)
    check("Pitch 0.8: A 440 -> 880", near(a, 440) and near(b, 880), "%.1f -> %.1f" % (a, b))


def sc_source():
    print("source")
    (x, _) = run("source", 6, "gkblend = 1\ngksource = 1\n", "a440.wav")
    b = pf(x, 2.0, 5.5)
    check("Source on: B = the right input (330 Hz)", near(b, 330), "%.1f" % b)


def sc_grab():
    print("grab")
    (x, _) = run("grab", 10, "gkblend = (kt < 5 ? 0 : 1)\ngkrecord = (kt > 3.5 && kt < 3.52 ? 1 : 0)\n",
                 "agrab.wav")
    a, b = pf(x, 4.5, 4.95), pf(x, 6.0, 9.5)
    check("A is 770 by then; Record grabbed its 550 as B", near(a, 770) and near(b, 550), "A %.1f, B %.1f" % (a, b))


def sc_full():
    print("full (level, clicks, CPU)")
    auto = ("gkblend = 0.5 + 0.5 * sin(kt * 0.7)\ngkoverlap = 0.5 + 0.4 * sin(kt * 0.31)\n"
            "gkwindow = 0.4 + 0.3 * sin(kt * 0.2)\ngkpitch = 0.6 + (kt > 30 ? 0.1 : 0)\ngkdensity = 0.8\n"
            "gkspeed = 0.6\ngkloopstart = 0.2 + 0.1 * sin(kt * 0.3)\ngkloopsize = 0.5\n"
            "gkfreeze = (frac(kt / 10) > 0.8 ? 1 : 0)\ngkreset = (frac(kt / 4) < 0.01 ? 1 : 0)\n"
            "gkrecord = (frac(kt / 20) < 0.002 ? 1 : 0)\ngkblend_alt = 0.5\n")
    (x, cpu) = run("full", 70, auto, "abusy.wav", wav="bbusy.wav")
    seg = x[2 * SR:]
    pk, nan = float(np.max(np.abs(seg))), int(np.isnan(seg).sum())
    rms = float(np.sqrt(np.mean(seg ** 2)))
    check("level", 0.02 < rms and pk <= 1.0 and nan == 0, "rms %.3f, peak %.3f, NaN %d" % (rms, pk, nan))
    n = clicks(x, 2, 70)
    if n:
        seg = x[2 * SR:70 * SR, 0]
        d2 = np.abs(np.diff(seg, 2))
        print("  clicks at", [round(2 + i / SR, 3) for i in np.argsort(d2)[-3:]])
    check("no clicks", n == 0, "%d" % n)
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 70, lp, sets="start_alt=0", wav="b.wav"), os.path.join(OUT, "abusy.wav"),
                       "looper")
    print("  CPU for 70 s: morph %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.8x the factory looper", cpu < 1.8 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1, 44.1 kHz file)")
    auto = BASE + "gkblend = 1\n"
    csd = S.make_csd(INSTR, "m609", 8, auto, sets=ALTS, wav="b44.wav")
    s = open(csd).read().replace("giCapMax = 30 ", "giCapMax = 5 ")
    open(csd, "w").write(s)
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "b44.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "8", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    ok = any("compileOrc returned 0" in ln for ln in info)
    x = S.read_wav(out)
    b = pf(x, 3.0, 7.0)
    check("6.09: compiles, B (a 44.1 kHz file) plays in tune at 660 Hz", near(b, 660) and ok, "%.1f Hz %s" % (b, info))


def main():
    make_inputs()
    want = sys.argv[1:] or ["morph", "cross", "freeze", "pitch", "source", "grab", "full"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
