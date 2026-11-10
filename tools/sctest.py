#!/usr/bin/env python3
"""Run SuperCollider scripts on the PC (SC 3.10.4 + sc3-plugins 3.10.0, the module's versions) for offline tests.

  python tools/sctest.py check a.scd [b.scd ...]   # syntax only: sclang compiles each file, nothing runs
  python tools/sctest.py run   a.scd [seconds]     # run a script (e.g. an NRT render that ends with 0.exit)

The module and the PC render identically (sc/probe/probe_nrt.scd: same frames, sine within 1 LSB), so NRT renders
here can be checked with tools/wavcheck.py / tools/wavpeaks.py like the Pd batch tests.
A script meant for the module may use /tmp paths; for `run`, pass a PC copy or a script that takes paths from
`thisProcess.argv`.
"""
import os
import subprocess
import sys
import tempfile

SC_DIR = r"C:\Program Files\SuperCollider-3.10.4"
SCLANG = os.path.join(SC_DIR, "sclang.exe")


def sclang(script_path, timeout):
    env = dict(os.environ, PATH=SC_DIR + os.pathsep + os.environ.get("PATH", ""))   # sclang starts scsynth.exe
    try:
        r = subprocess.run([SCLANG, script_path], cwd=SC_DIR, env=env, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        return None, out + "\nTIMEOUT after %d s" % timeout


def check(paths):
    lines = ["(", "var bad = 0;"]
    for p in paths:
        q = os.path.abspath(p).replace("\\", "/")
        lines.append('if(File.readAllString("%s").compile.isNil, { bad = bad + 1; "SCTEST SYNTAX ERROR %s".postln },'
                     ' { "SCTEST SYNTAX OK %s".postln });' % (q, os.path.basename(p), os.path.basename(p)))
    lines += ['"SCTEST DONE".postln;', "bad.exit;", ")"]
    fd, tmp = tempfile.mkstemp(suffix=".scd")
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n")
    try:
        code, out = sclang(tmp, 120)
    finally:
        os.remove(tmp)
    shown = [l for l in out.splitlines() if l.startswith("SCTEST") or "ERROR" in l or "rror" in l]
    print("\n".join(shown))
    ok = code == 0 and "SCTEST DONE" in out
    return 0 if ok else 1


def run(path, seconds=120):
    code, out = sclang(os.path.abspath(path), seconds)
    print(out)
    return 0 if code == 0 else 1


def main():
    if not os.path.isfile(SCLANG):
        sys.exit("SuperCollider 3.10.4 not found at " + SC_DIR)
    if len(sys.argv) < 3 or sys.argv[1] not in ("check", "run"):
        sys.exit(__doc__)
    if sys.argv[1] == "check":
        sys.exit(check(sys.argv[2:]))
    sys.exit(run(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 120))


if __name__ == "__main__":
    main()
