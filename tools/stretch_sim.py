#!/usr/bin/env python3
"""Offline tests of instr/stretch.instr through real Csound (WSL: needs csound + numpy).

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/stretch_sim.py [scenario ...]

Builds the CSD the module builds (tools/instr2csd.py), adds one stick file the way conductor.py loads files
(tables 400 + n and the file arrays), drives the controls from a score-time automation instrument, renders, and
checks the output numerically:
  rate      1x plays the ten tones of the file a second each; 0.1x plays them ten times slower
  pitch     frozen on tone 3, Pitch +12 -> twice its frequency; Freeze holds the moment
  reverse   -1x from the middle to the end walks the tones downwards
  live      Source on: the first grab (after 5 s) holds what was played; a Record press grabs later playing
  texture   Overlap (blur) keeps the previous tone sounding; Window (smear) spreads a pure tone
  full      everything on (4 layers, smear, blur, reverb, scrubbing): level, NaN, clicks, and CPU against the
            factory granular looper on the same input
  rate609   a 44.1 kHz file through Csound 6.09.1 (tools/run_csound609.js; run from Windows Python, needs node):
            the module's Csound 6.11 mincer reads tables at sr, so the instrument scales time and pitch by
            file sr / sr. Csound 6.18 (WSL) does that inside mincer, so the WSL scenarios use a 48 kHz file, where
            both agree.
Renders go to firmware/dist/stretch_sim/.
"""
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "firmware", "dist", "stretch_sim")
INSTR = os.path.join(ROOT, "instr", "stretch.instr")
LOOPER = os.path.join(ROOT, "firmware", "src", "QB_Nebulae_V2", "Code", "instr", "a_granularlooper.instr")
SR = 48000
FILE_SR = 48000                                    # the WSL (6.18) scenarios; rate609 uses 44100
TONES = [300 + 60 * k for k in range(10)]          # tone k plays from k to k + 1 s in the file
ALTS = "start_alt=0.5 size_alt=0.0 density_alt=0.3 window_alt=0.5 overlap_alt=0.5 blend_alt=0.0 pitch_alt=0.5"


def speed_for(rate):
    """The Speed value that gives this rate (inverse of the instrument's map; negative = backwards)."""
    r = abs(rate)
    kad = 0.04 + 0.96 * (1 + np.log10(r) / 3) if r < 1 else 1 + (r - 1)
    return 0.5 + (kad if rate > 0 else -kad) * 0.125


def write_wav(path, x, sr, ch=2):
    data = (np.clip(np.stack([x] * ch, axis=1), -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def read_wav(path):
    """16-bit or 32-bit float WAV (Python's wave module can't read float) -> (frames, channels)."""
    import struct
    b = open(path, "rb").read()
    i, fmt, ch, bits, data = 12, None, 2, 16, b""
    while i + 8 <= len(b):
        cid, size = b[i:i + 4], struct.unpack("<I", b[i + 4:i + 8])[0]
        if cid == b"fmt ":
            fmt, ch = struct.unpack("<HH", b[i + 8:i + 12])
            bits = struct.unpack("<H", b[i + 22:i + 24])[0]
        elif cid == b"data":
            data = b[i + 8:i + 8 + size]
        i += 8 + size + (size & 1)
    if fmt == 3 or bits == 32:
        x = np.frombuffer(data[:len(data) // 4 * 4], "<f4").astype(float)
    else:
        x = np.frombuffer(data[:len(data) // 2 * 2], "<i2").astype(float) / 32768
    return x[:len(x) // ch * ch].reshape(-1, ch)


def tones_wav(name, fsr):
    t = np.arange(10 * fsr) / fsr
    tones = np.zeros_like(t)
    for k, f in enumerate(TONES):
        m = (t >= k) & (t < k + 1)
        tones[m] = 0.4 * np.sin(2 * np.pi * f * t[m])
    write_wav(os.path.join(OUT, name), tones, fsr)
    return tones


def make_inputs():
    tones = tones_wav("tones.wav", FILE_SR)
    tones_wav("tones44.wav", 44100)
    # live input: 660 Hz from 1 to 7 s (instr 1 starts at 1 s), silence, 880 Hz from 12 to 15 s, silence to 30 s
    t = np.arange(30 * SR) / SR
    live = np.zeros_like(t)
    for a, b, f in ((1, 7, 660), (12, 15, 880)):
        m = (t >= a) & (t < b)
        live[m] = 0.4 * np.sin(2 * np.pi * f * t[m])
    write_wav(os.path.join(OUT, "live.wav"), live, SR)
    # a busy input for the CPU run: the tones again plus noise bursts
    rng = np.random.default_rng(3)
    busy = np.tile(np.interp(np.arange(10 * SR) / SR, np.arange(10 * FILE_SR) / FILE_SR, tones), 7)[:70 * SR]
    busy += 0.05 * rng.standard_normal(len(busy))
    write_wav(os.path.join(OUT, "busy.wav"), busy, SR)


def make_csd(instr, name, secs, automation, sets=ALTS, wav="tones.wav"):
    csd = os.path.join(OUT, name + ".csd")
    subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "instr2csd.py"), instr, csd, "--secs",
                           str(secs), "--set"] + sets.split(), stdout=subprocess.DEVNULL)
    s = open(csd).read()
    files = ('gSname[0] = "W"\ngilen[0] filelen "W"\ngichn[0] filenchnls "W"\n'
             'gisr[0] filesr "W"\ngipeak[0] filepeak "W"\nginumfiles init 1\n').replace("W", wav)
    s = s.replace("ginumfiles init 0\n", files)
    s = s.replace("</CsScore>", 'f 400 0 0 1 "%s" 0 0 1\ni 50 0 %d\n</CsScore>' % (wav, secs))
    s = s.replace("</CsInstruments>", "instr 50\nkt timeinsts\n" + automation + "\nendin\n</CsInstruments>")
    open(csd, "w").write(s)
    return csd


def render(csd, wav_in, name):
    import resource                                  # Linux only (WSL): CPU time of the csound child
    out = os.path.join(OUT, name + ".wav")
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    r = subprocess.run(["csound", "-d", "-W", "-f", "-i", wav_in, "-o", out, csd], capture_output=True, text=True,
                       cwd=OUT)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    errs = [l for l in (r.stdout + r.stderr).splitlines()
            if ("error" in l.lower() and "0 errors" not in l) or "INIT ERROR" in l or "PERF ERROR" in l]
    if r.returncode != 0 or errs:
        print("\n".join((r.stdout + r.stderr).splitlines()[-30:]))
        raise SystemExit("%s: csound exit %d %s" % (name, r.returncode, errs[:5]))
    return read_wav(out), cpu


def peak_freq(x, t0, t1, lo=150, hi=2500):
    seg = x[int(t0 * SR):int(t1 * SR), 0]
    seg = seg * np.hanning(len(seg))
    sp = np.abs(np.fft.rfft(seg, 1 << 17))
    f = np.fft.rfftfreq(1 << 17, 1 / SR)
    m = (f > lo) & (f < hi)
    return f[m][np.argmax(sp[m])], float(np.sqrt(np.mean(seg ** 2)) * 1.63)


RESULTS = []


def check(name, ok, detail):
    RESULTS.append(ok)
    print("  %s %s: %s" % ("PASS" if ok else "FAIL", name, detail))


def near(f, target, tol=0.03):
    return abs(f - target) <= tol * target


def sc_rate():
    print("rate")
    auto = "gkspeed = %f\ngkloopstart = 0\ngkloopsize = 1\ngkblend = 1\ngkpitch = 0.6\ngkdensity = 0\n" % speed_for(1)
    x, _ = render(make_csd(INSTR, "rate1", 12, auto), os.path.join(OUT, "live.wav"), "rate1")
    got = [peak_freq(x, 1 + k + 0.35, 1 + k + 0.75)[0] for k in range(9)]
    check("1x plays each tone for a second", all(near(g, f) for g, f in zip(got, TONES)),
          " ".join("%.0f" % g for g in got))
    auto = auto.replace("gkspeed = %f" % speed_for(1), "gkspeed = %f" % speed_for(0.1))
    x, _ = render(make_csd(INSTR, "rate01", 32, auto), os.path.join(OUT, "live.wav"), "rate01")
    got = [peak_freq(x, 1 + c - 1.5, 1 + c + 1.5)[0] for c in (5, 15, 25)]
    check("0.1x: tone 0 at 5 s, tone 1 at 15 s, tone 2 at 25 s", all(near(g, f) for g, f in zip(got, TONES)),
          " ".join("%.0f" % g for g in got))


def sc_pitch():
    print("pitch and freeze")
    auto = ("gkspeed = 0.5\ngkloopstart = 0.35\ngkloopsize = 1\ngkblend = 1\ngkdensity = 0\n"
            "gkpitch = (kt < 4 ? 0.6 : 0.8)\ngkfreeze = 0\n")
    x, _ = render(make_csd(INSTR, "pitch", 8, auto), os.path.join(OUT, "live.wav"), "pitch")
    f0, a0 = peak_freq(x, 2.0, 3.8)
    f1, a1 = peak_freq(x, 5.0, 7.8)
    check("frozen on tone 3", near(f0, TONES[3]), "%.1f Hz (expect %d), level %.2f" % (f0, TONES[3], a0))
    check("Pitch +12 doubles it", near(f1, 2 * TONES[3]), "%.1f Hz (expect %d)" % (f1, 2 * TONES[3]))
    auto = ("gkspeed = %f\ngkloopstart = 0\ngkloopsize = 1\ngkblend = 1\ngkdensity = 0\ngkpitch = 0.6\n"
            "gkfreeze = (kt > 3.5 ? 1 : 0)\n" % speed_for(1))
    x, _ = render(make_csd(INSTR, "freeze", 9, auto), os.path.join(OUT, "live.wav"), "freeze")
    got = [peak_freq(x, a, a + 0.6)[0] for a in (5.0, 6.5, 8.0)]
    check("Freeze holds the moment (tone 2, from 3.5 s)", all(near(g, TONES[2]) for g in got),
          " ".join("%.0f" % g for g in got))


def sc_reverse():
    print("reverse")
    auto = ("gkspeed = %f\ngkloopstart = 0.5\ngkloopsize = 1\ngkblend = 1\ngkdensity = 0\ngkpitch = 0.6\n"
            % speed_for(-1))
    x, _ = render(make_csd(INSTR, "reverse", 8, auto), os.path.join(OUT, "live.wav"), "reverse")
    got = [peak_freq(x, 1 + k + 0.35, 1 + k + 0.75)[0] for k in range(1, 6)]   # k = 1..5 s after the start
    # from 5 s backwards: it wraps to the end of the region (10 s) at once, so 1.35-1.75 s later it is in tone 8;
    # then 7, 6, 5, and below 5 s it wraps to the end again (tone 9)
    expect = [TONES[8], TONES[7], TONES[6], TONES[5], TONES[9]]
    check("-1x walks the tones downwards", all(near(g, f) for g, f in zip(got, expect)),
          " ".join("%.0f" % g for g in got) + " (expect " + " ".join(str(e) for e in expect) + ")")


def sc_live():
    print("live grab")
    auto = ("gksource = 1\ngkspeed = 0.5\ngkloopstart = (kt < 16.5 ? 0.5 : 0.3)\ngkloopsize = 1\ngkblend = 1\n"
            "gkdensity = 0\ngkpitch = 0.6\ngkrecord = (kt > 16 && kt < 16.02 ? 1 : 0)\n")
    x, _ = render(make_csd(INSTR, "livegrab", 22, auto), os.path.join(OUT, "live.wav"), "livegrab")
    f0, a0 = peak_freq(x, 8.5, 11.5)
    check("first grab holds the 660 Hz played before it (input silent now)", near(f0, 660) and a0 > 0.05,
          "%.1f Hz, level %.2f" % (f0, a0))
    f1, a1 = peak_freq(x, 18, 21.5)
    check("Record grabs the later 880 Hz", near(f1, 880) and a1 > 0.05, "%.1f Hz, level %.2f" % (f1, a1))


def band_energy(x, t0, t1, f, width=15):
    seg = x[int(t0 * SR):int(t1 * SR), 0] * np.hanning(int(t1 * SR) - int(t0 * SR))
    sp = np.abs(np.fft.rfft(seg, 1 << 16)) ** 2
    fr = np.fft.rfftfreq(1 << 16, 1 / SR)
    return float(sp[(fr > f - width) & (fr < f + width)].sum() / (sp.sum() + 1e-12))


def sc_texture():
    print("texture (blur, smear)")
    auto = ("gkspeed = %f\ngkloopstart = 0\ngkloopsize = 1\ngkblend = 1\ngkdensity = 0\ngkpitch = 0.6\n"
            "gkoverlap = OV\ngkwindow = 0\n" % speed_for(1))
    x0, _ = render(make_csd(INSTR, "blur0", 6, auto.replace("OV", "0")), os.path.join(OUT, "live.wav"), "blur0")
    x1, _ = render(make_csd(INSTR, "blur1", 6, auto.replace("OV", "1")), os.path.join(OUT, "live.wav"), "blur1")
    # 0.25-0.6 s after tone 3 starts (file 3 s = render 4 s): how much of tone 2 is still sounding
    e0, e1 = band_energy(x0, 4.25, 4.6, TONES[2]), band_energy(x1, 4.25, 4.6, TONES[2])
    check("blur keeps the previous tone sounding", e1 > 0.1 and e1 > 5 * e0, "tone 2 share %.3f -> %.3f" % (e0, e1))
    auto = ("gkspeed = 0.5\ngkloopstart = 0.35\ngkloopsize = 1\ngkblend = 1\ngkdensity = 0\ngkpitch = 0.6\n"
            "gkoverlap = 0\ngkwindow = WI\n")
    y0, _ = render(make_csd(INSTR, "smear0", 6, auto.replace("WI", "0")), os.path.join(OUT, "live.wav"), "smear0")
    y1, _ = render(make_csd(INSTR, "smear1", 6, auto.replace("WI", "1")), os.path.join(OUT, "live.wav"), "smear1")
    c0, c1 = band_energy(y0, 3, 5.5, TONES[3]), band_energy(y1, 3, 5.5, TONES[3])
    check("smear spreads a pure tone (energy near its peak)", c1 < c0 - 0.05, "%.3f -> %.3f" % (c0, c1))


def clicks(x, t0, t1):
    seg = x[int(t0 * SR):int(t1 * SR), 0]
    d2 = np.abs(np.diff(seg, 2))
    win = 2400
    rms = np.sqrt(np.convolve(seg ** 2, np.ones(win) / win, "same"))[1:-1] + 1e-4
    return int(np.sum(d2 > 0.25 + 1.5 * rms))


def sc_full():
    print("full (CPU, level, clicks)")
    auto = ("gkspeed = %f\ngkloopstart = 0.2 + 0.1 * sin(kt * 0.3)\ngkloopsize = 0.6\ngkblend = 0.85\n"
            "gkdensity = 1\ngkwindow = 0.6\ngkoverlap = 0.6\ngkpitch = 0.6 + (kt > 30 ? 0.1 : 0)\n"
            "gkblend_alt = 0.5\ngkreset = (frac(kt / 4) < 0.01 ? 1 : 0)\n" % speed_for(0.05))
    x, cpu = render(make_csd(INSTR, "full", 70, auto), os.path.join(OUT, "busy.wav"), "full")
    seg = x[2 * SR:]
    pk, nan = float(np.max(np.abs(seg))), int(np.isnan(seg).sum())
    rms = float(np.sqrt(np.mean(seg ** 2)))
    check("level", 0.02 < rms and pk <= 1.0 and nan == 0, "rms %.3f, peak %.3f, NaN %d" % (rms, pk, nan))
    n = clicks(x, 2, 70)
    check("no clicks (scrubbing, Reset every 4 s, layers, blur)", n == 0, "%d" % n)
    auto0 = auto.replace("gkdensity = 1", "gkdensity = 0").replace("gkoverlap = 0.6", "gkoverlap = 0")
    _, cpu0 = render(make_csd(INSTR, "lean", 70, auto0), os.path.join(OUT, "busy.wav"), "lean")
    lp_auto = "gkspeed = 0.625\ngkdensity = 0.5\ngkloopsize = 0.6\ngkblend = 0.85\n"
    _, cpul = render(make_csd(LOOPER, "looper", 70, lp_auto, sets="start_alt=0"), os.path.join(OUT, "busy.wav"),
                     "looper")
    print("  CPU for 70 s: stretch full %.1f s, 1 layer no blur %.1f s, factory looper %.1f s (ratio %.2f / %.2f)"
          % (cpu, cpu0, cpul, cpu / cpul, cpu0 / cpul))
    # measured 1.2-1.5x on WSL (it varies run to run); the factory looper is known to run on the module
    check("full CPU within 1.8x the factory looper", cpu < 1.8 * cpul, "%.2fx" % (cpu / cpul))


def sc_rate609():
    print("rate609 (44.1 kHz file, Csound 6.09.1 = the module's mincer behaviour)")
    auto = "gkspeed = %f\ngkloopstart = 0\ngkloopsize = 1\ngkblend = 1\ngkdensity = 0\n" % speed_for(1)
    auto += "gkpitch = (kt < 7 ? 0.6 : 0.8)\n"
    csd = make_csd(INSTR, "rate609", 10, auto, wav="tones44.wav")
    s = open(csd).read().replace("giCapMax = 120 ", "giCapMax = 10 ")      # the wasm heap is small
    open(csd, "w").write(s)
    out = os.path.join(OUT, "rate609.wav")
    env = dict(os.environ, CS609_MEM="512", CS609_FILES=os.path.join(OUT, "tones44.wav"))
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "run_csound609.js"), csd, "10", out], env=env,
                       capture_output=True, text=True, errors="replace")
    print("  " + " / ".join(l for l in r.stdout.splitlines() if l.startswith("###")))
    x = read_wav(out)
    got = [peak_freq(x, 1 + k + 0.35, 1 + k + 0.75)[0] for k in range(5)]
    check("6.09: 1x plays each tone for a second, in tune", all(near(g, f) for g, f in zip(got, TONES)),
          " ".join("%.0f" % g for g in got))
    f, _ = peak_freq(x, 7.4, 7.8)
    check("6.09: Pitch +12 on tone 6", near(f, 2 * TONES[6]), "%.1f Hz (expect %d)" % (f, 2 * TONES[6]))


def main():
    os.makedirs(OUT, exist_ok=True)
    make_inputs()
    want = sys.argv[1:] or ["rate", "pitch", "reverse", "live", "texture", "full"]
    for w in want:
        globals()["sc_" + w]()
    print("\n%d/%d passed" % (sum(RESULTS), len(RESULTS)))
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
