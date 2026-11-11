#!/usr/bin/env python3
"""The storyteller on the PC: a scripted performance through the real instrument and the real narrator.

  wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/story_sim.py      (needs csound, numpy)

1. Synthesises a 150 s input (pad, a 120 bpm pulse, a brightening noise, silence, a crack, the pad with more
   bass, irregular taps).
2. Wraps instr/bt_storyteller.instr like the module (tools/instr2csd.py) plus an automation instrument that
   moves the controls (a density move, indecision on size, an octave jump, reverse speed, freeze, an LFO on
   overlap, a 100 bpm Reset gate, three knobs at once).
3. Renders it with Csound (the input from the file), keeps the events file the instrument wrote, replays it
   through bt/narrator.py and prints the story. Also times the render against the plain looper (CPU check).
Output: firmware/dist/story_sim/ (input.wav, events.txt, story.txt, out.wav).
"""
import os
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "firmware", "dist", "story_sim")
SR = 48000
SECS = 150
EVENTS = "/dev/shm/neb_bt/events"

AUTOMATION = r"""
instr 50
kt timeinsts
; 10 s: density 0.30 -> 0.80 in 1 s (a hand)
gkdensity = (kt < 10 ? 0.3 : (kt < 11 ? 0.3 + (kt - 10) * 0.5 : 0.8))
; 24-28 s: size back and forth (indecision)
gksize_v = 0.4
if kt > 24 && kt < 28 then
    gksize_v = 0.4 + 0.15 * sin((kt - 24) * 3.14159 * 1.5)
endif
gkloopsize = gksize_v
; 35 s: pitch up an octave (0.6 -> 0.8, a step)
gkpitch = (kt < 35 ? 0.6 : 0.8)
; 45 s: speed from x1 to x-1 (backwards) in 0.5 s
gkspeed = (kt < 45 ? 0.625 : (kt < 45.5 ? 0.625 - (kt - 45) * 0.5 : 0.375))
; 50-58 s: freeze
gkfreeze = (kt > 50 && kt < 58 ? 1 : 0)
; 100-130 s: an LFO on overlap, period 4 s
gkoverlap = (kt > 100 && kt < 130 ? 0.5 + 0.3 * sin((kt - 100) * 2 * 3.14159 / 4) : 0.5)
; 118-133 s: a 100 bpm gate into Reset
kgate = 0
if kt > 118 && kt < 133 then
    kgate = (frac((kt - 118) * 100 / 60) < 0.05 ? 1 : 0)
endif
gkreset = kgate
; 140 s: three knobs at once
if kt > 140 && kt < 140.6 then
    gkwindow = 0.2 + (kt - 140)
    gkblend = 0.5 + (kt - 140) * 0.5
    gkloopstart = 0.1 + (kt - 140)
endif
endin
"""


def synth_input(path):
    t = np.arange(SECS * SR) / SR
    x = np.zeros_like(t)
    rng = np.random.default_rng(7)
    pad = 0.03 * (np.sin(2 * np.pi * 110 * t) + 0.6 * np.sin(2 * np.pi * 220 * t) + 0.3 * np.sin(2 * np.pi * 330 * t))
    m = (t < 20)
    x[m] += pad[m]
    # 20-40 s: 120 bpm kicks + the pad
    for b in np.arange(20, 40, 0.5):
        i = int(b * SR)
        n = int(0.15 * SR)
        e = np.exp(-np.arange(n) / (0.03 * SR))
        x[i:i + n] += 0.5 * e * np.sin(2 * np.pi * 60 * np.arange(n) / SR)
    m = (t >= 20) & (t < 40)
    x[m] += pad[m]
    # 40-60 s: noise that gets brighter (a one-pole low-pass opening up)
    seg = (t >= 40) & (t < 60)
    noise = rng.standard_normal(seg.sum()) * 0.05
    y = np.zeros_like(noise)
    acc = 0.0
    k = np.linspace(0.01, 0.9, len(noise))
    for i in range(len(noise)):
        acc += k[i] * (noise[i] - acc)
        y[i] = acc
    x[seg] += y * 3
    # 60-90 s silence; 90 s a crack
    i = int(90 * SR)
    x[i:i + 400] += 0.7 * rng.standard_normal(400) * np.exp(-np.arange(400) / 80)
    # 95-115 s: the pad again, with more bass
    m = (t >= 95) & (t < 115)
    x[m] += pad[m] + 0.06 * np.sin(2 * np.pi * 55 * t[m])
    # 115-140 s: irregular taps
    for b in 115 + np.cumsum(rng.uniform(0.15, 1.2, 40)):
        if b > 140:
            break
        i = int(b * SR)
        x[i:i + 300] += 0.4 * rng.standard_normal(300) * np.exp(-np.arange(300) / 60)
    # 140-150: the pad
    m = t >= 140
    x[m] += pad[m]
    stereo = np.stack([x, x], axis=1)
    data = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def make_csd(instr, csd, automation):
    subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "instr2csd.py"), instr, csd, "--secs",
                           str(SECS)], stdout=subprocess.DEVNULL)
    s = open(csd).read()
    # one audio file, as the firmware's conductor.py loads the stick's files (table 400 + the file arrays)
    files = ('gSname[0] = "input.wav"\ngilen[0] filelen "input.wav"\ngichn[0] filenchnls "input.wav"\n'
             'gisr[0] filesr "input.wav"\ngipeak[0] filepeak "input.wav"\nginumfiles init 1\n')
    assert "ginumfiles init 0" in s
    s = s.replace("ginumfiles init 0\n", files)
    s = s.replace("</CsScore>", 'f 400 0 0 1 "input.wav" 0 0 1\n</CsScore>')
    if automation:
        s = s.replace("</CsInstruments>", "gksize_v init 0.4\n" + AUTOMATION + "</CsInstruments>")
        s = s.replace("</CsScore>", "i 50 0 %d\n</CsScore>" % SECS)
    open(csd, "w").write(s)


def render(csd, wav_in, wav_out):
    # CPU time of the Csound process (user + system), not wall time: the launcher's systemctl/mount calls wait
    # on the PC (no stick, no systemd rights) and would count otherwise
    import resource
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    r = subprocess.run(["csound", "-d", "-i", wav_in, "-o", wav_out, csd], capture_output=True, text=True,
                       cwd=OUT)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    el = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    errs = [l for l in (r.stdout + r.stderr).splitlines() if "error" in l.lower() and "0 errors" not in l]
    return el, r.returncode, errs


def main():
    os.makedirs(OUT, exist_ok=True)
    wav_in = os.path.join(OUT, "input.wav")
    synth_input(wav_in)
    st_csd = os.path.join(OUT, "storyteller.csd")
    make_csd(os.path.join(ROOT, "instr", "bt_storyteller.instr"), st_csd, True)
    el_story, code, errs = render(st_csd, wav_in, os.path.join(OUT, "out.wav"))
    print("storyteller render: %.1f s CPU for %d s of audio, exit %d" % (el_story, SECS, code))
    for e in errs[:10]:
        print("  " + e)
    if not os.path.exists(EVENTS):
        sys.exit("no events file written")
    shutil.copy(EVENTS, os.path.join(OUT, "events.txt"))
    lines = open(EVENTS).read().splitlines()
    kinds = {}
    for l in lines:
        kinds[l[:1]] = kinds.get(l[:1], 0) + 1
    print("events: %d lines (%s)" % (len(lines), ", ".join("%s %d" % kv for kv in sorted(kinds.items()))))
    lp_csd = os.path.join(OUT, "looper.csd")
    make_csd(os.path.join(ROOT, "firmware", "src", "QB_Nebulae_V2", "Code", "instr", "a_granularlooper.instr"),
             lp_csd, True)
    el_loop, _, _ = render(lp_csd, wav_in, os.path.join(OUT, "looper_out.wav"))
    print("plain looper render: %.1f s CPU -> the storyteller's ears cost %+.0f%% CPU" % (
        el_loop, 100.0 * (el_story - el_loop) / el_loop))
    sys.path.insert(0, os.path.join(ROOT, "bt"))
    import narrator
    told = narrator.replay(os.path.join(OUT, "events.txt"))
    story = "".join(text for t, text in told)
    open(os.path.join(OUT, "story.txt"), "w").write(story)
    print("\n================ the story (%d observations) ================\n" % len(told))
    print(story)


if __name__ == "__main__":
    main()
