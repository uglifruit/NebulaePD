# uf2: runs a SuperCollider patch (Technobear-compatible). Python 2 and 3 compatible.
#
# A patch is an sclang script (/home/alarm/sc/<name>.scd, copied from the stick like .pd files) that boots the
# server itself (s.waitForBoot) and listens with OSCdef on port 3000 (scsender.py). This runs:
#   jackd -R -P75 -dalsa -dhw:0 -p<sc_period> -n<sc_nperiods> -s -r48000   (JACK_NO_AUDIO_RESERVATION=1: the module
#       has no D-Bus session bus, and without it jack2 1.9.21 can't acquire hw:0; SC probe run 1)
#   sclang -D -l <conf> <patch>   with the runtime's libraries, plugins and class library, and a startup file that
#       sets Technobear's server options.
# The runtime (tools/scbundle.py: SC 3.10.4 + sc3-plugins from Technobear's firmware, Debian avahi libs) is installed
# once from the stick's sc_runtime.tgz into RUNTIME, outside the firmware tree, so firmware updates stay small and a
# stock revert leaves it unused.
import hashlib
import os
import shutil
import subprocess
import tarfile
import time

RUNTIME = "/home/alarm/sc_runtime/"
PATCH_DIR = "/home/alarm/sc/"
WORK = "/tmp/neb_sc/"
USB_BUNDLE = "/mnt/memory/sc_runtime.tgz"
STAMP = ".bundle_sha256"
READY = "SuperCollider 3 server ready"
START_TIMEOUT = 30.0
JACK_SETTLE = 3.0

STARTUP = """// written by the Nebulae firmware (uf2, scengine.py) before every SuperCollider patch
// Technobear's server options (his firmware's startup.scd), plus the runtime's plugin folder
Server.local.options.memSize = 16 * 8192;
Server.local.options.bindAddress = "0.0.0.0";
Server.local.options.maxLogins = 4;
Server.local.options.blockSize = 64;
Server.local.options.numInputBusChannels = 2;
Server.local.options.numOutputBusChannels = 2;
Server.local.options.sampleRate = 48000;
Server.local.options.ugenPluginsPath = "%(runtime)splugins";
Server.internal.options.memSize = 16 * 8192;
Server.internal.options.blockSize = 64;
Server.internal.options.numInputBusChannels = 2;
Server.internal.options.numOutputBusChannels = 2;
Server.internal.options.ugenPluginsPath = "%(runtime)splugins";
s = Server.default;
thisProcess.openUDPPort(3000);
// tells the firmware the patch's server is up (the log may be block-buffered)
ServerBoot.add({ File.use("%(work)sready", "w", { |f| f.write("ready") }) });
"""

CONF = """includePaths:
    - %(runtime)sshare/SCClassLibrary
    - %(runtime)sshare/Extensions
excludePaths:
    []
postInlineWarnings: false
excludeDefaultPaths: true
"""


def runtime_ok(runtime=RUNTIME):
    for rel in ("bin/sclang", "bin/scsynth", "lib/libscsynth.so.1", "share/SCClassLibrary"):
        if not os.path.exists(runtime + rel):
            return False
    return True


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def install_from_usb(bundle=USB_BUNDLE, runtime=RUNTIME):
    """Install or update the runtime from the stick. The caller has the stick mounted and the card writable.
    Returns a log line, or None when the stick has no bundle. Never raises."""
    try:
        if not os.path.isfile(bundle):
            return None
        digest = sha256(bundle)
        stamp = runtime + STAMP
        if os.path.isfile(stamp) and runtime_ok(runtime):
            with open(stamp, "r") as f:
                if f.read().strip() == digest:
                    return "SuperCollider runtime up to date"
        new = runtime.rstrip("/") + ".new/"
        if os.path.isdir(new):
            shutil.rmtree(new)
        os.makedirs(new)
        t = tarfile.open(bundle)
        t.extractall(new)
        t.close()
        if not runtime_ok(new):
            shutil.rmtree(new)
            return "SuperCollider runtime: bundle incomplete, not installed"
        with open(new + STAMP, "w") as f:
            f.write(digest + "\n")
        if os.path.isdir(runtime):
            shutil.rmtree(runtime)
        os.rename(new.rstrip("/"), runtime.rstrip("/"))
        return "SuperCollider runtime installed (" + digest[:12] + ")"
    except Exception as e:
        return "SuperCollider runtime install failed: " + str(e)


def jackd_cmd(period=256, nperiods=2):
    return ["jackd", "-R", "-P75", "-dalsa", "-dhw:0", "-p%d" % int(period), "-n%d" % int(nperiods), "-s", "-r48000"]


def environment(runtime=RUNTIME, work=WORK, base=None):
    env = dict(os.environ if base is None else base)
    env["LD_LIBRARY_PATH"] = runtime + "lib"
    env["PATH"] = runtime + "bin:" + env.get("PATH", "/usr/bin:/bin")
    env["HOME"] = work + "home"
    env["SC_PLUGIN_PATH"] = runtime + "plugins"
    env["SC_JACK_DEFAULT_OUTPUTS"] = "system:playback_1,system:playback_2"
    env["SC_JACK_DEFAULT_INPUTS"] = "system:capture_1,system:capture_2"
    env["JACK_NO_AUDIO_RESERVATION"] = "1"
    return env


def tail(path, n=40):
    try:
        with open(path, "r") as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return ""


class ScEngine(object):
    def __init__(self, patch, period=256, nperiods=2, runtime=RUNTIME, work=WORK, popen=subprocess.Popen,
                 clock=time.time, sleep=time.sleep):
        self.patch, self.period, self.nperiods = patch, period, nperiods
        self.runtime, self.work = runtime, work
        self.popen, self.clock, self.sleep = popen, clock, sleep
        self.jackd = self.sclang = None
        self.state, self.reason = "idle", ""
        self.started_at = 0.0
        self.next_check = 0.0
        self.sclang_log = work + "sclang.log"
        self.jackd_log = work + "jackd.log"

    def fail(self, reason):
        self.state, self.reason = "failed", reason
        return self.state

    def write_files(self):
        home_cfg = self.work + "home/.config/SuperCollider/"
        if not os.path.isdir(home_cfg):
            os.makedirs(home_cfg)
        with open(home_cfg + "startup.scd", "w") as f:
            f.write(STARTUP % {"runtime": self.runtime, "work": self.work})
        if os.path.exists(self.work + "ready"):
            os.remove(self.work + "ready")
        with open(self.work + "sclang_conf.yaml", "w") as f:
            f.write(CONF % {"runtime": self.runtime})

    def spawn(self, cmd, env, log):
        # the child keeps its own copies of the log and /dev/null handles; close ours (no leak per patch load)
        out = open(log, "w")
        nul = open(os.devnull, "r")
        try:
            return self.popen(cmd, env=env, cwd=self.work, stdin=nul, stdout=out, stderr=subprocess.STDOUT)
        finally:
            out.close()
            nul.close()

    def start(self):
        """Start jackd, then sclang with the patch. Returns "starting" or "failed" (see reason)."""
        if not runtime_ok(self.runtime):
            return self.fail("SuperCollider runtime missing: put sc_runtime.tgz in the stick root and reload")
        if not os.path.isfile(self.patch):
            return self.fail("patch not found: " + self.patch)
        try:
            if not os.path.isdir(self.work):
                os.makedirs(self.work)
            self.write_files()
            env = environment(self.runtime, self.work)
            self.jackd = self.spawn(jackd_cmd(self.period, self.nperiods), env, self.jackd_log)
            # jackd's info lines go to a block-buffered stdout, so they may show up late: wait until it has stayed
            # up JACK_SETTLE seconds (the SC probe waited 5 s), or until it reports the device open
            deadline = self.clock() + JACK_SETTLE
            while self.clock() < deadline:
                if self.jackd.poll() is not None:
                    return self.fail("jackd exited: " + tail(self.jackd_log, 6).strip())
                if "periods for playback" in tail(self.jackd_log, 20):
                    break
                self.sleep(0.1)
            self.sclang = self.spawn(["sclang", "-D", "-l", self.work + "sclang_conf.yaml", self.patch], env,
                                     self.sclang_log)
        except Exception as e:
            return self.fail("could not start: " + str(e))
        self.started_at = self.clock()
        self.state = "starting"
        return self.state

    def poll(self):
        """Call every pass: "starting", "ready" or "failed" (see reason)."""
        if self.state not in ("starting", "ready"):
            return self.state
        if self.jackd is not None and self.jackd.poll() is not None:
            return self.fail("jackd exited")
        if self.sclang is not None and self.sclang.poll() is not None:
            return self.fail("sclang exited (the patch stopped or has an error)")
        now = self.clock()
        if self.state == "starting" and now >= self.next_check:
            self.next_check = now + 0.25
            if os.path.exists(self.work + "ready") or READY in tail(self.sclang_log, 400):
                self.state = "ready"
            elif now - self.started_at > START_TIMEOUT:
                return self.fail("the patch did not start the server within %d s" % START_TIMEOUT)
        return self.state

    def stop(self):
        """Stop sclang, scsynth and jackd, waiting up to 2 s each, so the next engine finds hw:0 free."""
        for proc in (self.sclang, None, self.jackd):
            if proc is None:
                os.system("pkill -x scsynth")
                continue
            try:
                if proc.poll() is None:
                    proc.terminate()
                deadline = self.clock() + 2.0
                while proc.poll() is None and self.clock() < deadline:
                    self.sleep(0.02)
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
            except Exception:
                pass
        os.system("pkill -9 -x scsynth")
        self.sclang = self.jackd = None
        if self.state != "failed":
            self.state = "stopped"

    def report(self):
        return ("SuperCollider patch: %s\nreason: %s\n--- sclang (last lines)\n%s\n--- jackd (last lines)\n%s\n"
                % (self.patch, self.reason, tail(self.sclang_log), tail(self.jackd_log, 15)))
