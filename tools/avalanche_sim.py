#!/usr/bin/env python3
"""Offline tests of instr/avalanche.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/avalanche_sim.py [scenario ...]
  python tools/avalanche_sim.py m609

  rate      OSC1 alone (no cross-mod, steady): tone range at C3, 1V/oct; rhythm range at 4 Hz
  crossmod  Size: OSC1 kicking OSC2 changes the rhythm (more distinct gaps between hits)
  starve    Speed: slower as it starves, silent past the threshold
  steady    Freeze: the jitter stops; the rhythm settles into a repeating cycle
  kick      Reset: every oscillator fires at once (a hit on the trigger)
  pulse     the Pulse jack: TR gates when the engine peaks
  shutter   Overlap: the shutter (OSC4) interrupts the sound
  fuzz      Blend: ZZ is fuzzed and smoothed (less top than NM)
  source    Source: a loud input starves it
  reverb    alt Blend: a stereo reverb
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles and sounds
Renders go to firmware/dist/avalanche_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "avalanche_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "avalanche.instr")
SR = 48000
C3 = 130.813
# a quiet start: OSC1 alone, no cross-mod, no shutter, steady
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0\ngkloopsize = 0\ngkdensity = 1\ngkwindow = 0.3\n"
        "gkoverlap = 0\ngkblend = 0\ngkfreeze = 1\ngkrecord = 0\ngksource = 0\ngkreset = 0\n")
ALTS = "start_alt=1 size_alt=0 window_alt=0.5 blend_alt=0"
RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    import wave
    t = np.arange(70 * SR) / SR
    for name, sig in (("in_silence.wav", np.zeros_like(t)), ("in_loud.wav", 0.6 * np.sin(2 * np.pi * 220 * t))):
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


def onsets(x, t0, t1, ch=0):
    """Discharge spikes: jumps in the high band (each firing is a sharp edge)."""
    s = seg(x, t0, t1, ch)
    d = np.abs(np.diff(s))
    thr = max(0.3 * d.max(), 0.02)                   # (an absolute floor: in near-silence noise isn't a hit)
    idx = np.flatnonzero(d > thr)
    out = []
    for i in idx:
        if not out or i - out[-1] > int(0.01 * SR):
            out.append(i)
    return np.array(out) / SR + t0


def sc_rate():
    print("rate")
    auto = pulses(1.2, name="gkfilestate") + steps("gkpitch", (0, 0.6), (4, 0.8))
    (x, _) = run("rate_tone", 7, auto)
    a, b = near_peak(x, 1.8, 3.9, C3, tol=0.03)[0], near_peak(x, 4.5, 6.9, 2 * C3, tol=0.03)[0]
    check("tone range, OSC1 alone: C3 at the click, C4 at +0.2 (within 1 %)",
          abs(a / C3 - 1) < 0.01 and abs(b / (2 * C3) - 1) < 0.01, "%.2f, %.2f Hz" % (a, b))
    (y, _) = run("rate_rhythm", 6, "gkdensity = 0\n", alts=ALTS.replace("start_alt=1", "start_alt=0"))
    on = onsets(y, 1.5, 5.9)
    ioi = np.diff(on)
    # OSC1 at 4 Hz with OSC2 and OSC3 at a quarter of it: the most common gap is OSC1's 0.25 s
    med = float(np.median(ioi)) if len(ioi) else 0
    hist = np.round(ioi / 0.005) * 0.005
    vals, cnt = np.unique(hist, return_counts=True)
    common = float(vals[np.argmax(cnt)]) if len(vals) else 0
    check("rhythm range: OSC1 fires at 4 Hz at the click (the commonest gap 0.25 s, within 4 %)",
          abs(common / 0.25 - 1) < 0.04, "commonest gap %.3f s (%d hits)" % (common, len(on)))


def sc_crossmod():
    print("crossmod")
    auto = "gkdensity = 0.4\n"
    (x, _) = run("xm0", 8, auto)
    (y, _) = run("xm1", 8, auto + "gkloopsize = 1\ngkloopstart = 0.6\n")

    def hist(z):
        ioi = np.diff(onsets(z, 1.5, 7.9))
        h, _ = np.histogram(ioi, bins=np.arange(0, 1.0, 0.02))
        return h / max(1, h.sum())
    d = 0.5 * float(np.abs(hist(x) - hist(y)).sum())
    # (coupled relaxation oscillators lock to each other, so a strong kick can make the rhythm simpler as well as
    # wilder: the check is that it changes)
    check("cross-mod: the rhythm changes (the gaps distribution moves > 0.25 of the way)", d > 0.25, "%.2f" % d)


def sc_starve():
    print("starve")
    auto = steps("gkspeed", (0, 0.5), (4, 0.3), (7, 0.1))
    (x, _) = run("starve", 10, auto)
    n0 = len(onsets(x, 1.5, 3.9))
    n1 = len(onsets(x, 4.5, 6.9))
    q = db(rms(x, 8, 9.9)) - db(rms(x, 1.5, 3.9))
    check("Speed: starving slows it (fewer hits)", n1 < 0.8 * n0, "%d -> %d hits in 2.4 s" % (n0, n1))
    check("and past the threshold it falls silent (> 30 dB down)", q < -30, "%+.1f dB" % q)


def sc_steady():
    print("steady")
    auto = "gkdensity = 0.4\ngkloopsize = 0.8\ngkloopstart = 0.5\ngkfreeze = (kt > 6 ? 1 : 0)\n"
    (x, _) = run("steady", 12, auto)

    def periodic(t0, t1):
        s = np.abs(seg(x, t0, t1))
        w = int(0.005 * SR)
        e = np.convolve(s, np.ones(w) / w, "same")[::w]
        e = e - e.mean()
        ac = np.correlate(e, e, "full")[len(e) - 1:]
        ac = ac / ac[0]
        return float(ac[int(0.3 / 0.005):int(2.5 / 0.005)].max())
    a, b = periodic(1.5, 5.9), periodic(7.5, 11.9)
    check("Freeze: steady, the rhythm repeats (envelope autocorrelation peak up, > 0.8)", b > 0.8 and b > a,
          "%.2f -> %.2f" % (a, b))


def sc_kick():
    print("kick")
    auto = "gkdensity = 0.4\ngkloopsize = 0.5\n" + pulses(3.137)
    (x, _) = run("kick", 5, auto)
    on = onsets(x, 3.0, 3.3)
    check("Reset: a hit on the trigger (within 15 ms)", len(on) > 0 and min(abs(on - 3.137)) < 0.015,
          "hits at %s" % [round(o, 3) for o in on])


def sc_pulse():
    print("pulse")
    log = os.path.join(OUT, "pulse_log.txt")
    if os.path.exists(log):
        os.remove(log)
    auto = ("gkdensity = 0.5\ngkloopsize = 1\ngkloopstart = 0.8\ngkfreeze = 0\n" + pulses(2.5, 3.5, 4.5) +
            "kge changed gkeol\nif kge == 1 && gkeol == 1 then\n    fprintks \"pulse_log.txt\", \"%f\\n\", kt\nendif\n")
    run("pulse", 6, auto)
    ts = [float(l) for l in open(log)] if os.path.exists(log) else []
    near = [t for t in ts if min(abs(t - k) for k in (2.5, 3.5, 4.5)) < 0.02]
    check("the Pulse jack: TR gates when oscillators fire together (every kick, and more)", len(near) >= 3 and len(ts) > 3,
          "%d gates, %d at the kicks" % (len(ts), len(near)))


def sc_shutter():
    print("shutter")
    auto = "gkdensity = 0.4\ngkwindow = 0.15\n"   # the shutter at 0.4 Hz
    (x, _) = run("sh0", 8, auto)
    (y, _) = run("sh1", 8, auto + "gkoverlap = 1\n")

    def depth(z):
        s = np.abs(seg(z, 1.5, 7.9))
        w = int(0.1 * SR)
        e = np.convolve(s, np.ones(w) / w, "same")[::w // 4]
        return float(db(np.percentile(e, 90)) - db(np.percentile(e, 10) + 1e-6))
    a, b = depth(x), depth(y)
    check("Overlap: the shutter interrupts the sound (the envelope's range > 10 dB wider)", b - a > 10, "%.1f -> %.1f dB" % (a, b))


def sc_fuzz():
    print("fuzz")
    auto = pulses(1.2, name="gkfilestate") + steps("gkblend", (0, 0), (4, 1))
    (x, _) = run("fuzz", 7, auto)

    def top(t0, t1):
        f, p = psd(x, t0, t1)
        return 10 * np.log10(band(f, p, 5000, 15000) / band(f, p, 50, 15000))
    a, b = top(1.8, 3.9), top(4.5, 6.9)
    check("Blend: ZZ is smoothed (the share above 5 kHz down > 10 dB)", a - b > 10, "%+.1f -> %+.1f dB" % (a, b))


def sc_source():
    print("source")
    (x, _) = run("source", 7, "gkdensity = 0.4\ngksource = (kt > 4 ? 1 : 0)\n", wav="in_loud.wav")
    n0, n1 = len(onsets(x, 1.5, 3.9)), len(onsets(x, 4.5, 6.9))
    check("Source: a loud input starves it (far fewer hits)", n1 < 0.5 * n0, "%d -> %d hits" % (n0, n1))


def sc_reverb():
    print("reverb")
    auto = "gkdensity = 0.4\n"
    (x, _) = run("rev0", 5, auto)
    (y, _) = run("rev1", 5, auto, alts=ALTS.replace("blend_alt=0", "blend_alt=1"))

    def corr(z):
        return float(np.corrcoef(seg(z, 2, 4.9, 0), seg(z, 2, 4.9, 1))[0, 1])
    a, b = corr(x), corr(y)
    check("alt Blend: a stereo reverb (L/R correlation 1 -> < 0.95)", a > 0.99 and b < 0.95, "%.3f -> %.3f" % (a, b))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkblend = frac(kt * 0.04)\n"
            "gkrecord = (frac(kt * 0.07) > 0.5 ? 1 : 0)\ngkfreeze = (frac(kt * 0.045) > 0.6 ? 1 : 0)\n"
            "gksource = (frac(kt / 11) > 0.5 ? 1 : 0)\ngkreset = (frac(kt * 0.7) < 0.02 ? 1 : 0)\n"
            "gkfilestate = (frac(kt * 0.1) < 0.02 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\n"
            "gkwindow_alt = frac(kt * 0.08)\ngkblend_alt = frac(kt * 0.02)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_loud.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN, ran to the end (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0 and len(x) > 61 * SR,
          "peak %.3f, NaN %d, %.1f s" % (float(np.nanmax(np.abs(s))), nan, len(x) / SR))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_loud.wav"), "looper")
    print("  CPU for 62 s: avalanche %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper (with the reverb)", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 4, BASE + "gkdensity = 0.4\ngkloopsize = 0.5\ngkfreeze = 0\n", sets=ALTS,
                     wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "4", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    check("6.09: compiles and sounds (rms > 0.02, no NaN)", ok and rms(x, 1.5, 3.9) > 0.02 and not np.isnan(x).any(),
          "rms %.3f" % rms(x, 1.5, 3.9))


def main():
    make_inputs()
    want = sys.argv[1:] or ["rate", "crossmod", "starve", "steady", "kick", "pulse", "shutter", "fuzz", "source",
                            "reverb", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
