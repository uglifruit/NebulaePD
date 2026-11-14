#!/usr/bin/env python3
"""Live control test of the SC patches: the firmware's own OSC sender -> sclang -> the running synth.

  python tools/sc_osc_tests.py            # sc/01..04
  python tools/sc_osc_tests.py sc/x.scd   # one patch

tools/sc_nrt_tests.py checks the sound, but it drives the SynthDefs directly. This checks the path the module uses.
Each patch runs in SuperCollider 3.10.4 (real time, the PC's audio device) with the module's port setup
(scengine.STARTUP: openUDPPort(3000)). firmware/src/.../scsender.py then sends every control a distinct value, and
the test reads each value back from the synth. 01_sctest is checked by its own "SCTEST got" lines. Any sclang ERROR
fails the patch.
(Found the uf2_1 bug: `~neb.synth` called Event's built-in `synth` method, so every control was dropped.)
"""
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True              # no .pyc in firmware/src (it would be packaged)
sys.path.insert(0, os.path.join(ROOT, "firmware", "src", "QB_Nebulae_V2", "Code", "nebulae"))
import scsender  # noqa: E402

SC_DIR = r"C:\Program Files\SuperCollider-3.10.4"
SCLANG = os.path.join(SC_DIR, "sclang.exe")
LATCHES = ("freeze", "source", "record")
SCTEST_CONTROLS = ["pitch", "size", "density", "reset", "freeze", "blend"]

WRAPPER = """(
Server.local.options.numInputBusChannels = 2;
Server.local.options.numOutputBusChannels = 2;
s = Server.default;
("NEBTEST port " ++ thisProcess.openUDPPort(3000)).postln;
OSCdef(\\nebtest_query, {
    ~neb.controls.do { |name| ~nebSynth.get(name, { |v| ("NEBTEST value " ++ name ++ " " ++ v).postln }) };
    AppClock.sched(1.5, { "NEBTEST done".postln; s.quit; AppClock.sched(1, { 0.exit }); nil });
}, '/nebtest/query', recvPort: 3000);
OSCdef(\\nebtest_quit, { "NEBTEST done".postln; s.quit; AppClock.sched(1, { 0.exit }) }, '/nebtest/quit',
    recvPort: 3000);
"%(patch)s".load;
)
"""


def values_for(controls):
    out = {}
    for i, name in enumerate(controls):
        out[name] = 1.0 if name in LATCHES else round(0.11 + 0.07 * i, 2)
    return out


def run_patch(path):
    text = open(path, encoding="utf-8").read()
    m = re.search(r"~neb\.controls\s*=\s*\[([^\]]*)\]", text)
    controls = re.findall(r"\\(\w+)", m.group(1)) if m else SCTEST_CONTROLS
    is_sctest = m is None
    want = values_for(controls)
    fd, wrapper = tempfile.mkstemp(suffix=".scd")
    with os.fdopen(fd, "w") as f:
        f.write(WRAPPER % {"patch": os.path.abspath(path).replace("\\", "/")})
    env = dict(os.environ, PATH=SC_DIR + os.pathsep + os.environ.get("PATH", ""))
    proc = subprocess.Popen([SCLANG, wrapper], cwd=SC_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True, errors="replace")
    lines = []
    reader = threading.Thread(target=lambda: [lines.append(l.rstrip()) for l in proc.stdout], daemon=True)
    reader.start()

    def wait_for(pattern, timeout):
        end = time.time() + timeout
        while time.time() < end:
            if any(re.search(pattern, l) for l in lines):
                return True
            if proc.poll() is not None:
                return False
            time.sleep(0.1)
        return False

    problems = []
    sock = scsender.ScSend()
    try:
        if not wait_for(r"running", 60):
            problems.append("patch did not start")
        else:
            msgs = ["%s %s" % (n, v) for n, v in want.items() if n != "reset"]
            for i in range(6):                          # ~5 passes over 1.5 s, with one reset press in the middle
                sock.send(msgs + ["reset %d" % (1 if i == 2 else 0)])
                time.sleep(0.3)
            q = scsender.osc_message("/nebtest/" + ("quit" if is_sctest else "query"), 0)
            sock.sock.sendto(q, (sock.host, sock.sport))
            if not wait_for(r"NEBTEST done", 15):
                problems.append("no reply to the query")
    finally:
        sock.close()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        subprocess.run(["taskkill", "/F", "/IM", "scsynth.exe"], capture_output=True)
        reader.join(2)
        os.remove(wrapper)

    if not any(l == "NEBTEST port true" for l in lines):
        problems.append("port 3000 did not open")
    errors = [l for l in lines if "ERROR" in l]
    if errors:
        problems.append("%d sclang errors, first: %s" % (len(errors), errors[0]))
    if is_sctest:
        got = set(re.findall(r"SCTEST got /neb/(\w+)", "\n".join(lines)))
        missing = [n for n in SCTEST_CONTROLS if n not in got]
        if missing:
            problems.append("no SCTEST line for " + ", ".join(missing))
    else:
        seen = dict((n, float(v)) for n, v in re.findall(r"NEBTEST value (\w+) (\S+)", "\n".join(lines)))
        for n in controls:
            if n not in seen:
                problems.append("%s: no value read back" % n)
            elif abs(seen[n] - want[n]) > 1e-4:
                problems.append("%s: synth has %g, sent %g" % (n, seen[n], want[n]))
    return controls, problems


def main():
    if not os.path.isfile(SCLANG):
        sys.exit("SuperCollider 3.10.4 not found at " + SC_DIR)
    paths = sys.argv[1:] or [os.path.join(ROOT, "sc", f) for f in
                             ("01_sctest.scd", "02_sc_drift.scd", "03_sc_strike.scd", "04_sc_cloud.scd")]
    bad = 0
    for p in paths:
        controls, problems = run_patch(p)
        name = os.path.basename(p)
        if problems:
            bad += 1
            print("FAIL %s" % name)
            for x in problems:
                print("     " + x)
        else:
            print("OK   %s: %d controls reach the synth (%s)" % (name, len(controls), " ".join(controls)))
    print("ALL OK" if not bad else "%d FAILED" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
