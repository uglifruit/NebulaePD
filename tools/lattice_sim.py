#!/usr/bin/env python3
"""Offline tests of instr/lattice.instr through real Csound (WSL 6.18 + numpy), plus Csound 6.09.1 (m609).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/lattice_sim.py [scenario ...]
  python tools/lattice_sim.py m609

  echo      Plexus high: a click echoes at Size (120 ms at the click), and 240 ms at +0.2
  plexus    Plexus low: a dense reverb tail; high: sparse echoes
  decay     Decay: short -> long; at the top it rings on (super-infinite)
  color     Window: a darker tail below 1 o'clock, brighter above
  diffuse   Density: the first reflections soften (lower crest factor)
  couple    Speed: a left-only input stays left at 0, spreads right at 1
  skew      File: inverse skew sets left and right echo times apart
  send      Freeze held: what comes in meanwhile doesn't enter
  hold      Source: the network rings on
  clear     Reset: the network empties
  pulse     the Pulse jack: high while the network sounds
  sweep     every control at its extremes for 60 s: bounded, no NaN; CPU against the factory granular looper
  m609      Csound 6.09.1: compiles and runs
Renders go to firmware/dist/lattice_sim/.
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import stretch_sim as S   # noqa: E402
from radiate_sim import psd, band, steps, pulses, db, seg, rms   # noqa: E402

OUT = os.path.join(ROOT, "firmware", "dist", "lattice_sim")
S.OUT = OUT
INSTR = os.path.join(ROOT, "instr", "lattice.instr")
SR = 48000
BASE = ("gkspeed = 0.5\ngkpitch = 0.6\ngkloopstart = 0.3\ngkloopsize = 0.5\ngkdensity = 0\ngkwindow = 0.58\n"
        "gkoverlap = 0.55\ngkblend = 1\ngkfreeze = 0\ngkrecord = 0\ngksource = 0\ngkreset = 0\n")
ALTS = "start_alt=0.75 size_alt=0.3"
RESULTS = []
LAG = 32 / SR


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def make_inputs():
    os.makedirs(OUT, exist_ok=True)
    import wave
    n = 70 * SR
    t = np.arange(n) / SR
    rng = np.random.default_rng(9)
    click = np.zeros(n)
    click[int(1.5 * SR):int(1.5 * SR) + 24] = 0.8
    click2 = click.copy()
    click2[int(4.0 * SR):int(4.0 * SR) + 24] = 0.8
    noiseburst = 0.4 * rng.standard_normal(n) * ((t > 1.5) & (t < 1.7))
    sigs = {"in_click.wav": (click, click), "in_click2.wav": (click2, click2), "in_burst.wav": (noiseburst, noiseburst),
            "in_left.wav": (noiseburst, np.zeros(n)), "in_noise.wav": (0.1 * rng.standard_normal(n),) * 2,
            "in_silence.wav": (np.zeros(n), np.zeros(n))}
    for name, (l, r) in sigs.items():
        with wave.open(os.path.join(OUT, name), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(np.stack([l, r], 1), -1, 1) * 32767).astype("<i2").tobytes())
    S.write_wav(os.path.join(OUT, "dummy.wav"), np.zeros(SR), SR)


def run(name, secs, auto, alts=ALTS, wav="in_click.wav"):
    csd = S.make_csd(INSTR, name, secs, BASE + auto, sets=alts, wav="dummy.wav")
    return S.render(csd, os.path.join(OUT, wav), name)


def first_echo(x, t0, ch=0, after=0.004):
    s = np.abs(seg(x, t0 + after, t0 + 2, ch))
    thr = 0.3 * s.max()
    return after + float(np.argmax(s > thr)) / SR


def hi(x, t0, t1, lo=2000):
    f, p = psd(x, t0, t1)
    m = (f > 30) & (f < 14000)
    return float(10 * np.log10(np.sum(p[m & (f > lo)]) / np.sum(p[m]) + 1e-12))


def t30(x, t0, t1):
    s = seg(x, t0, t1)
    w = int(0.02 * SR)
    r = np.array([np.sqrt(np.mean(s[i:i + w] ** 2)) for i in range(0, len(s) - w, w)])
    ip = int(np.argmax(r))                              # (from the loudest point: the first 100 ms can be silent)
    below = np.flatnonzero(r[ip:] < r[ip] * 0.0316)
    return below[0] * 0.02 if len(below) else t1 - t0


def sc_echo():
    print("echo")
    got = []
    for name, p, want in (("echo0", 0.6, 0.12), ("echo1", 0.8, 0.24)):
        (x, _) = run(name, 3.5, "gkloopstart = 1\ngkoverlap = 0.4\ngkpitch = %g\n" % p)
        got.append((first_echo(x, 1.5), want + LAG))
    check("Plexus high: a click echoes at Size: 120 ms at the click, 240 ms at +0.2 (within 3 %)",
          all(abs(g / w - 1) < 0.03 for g, w in got), ", ".join("%.4f s" % g for g, _ in got))


def density(x, t0, t1):
    s = np.abs(seg(x, t0, t1))
    w = int(0.002 * SR)
    e = np.convolve(s, np.ones(w) / w, "same")[::w]
    pk = [i for i in range(1, len(e) - 1) if e[i] > e[i - 1] and e[i] >= e[i + 1] and e[i] > 0.1 * e.max()]
    return len(pk) / (t1 - t0)


def sc_plexus():
    print("plexus")
    (x, _) = run("plex0", 4, "gkloopstart = 0\ngkoverlap = 0.7\n")
    (y, _) = run("plex1", 4, "gkloopstart = 1\ngkoverlap = 0.7\n")
    a, b = density(x, 1.7, 2.7), density(y, 1.7, 2.7)
    check("Plexus low: a dense tail; high: sparse echoes (peaks per second, low > 3x high)", a > 3 * b,
          "%.0f vs %.0f per s" % (a, b))


def sc_decay():
    print("decay")
    (x, _) = run("dec0", 6, "gkloopstart = 0\ngkoverlap = 0.3\n")
    (y, _) = run("dec1", 6, "gkloopstart = 0\ngkoverlap = 0.85\n")
    (z, _) = run("dec2", 9, "gkloopstart = 0\ngkoverlap = 1\n")
    a, b = t30(x, 1.5, 5.9), t30(y, 1.5, 5.9)
    ref = db(rms(z, 1.6, 2.0))
    c = db(rms(z, 7.5, 8.9))
    check("Decay: the tail lengthens (-30 dB time x3)", b > 3 * a, "%.2f -> %.2f s" % (a, b))
    check("at the top it rings on (super-infinite: > -20 dB of its start 6 s later)", c > ref - 20,
          "%.1f vs %.1f dB" % (c, ref))


def sc_color():
    print("color")
    auto = "gkloopstart = 0\ngkoverlap = 0.8\n"
    (x, _) = run("col0", 5, auto + "gkwindow = 0.15\n", wav="in_burst.wav")
    (y, _) = run("col1", 5, auto + "gkwindow = 0.95\n", wav="in_burst.wav")
    a, b = hi(x, 2.2, 3.5), hi(y, 2.2, 3.5)
    check("Window: darker below 1 o'clock, brighter above (the tail's share above 2 kHz > 15 dB apart)", b - a > 15,
          "%+.1f vs %+.1f dB" % (a, b))


def sc_diffuse():
    print("diffuse")
    auto = "gkloopstart = 0\ngkoverlap = 0.5\ngkblend = 1\n"
    (x, _) = run("dif0", 3, auto)
    (y, _) = run("dif1", 3, auto + "gkdensity = 1\n")

    def crest(z):
        s = seg(z, 1.6, 1.7)                            # (the first pass through the network, wet only)
        return float(db(np.abs(s).max()) - db(np.sqrt(np.mean(s ** 2))))
    a, b = crest(x), crest(y)
    check("Density: diffusion softens the first reflections (crest factor down > 3 dB)", a - b > 3, "%.1f -> %.1f dB" % (a, b))


def sc_couple():
    print("couple")
    auto = "gkloopstart = 0\ngkoverlap = 0.7\n"
    (x, _) = run("cp0", 4, auto + "gkspeed = 0\n", wav="in_left.wav")
    (y, _) = run("cp1", 4, auto + "gkspeed = 1\n", wav="in_left.wav")
    a = db(rms(x, 2.0, 3.5, 1)) - db(rms(x, 2.0, 3.5, 0))
    b = db(rms(y, 2.0, 3.5, 1)) - db(rms(y, 2.0, 3.5, 0))
    check("Speed (Couple): a left-only input stays left at 0 (right > 40 dB down), spreads right at 1 (within 10 dB)",
          a < -40 and b > -10, "right vs left %+.1f -> %+.1f dB" % (a, b))


def sc_skew():
    print("skew")
    auto = "gkloopstart = 1\ngkoverlap = 0.4\n" + pulses(1.1, name="gkfilestate")
    (x, _) = run("skew", 3.5, auto, alts="start_alt=0.75 size_alt=0.6")
    l, r = first_echo(x, 1.5, 0), first_echo(x, 1.5, 1)
    check("File (inverse skew): left and right echo times apart (ratio > 1.5)", max(l, r) / min(l, r) > 1.5,
          "%.4f, %.4f s" % (l, r))


def sc_send():
    print("send")
    auto = "gkloopstart = 0\ngkoverlap = 0.3\ngkfreeze = (kt > 3.8 && kt < 4.5 ? 1 : 0)\n"
    (x, _) = run("send", 6, auto, wav="in_click2.wav")
    a, b = db(rms(x, 1.51, 1.9)), db(rms(x, 4.01, 4.4))
    check("Freeze held: a click meanwhile doesn't enter (> 30 dB under the one before)", b < a - 30, "%.1f vs %.1f dB" % (b, a))


def sc_hold():
    print("hold")
    (x, _) = run("hold", 8, "gkloopstart = 0\ngkoverlap = 0.3\ngksource = (kt > 1.55 ? 1 : 0)\n")
    a, b = db(rms(x, 1.6, 1.9)), db(rms(x, 6.5, 7.9))
    check("Source: the network rings on (> -20 dB of its start 5 s later, at a low Decay)", b > a - 20, "%.1f -> %.1f dB" % (a, b))


def sc_clear():
    print("clear")
    (x, _) = run("clear", 5, "gkloopstart = 0\ngkoverlap = 1\n" + pulses(3.0))
    a, b = db(rms(x, 2.5, 2.95)), db(rms(x, 3.3, 3.8))
    check("Reset: the network empties (> 40 dB down)", b < a - 40, "%.1f -> %.1f dB" % (a, b))


def sc_pulse():
    print("pulse")
    log = os.path.join(OUT, "pulse_log.txt")
    if os.path.exists(log):
        os.remove(log)
    auto = ("gkloopstart = 0\ngkoverlap = 0.3\n" +
            "kge changed gkeol\nif kge == 1 then\n    fprintks \"pulse_log.txt\", \"%f %d\\n\", kt, gkeol\nendif\n")
    run("pulse", 5, auto)
    rows = [l.split() for l in open(log)] if os.path.exists(log) else []
    on = [float(t) for t, v in rows if v == "1"]
    off = [float(t) for t, v in rows if v == "0"]
    check("the Pulse jack: high while the network sounds (high from the first echo, low as it dies away, no chatter)",
          len(on) >= 1 and 1.5 < on[0] < 1.7 and len(on) <= 2 and len(off) >= 1 and off[-1] > on[0] + 0.1,
          "on %s, off %s" % ([round(t, 2) for t in on], [round(t, 2) for t in off]))


def sc_sweep():
    print("sweep (stability, CPU)")
    auto = ("gkloopsize = frac(kt * 0.13)\ngkdensity = frac(kt * 0.17)\ngkwindow = frac(kt * 0.11)\n"
            "gkoverlap = frac(kt * 0.07)\ngkloopstart = frac(kt * 0.3)\ngkpitch = -0.3 + frac(kt * 0.05) * 1.6\n"
            "gkspeed = frac(kt * 0.09)\ngkblend = frac(kt * 0.04)\n"
            "gkfreeze = (frac(kt * 0.45) > 0.8 ? 1 : 0)\ngksource = (frac(kt / 11) > 0.7 ? 1 : 0)\n"
            "gkreset = (frac(kt * 0.2) < 0.02 ? 1 : 0)\ngkfilestate = (frac(kt * 0.1) < 0.02 ? 1 : 0)\n"
            "gkloopstart_alt = frac(kt * 0.05)\ngkloopsize_alt = frac(kt * 0.06)\n")
    (x, cpu) = run("sweep", 62, auto, wav="in_noise.wav")
    s = x[SR:]
    nan = int(np.isnan(s).sum())
    check("bounded, no NaN, ran to the end (60 s of extremes)", nan == 0 and float(np.nanmax(np.abs(s))) <= 1.0 and len(x) > 61 * SR,
          "peak %.3f, NaN %d, %.1f s" % (float(np.nanmax(np.abs(s))), nan, len(x) / SR))
    lp = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = S.render(S.make_csd(S.LOOPER, "looper", 62, lp, sets="start_alt=0", wav="dummy.wav"),
                       os.path.join(OUT, "in_noise.wav"), "looper")
    print("  CPU for 62 s: lattice %.1f s, factory looper %.1f s (%.2fx)" % (cpu, cpul, cpu / cpul))
    check("CPU within 1.2x the factory looper", cpu < 1.2 * cpul, "%.2fx" % (cpu / cpul))


def sc_m609():
    print("m609 (Csound 6.09.1)")
    csd = S.make_csd(INSTR, "m609", 3, BASE, sets=ALTS, wav="dummy.wav")
    out = os.path.join(OUT, "m609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "dummy.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "3", out], env=env,
                       capture_output=True, text=True, errors="replace")
    info = [ln for ln in r.stdout.splitlines() if ln.startswith("###")]
    print("  " + " / ".join(info))
    x = S.read_wav(out)
    ok = any("compileOrc returned 0" in ln for ln in info)
    check("6.09: compiles and runs (no NaN; no input here, so silence is right)", ok and not np.isnan(x).any(),
          "peak %.4f" % float(np.abs(x).max()))


def main():
    make_inputs()
    want = sys.argv[1:] or ["echo", "plexus", "decay", "color", "diffuse", "couple", "skew", "send", "hold", "clear",
                            "pulse", "sweep"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
