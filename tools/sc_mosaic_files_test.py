#!/usr/bin/env python3
"""Live check of 07_sc_mosaic's file handling (SC 3.10.4 on the PC): the patch scans a folder (here
firmware/dist/stick_audio, the unit's own WAVs read from the SD image), loads the first, and File presses (OSC
/neb/filestate) load the next ones.

  python tools/sc_mosaic_files_test.py
"""
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "firmware", "src", "QB_Nebulae_V2", "Code", "nebulae"))
import sctest      # noqa: E402
import scsender    # noqa: E402

DIR = os.path.join(ROOT, "firmware", "dist", "stick_audio").replace("\\", "/")
PATCH = os.path.join(ROOT, "sc", "07_sc_mosaic.scd").replace("\\", "/")
WRAP = """(
Server.local.options.numInputBusChannels = 2;
Server.local.options.numOutputBusChannels = 2;
s = Server.default;
("NEBTEST port " ++ thisProcess.openUDPPort(3000)).postln;
~mosaicDir = "%s";
"%s".load;
)
""" % (DIR, PATCH)


def main():
    if not os.path.isdir(DIR):
        sys.exit("no %s (the stick WAVs from the SD image)" % DIR)
    n = len([f for f in os.listdir(DIR) if f.lower().endswith((".wav", ".aif", ".aiff", ".flac"))])
    fd, w = tempfile.mkstemp(suffix=".scd")
    with os.fdopen(fd, "w") as f:
        f.write(WRAP)
    env = dict(os.environ, PATH=sctest.SC_DIR + os.pathsep + os.environ.get("PATH", ""))
    p = subprocess.Popen([sctest.SCLANG, w], cwd=sctest.SC_DIR, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, errors="replace")
    lines = []
    th = threading.Thread(target=lambda: [lines.append(l.rstrip()) for l in p.stdout], daemon=True)
    th.start()
    end = time.time() + 60
    while time.time() < end and not any("07_sc_mosaic running" in l for l in lines):
        time.sleep(0.1)
    sock = scsender.ScSend()
    try:
        for _ in range(2):
            time.sleep(1.5)
            for v in (1, 0):
                sock.sock.sendto(scsender.osc_message("/neb/filestate", v), (sock.host, sock.sport))
                time.sleep(0.1)
        time.sleep(2)
    finally:
        sock.close()
        p.kill()
        subprocess.run(["taskkill", "/F", "/IM", "scsynth.exe"], capture_output=True)
        th.join(2)
        os.remove(w)
    run = [l for l in lines if "07_sc_mosaic running" in l]
    loads = [l for l in lines if l.startswith("sc_mosaic corpus")]
    errs = [l for l in lines if "ERROR" in l or "FAILURE" in l]
    ok = bool(run) and ("(%d files)" % n) in run[0] and len(loads) == 2 and not errs
    print("running line:", run)
    print("loads:", loads)
    print("errors:", errs[:3])
    print("OK" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
