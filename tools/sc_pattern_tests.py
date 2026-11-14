#!/usr/bin/env python3
"""Tests of sc/05_sc_pattern.scd in SuperCollider 3.10.4 (the module's version) on the PC.

  python tools/sc_pattern_tests.py [syntax logic nrt live]

  syntax  sclang compiles the file
  logic   the pattern functions in sclang (no server): length, Euclidean hit counts, notes in the scale, root on
          V/oct, Freeze = identical cycles, mutation changes them, File home recall, the hit chance, voice set B
  nrt     a 16 s render of the pattern (the same functions -> a Score): bounded, not silent, set A vs set B differ
  live    (and liveq: the pulses on the module's 5.3 ms poll grid) the patch running for real with its OSC port; Python sends Reset pulses (125 ms, +-2 ms jitter), stops,
          and restarts after a 3 s gap. From the patch's own log: every step is sent ahead of its time and sounds
          on its pulse, steps never double or skip, the clock carries on when stopped, a restart is step 1.
Renders and logs go to firmware/dist/sc_pattern/.
"""
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.dont_write_bytecode = True              # no .pyc in firmware/src (it would be packaged)
sys.path.insert(0, os.path.join(ROOT, "firmware", "src", "QB_Nebulae_V2", "Code", "nebulae"))
import sctest           # noqa: E402
import sc_nrt_tests as N  # noqa: E402
import scsender         # noqa: E402

PATCH = os.path.join(ROOT, "sc", "05_sc_pattern.scd").replace("\\", "/")
OUT = os.path.join(ROOT, "firmware", "dist", "sc_pattern").replace("\\", "/")
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


def sc_liveq():
    sc_live(quant=True)


def sc_syntax():
    print("[syntax]")
    check(sctest.check([PATCH]) == 0, "sclang compiles 05_sc_pattern.scd")


LOGIC = r"""
~nrtTest = true;
thisProcess.interpreter.executeFile("%(patch)s");
~say = { |ok, msg| ((if(ok, { "SCPTEST ok   " }, { "SCPTEST FAIL " })) ++ msg).postln };
~cycle = { var len = ~len.(); Array.fill(len, { ~scpTick.() }) };
~freqs = { |c| c.collect { |ev| ev.collect { |e| e[1][1].round(0.001) } } };
thisThread.randSeed = 7;
~newPattern.(); ~storeHome.(); ~k = 0; ~hitP = 1.0;
~ctl[\overlap] = 0; ~ctl[\freeze] = 1;
// length
~ctl[\size] = 0; ~say.(~len.() == 4, "Size 0 = 4 steps (" ++ ~len.() ++ ")");
~ctl[\size] = 1; ~say.(~len.() == 32, "Size 1 = 32 steps (" ++ ~len.() ++ ")");
~ctl[\size] = 0.43; ~say.(~len.() == 16, "Size 0.43 = 16 steps (" ++ ~len.() ++ ")");
// Euclidean hits per voice over one cycle
~k = 0;
~c = ~cycle.();
4.do { |v|
	var n = ~c.sum { |ev| ev.count { |e| e[0] == ~voiceDefs[v] } };
	~say.(n == ~hits.(v), "voice " ++ v ++ ": " ++ n ++ " hits = Euclid " ++ ~hits.(v));
};
// notes in the scale (major, then minor pentatonic), root on V/oct
[[0.0, [0, 2, 4, 5, 7, 9, 11]], [0.95, [0, 3, 5, 7, 10]]].do { |p|
	var bad = 0, root;
	~ctl[\start] = p[0]; ~k = 0;
	root = ~root.();
	~cycle.().do { |ev| ev.do { |e| if(e[0] != \scp_hat, {
		var m = (e[1][1].cpsmidi - root).round % 12;
		if(p[1].includes(m.asInteger).not, { bad = bad + 1 }) }) } };
	~say.(bad == 0, "Start " ++ p[0] ++ ": every note in the scale (" ++ bad ++ " outside)");
};
~ctl[\start] = 0; ~k = 0; ~a = ~freqs.(~cycle.());
~ctl[\pitch] = 0.7; ~k = 0; ~b = ~freqs.(~cycle.());
~say.(~a.flat.size > 0 and: { ~a.flat.every { |f, i| ((~b.flat[i] / f).ratiomidi - 6).abs < 0.01 } },
	"Pitch 0.7 = every note +6 semitones");
~ctl[\pitch] = 0.6;
// Freeze: identical cycles even with Overlap at full; unfrozen they change
~ctl[\overlap] = 1; ~ctl[\freeze] = 1; ~k = 0; ~hitP = 0.85;
~c1 = ~freqs.(~cycle.()); ~c2 = ~freqs.(~cycle.()); ~c3 = ~freqs.(~cycle.());
~say.((~c2 == ~c3) and: { ~c1 == ~c2 }, "Freeze: three cycles identical (Overlap 1)");
~ctl[\freeze] = 0;
~c4 = ~freqs.(~cycle.()); ~c5 = ~freqs.(~cycle.());
~say.((~c4 != ~c3) or: { ~c5 != ~c4 }, "unfrozen, Overlap 1: the cycles change");
// home
~ctl[\freeze] = 1; ~ctl[\overlap] = 0;
~recallHome.(); ~h0 = [~rot.copy, ~deg.collect(_.copy)];
~mutate.(0.3, 0.8);
~say.([~rot, ~deg] != ~h0, "Record burst changes the pattern");
~recallHome.();
~say.([~rot, ~deg] == ~h0, "File short press: back to home");
~mutate.(0.3, 0.8); ~storeHome.(); ~h1 = [~rot.copy, ~deg.collect(_.copy)]; ~mutate.(0.3, 0.8); ~recallHome.();
~say.([~rot, ~deg] == ~h1, "File held: the new home is recalled");
// the chance of a hit
~hitP = 0.85; ~ctl[\freeze] = 0; ~ctl[\overlap] = 0;
~tot = 0; ~exp = 0;
40.do { ~k = 0; ~rollDice.(); ~cycle.().do { |ev| ~tot = ~tot + ev.size }; ~exp = ~exp + 4.collect { |v| ~hits.(v) }.sum };
~say.(((~tot / ~exp) - 0.85).abs < 0.05, "hit chance: " ++ (~tot / ~exp).round(0.001) ++ " of the Euclidean hits (0.85)");
// set B
~ctl[\source] = 1; ~k = 0;
~say.(~cycle.().flatten.every { |e| e[1][9] == 1 }, "Source on: every voice gets set B");
~ctl[\source] = 0;
"SCPTEST done".postln;
0.exit;
"""


def sc_logic():
    print("[logic]")
    os.makedirs(OUT, exist_ok=True)
    path = OUT + "/logic.scd"
    open(path, "w").write(LOGIC.replace("%(patch)s", PATCH))
    code, out = sctest.sclang(path, 120)
    open(OUT + "/logic.log", "w").write(out)
    lines = [ln for ln in out.splitlines() if ln.startswith("SCPTEST")]
    for ln in lines:
        if ln.startswith("SCPTEST ok") or ln.startswith("SCPTEST FAIL"):
            check(ln.startswith("SCPTEST ok"), ln[13:])
    errs = [ln for ln in out.splitlines() if "ERROR" in ln]
    check("SCPTEST done" in out and not errs, f"logic script ran to the end ({errs[:2]})")


NRT = r"""
~nrtTest = true;
thisProcess.interpreter.executeFile("%(patch)s");
thisThread.randSeed = 3;
~newPattern.(); ~k = 0;
~ctl[\source] = %(set)d; ~ctl[\blend] = 0.3; ~ctl[\overlap] = 0.3;
~rows = ~neb.defs.collect { |d| [0.0, ['/d_recv', d.asBytes]] };
~rows = ~rows ++ [[0.0, [\g_new, 1000, 0, 0]], [0.0, [\s_new, \scp_master, 1001, 3, 1000, \in, 16, \blend, 0.3]]];
128.do { |i|
	var t = 0.3 + (i * 0.125);
	~scpTick.().do { |e| ~rows = ~rows.add([t, [\s_new, e[0], -1, 0, 1000, \out, 16] ++ e[1]]) };
};
~rows = ~rows.add([16.5, [\c_set, 0, 0]]);
~score = Score(~rows);
~opts = ServerOptions.new.numOutputBusChannels_(2).numInputBusChannels_(2).memSize_(65536);
~score.recordNRT(outputFilePath: "%(wav)s", sampleRate: 48000, headerFormat: "WAV", sampleFormat: "float",
	options: ~opts, duration: 16.5, action: { "SCNRT done".postln; 0.exit });
SystemClock.sched(120, { "SCNRT timeout".postln; 1.exit; nil });
"""


def render(set_):
    path = f"{OUT}/nrt{set_}.scd"
    wav = f"{OUT}/nrt{set_}.wav"
    if os.path.exists(wav):
        os.remove(wav)
    open(path, "w").write(NRT.replace("%(patch)s", PATCH).replace("%(set)d", str(set_)).replace("%(wav)s", wav))
    code, out = sctest.sclang(path, 150)
    open(f"{OUT}/nrt{set_}.log", "w").write(out)
    a, sr = N.read_wav(wav)
    return a, out


def sc_nrt():
    print("[nrt]")
    a, out = render(0)
    b, _ = render(1)
    seg = a[int(0.3 * 48000):]
    check(not np.isnan(a).any() and float(np.abs(a).max()) <= 0.96, f"bounded, no NaN (peak {np.abs(a).max():.3f})")
    r = float(np.sqrt(np.mean(seg ** 2)))
    check(r > 0.02, f"not silent (rms {r:.3f})")
    errs = [ln for ln in out.splitlines() if "ERROR" in ln or "FAILURE" in ln]
    check(not errs, f"no server errors ({errs[:2]})")

    def centroid(x):
        sp = np.abs(np.fft.rfft(x.mean(axis=1)))
        f = np.fft.rfftfreq(len(x), 1 / 48000)
        return float((sp * f).sum() / sp.sum())
    ca, cb = centroid(seg), centroid(b[int(0.3 * 48000):])
    check(abs(ca - cb) / ca > 0.1, f"voice set B sounds different (centroid {ca:.0f} vs {cb:.0f} Hz)")


WRAPPER = r"""(
Server.local.options.numInputBusChannels = 2;
Server.local.options.numOutputBusChannels = 2;
s = Server.default;
("NEBTEST port " ++ thisProcess.openUDPPort(3000)).postln;
~scpLog = true;
"%(patch)s".load;
)
"""


def live_once(quant):
    res, scatter = [], [99.0]

    def _chk(ok, msg):
        res.append((ok, msg))
    fd, wrapper = tempfile.mkstemp(suffix=".scd")
    with os.fdopen(fd, "w") as f:
        f.write(WRAPPER.replace("%(patch)s", PATCH))
    env = dict(os.environ, PATH=sctest.SC_DIR + os.pathsep + os.environ.get("PATH", ""))
    proc = subprocess.Popen([sctest.SCLANG, wrapper], cwd=sctest.SC_DIR, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, errors="replace")
    lines = []
    th = threading.Thread(target=lambda: [lines.append(ln.rstrip()) for ln in proc.stdout], daemon=True)
    th.start()
    end = time.time() + 60
    while time.time() < end and not any("05_sc_pattern running" in ln for ln in lines):
        time.sleep(0.1)
    sock = scsender.ScSend()
    rng = random.Random(4)

    def send(v):
        sock.sock.sendto(scsender.osc_message("/neb/reset", v), (sock.host, sock.sport))
    try:
        time.sleep(1.0)
        for phase in range(2):
            t0 = time.perf_counter()
            for i in range(48):                              # 6 s of 16ths at 120 BPM
                target = t0 + i * 0.125 + rng.uniform(-0.002, 0.002)
                if quant:                                    # the poll loop: values go out once per 5.3 ms pass
                    target = t0 + np.ceil((target - t0) / 0.0053) * 0.0053
                while time.perf_counter() < target:
                    time.sleep(0.0005)
                send(1)
                time.sleep(0.004)
                send(0)
            if phase == 0:
                time.sleep(3.0)                              # the clock stops: free-run, then a restart
        time.sleep(1.0)
    finally:
        sock.close()
        proc.kill()
        subprocess.run(["taskkill", "/F", "/IM", "scsynth.exe"], capture_output=True)
        th.join(2)
        os.remove(wrapper)
    open(OUT + ("/live_q.log" if quant else "/live.log"), "w").write("\n".join(lines))
    pulses = [float(m.group(1)) for ln in lines for m in [re.match(r"SCPLOG pulse (\S+)", ln)] if m]
    fires = [(int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)))
             for ln in lines for m in [re.match(r"SCPLOG fire (\S+) (\S+) (\S+) (\S+)", ln)] if m]
    _chk(len(pulses) == 96, f"96 pulses received ({len(pulses)})")
    if len(pulses) < 96 or not fires:
        return res, 99.0
    errs = [ln for ln in lines if "ERROR" in ln]
    _chk(not errs, f"no sclang errors ({errs[:2]})")
    cancel = [float(m.group(1)) for ln in lines for m in [re.match(r"SCPLOG cancel (\S+)", ln)] if m]
    fires = [f for f in fires if not any(abs(f[1] - c) < 1e-3 for c in cancel)]      # freed before they sounded
    # locked: pulses 8..47 and 56..95. The sender's own timing wobbles (Windows), so the steps are compared with a
    # straight line fitted through the received pulses (the clock the module would see), and the pulses' own
    # scatter around it is reported too
    dev, ahead, pj = [], [], []
    for lo, hi in ((8, 48), (56, 96)):
        idx = np.arange(lo, hi)
        y = np.array(pulses[lo:hi])
        a1, b1 = np.polyfit(idx, y, 1)
        keep = np.abs(y - (b1 + a1 * idx)) < 0.010                 # robust: refit without the sender's stalls
        a1, b1 = np.polyfit(idx[keep], y[keep], 1)
        for i in idx:
            ideal = b1 + a1 * i
            pj.append((pulses[i] - ideal) * 1000)
            k, g, t, sent = min(fires, key=lambda f: abs(f[2] - ideal))
            dev.append((t - ideal) * 1000)
            ahead.append((t - sent) * 1000)
    dev, ahead, pj = np.array(dev), np.array(ahead), np.array(pj)
    scatter[0] = float(np.abs(pj).max())
    print("  info pulses vs their straight line: p95 %.1f, max %.1f ms; steps: p95 %.1f, max %.1f ms"
          % (np.percentile(np.abs(pj), 95), np.abs(pj).max(), np.percentile(np.abs(dev), 95), np.abs(dev).max()))
    _chk(np.abs(np.median(dev)) < 3 and np.percentile(np.abs(dev), 95) < 6 and np.abs(dev).max() < 12,
          f"locked steps sound on the clock: median {np.median(dev):+.1f} ms, p95 {np.percentile(np.abs(dev), 95):.1f}, "
          f"worst {np.abs(dev).max():.1f} ms")
    late = [ln for ln in lines if ln.startswith("SCPLOG late")]
    print("  info late sends (sclang stalls): %d %s" % (len(late), late[:3]))
    _chk(ahead.min() > 25, f"each step is sent ahead of its sound time (min {ahead.min():.1f} ms; output latency 32)")
    seq = [f for f in fires if pulses[0] - 0.05 < f[2] <= pulses[47] + 0.05]    # a stand-in may sound up to 50 ms early
    ks = [f[0] for f in seq]
    # the step at the first pulse is step 1 (k 0), or a free-running step that stood in for it (then k 1 next)
    ok_seq = ks[1:] == list(range(1, len(ks))) and len(ks) == 48
    _chk(ok_seq,
          f"one step per pulse, none doubled or skipped ({len(ks)} steps for 48 pulses)")
    gap = [f for f in fires if pulses[47] + 0.2 < f[2] < pulses[48] - 0.1]
    gi = np.diff([f[2] for f in gap])
    _chk(len(gap) > 10 and np.allclose(gi, 0.125, atol=0.006), f"the clock stops: it carries on ({len(gap)} "
                                                               f"steps, {gi.mean() if len(gi) else 0:.4f} s apart)")
    for p0 in (pulses[0], pulses[48]):
        near = sorted(f[2] for f in fires if p0 - 0.06 < f[2] < p0 + 0.06
                      and not any(abs(f[1] - c) < 1e-3 for c in cancel))
        _chk(len(near) <= 1 or min(np.diff(near)) > 0.06,
              f"clock start at {p0:.2f}: no flam (steps sounding {[round(x - p0, 4) for x in near]}, cancelled {len(cancel)})")
    after = sorted((f for f in fires if f[2] > pulses[48] - 0.05), key=lambda f: f[2])
    _chk(after[0][0] == 0 or after[1][0] == 1,
          f"restart after 3 s: the first pulse is step 1 (k = {after[0][0]}, then {after[1][0]})")
    return res, scatter[0]


def sc_live(quant=False):
    """The PC runs the sender, sclang and scsynth side by side, and Windows sometimes holds the sender back by tens
    of ms - far beyond the module's poll-pass jitter (about 5 ms). A run is judged only when its pulses stay within
    12 ms of their straight line; up to 3 attempts."""
    print("[live%s]" % (" (pulses on the module's 5.3 ms poll grid)" if quant else ""))
    for attempt in range(3):
        res, scatter = live_once(quant)
        if scatter <= 12.0:
            for ok, msg in res:
                check(ok, msg)
            return
        print("  info attempt %d: the sender was held back (pulses up to %.0f ms off), not judged" % (attempt + 1,
                                                                                                  scatter))
    print("  SKIP the PC never sent a module-like clock in 3 attempts (no verdict on the patch)")

if __name__ == "__main__":
    want = sys.argv[1:] or ["syntax", "logic", "nrt", "live", "liveq"]
    for w in want:
        globals()["sc_" + w]()
    print(f"\n{len(FAILS)} failure(s)" + ("".join("\n  " + f for f in FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
