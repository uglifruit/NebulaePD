# uf2: a private Csound plugin folder for extra opcode libraries (Pearls' libpearls.so). Python 2 and 3 compatible.
#
# Csound's own folder (STOCK) is never written, so a stock revert leaves a stock system. Instead FARM holds a link to
# every stock plugin plus the extra plugins (real files in EXTRA). Csound is pointed at FARM through OPCODE6DIR64,
# and only while FARM is complete, so with nothing extra installed Csound runs exactly as stock.
#
# Extra plugins come from the stick folder USB_DIR (csound_plugins/). Each new or changed .so is first checked in a
# separate process, from a temporary folder holding only that plugin (csplugins_check.py: it must load into the
# module's Csound and, for Pearls, run and make sound). Only then is it copied into EXTRA. A plugin that failed is
# not retried until the stick has a different file.
import hashlib
import os
import shutil
import subprocess
import tempfile

STOCK = "/usr/lib/csound/plugins64-6.0/"
FARM = "/home/alarm/csound_plugins/"
USB_DIR = "/mnt/memory/csound_plugins/"
ENV = "OPCODE6DIR64"
CHECK_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csplugins_check.py")
CHECK_TIMEOUT = 90

generation = 0      # bumped when an extra plugin is installed: nebulae.py then resets Csound to load it


def extra_dir(farm=FARM):
    return farm + "extra/"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def plugins_in(folder):
    try:
        return sorted(n for n in os.listdir(folder) if n.endswith(".so") and os.path.isfile(folder + n))
    except Exception:
        return []


def build_farm(stock=STOCK, farm=FARM, link=None, readlink=None):
    """Link every stock plugin and every extra plugin into farm. Returns the extra plugin names. Never raises."""
    link = link or os.symlink
    readlink = readlink or os.readlink
    try:
        extra = extra_dir(farm)
        if not os.path.isdir(extra):
            os.makedirs(extra)
        wanted = {}
        for name in plugins_in(stock):
            wanted[name] = stock + name
        extras = plugins_in(extra)
        for name in extras:
            wanted[name] = extra + name          # an extra plugin wins over a stock one of the same name
        for name in os.listdir(farm):
            path = farm + name
            if name == "extra" or name.startswith("."):
                continue
            try:
                current = readlink(path)
            except Exception:
                current = None
            if wanted.get(name) != current:
                os.remove(path)
        for name, target in sorted(wanted.items()):
            if not os.path.lexists(farm + name):
                link(target, farm + name)
        return extras
    except Exception as e:
        print("csplugins: could not build " + farm + ": " + str(e))
        return []


def farm_complete(stock=STOCK, farm=FARM, readlink=None):
    readlink = readlink or os.readlink
    names = plugins_in(stock)
    if not names:
        return False
    for name in names:
        try:
            target = readlink(farm + name)
        except Exception:
            return False
        if target not in (stock + name, extra_dir(farm) + name):
            return False
    return True


def activate(stock=STOCK, farm=FARM, environ=None, readlink=None):
    """Point Csound at farm if it holds extra plugins and links every stock one; otherwise leave Csound as stock."""
    environ = os.environ if environ is None else environ
    if plugins_in(extra_dir(farm)) and farm_complete(stock, farm, readlink):
        environ[ENV] = farm
        return True
    environ.pop(ENV, None)
    return False


def run_check(plugin_path, timeout=CHECK_TIMEOUT):
    """Check one plugin in a separate Python 2 process: (ok, output)."""
    tmp = tempfile.mkdtemp(prefix="csplugin_check_")
    try:
        shutil.copyfile(plugin_path, os.path.join(tmp, os.path.basename(plugin_path)))
        cmd = ["timeout", "-k", "5", str(timeout), "python2", CHECK_SCRIPT, tmp, os.path.basename(plugin_path)]
        p = subprocess.Popen(cmd, stdin=open(os.devnull, "r"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.communicate()[0]
        if not isinstance(out, str):
            out = out.decode("utf-8", "replace")
        return p.returncode == 0, out.strip()
    except Exception as e:
        return False, "check could not run: " + str(e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def install_from_usb(usb_dir=USB_DIR, farm=FARM, stock=STOCK, check=run_check, link=None, readlink=None):
    """Install new or changed plugins from the stick. The caller has the stick mounted and the card writable.
    Returns log lines. Never raises."""
    global generation
    log = []
    try:
        names = plugins_in(usb_dir)
        if not names:
            return log
        extra = extra_dir(farm)
        if not os.path.isdir(extra):
            os.makedirs(extra)
        for name in names:
            digest = sha256(usb_dir + name)
            stamp = extra + "." + name + ".sha256"
            failed = extra + "." + name + ".failed"
            if os.path.isfile(extra + name) and _read(stamp) == digest:
                continue                                     # already installed
            if _read(failed) == digest:
                continue                                     # this file failed before: not retried
            ok, out = check(usb_dir + name)
            if ok:
                shutil.copyfile(usb_dir + name, extra + name + ".new")
                os.rename(extra + name + ".new", extra + name)
                _write(stamp, digest)
                if os.path.exists(failed):
                    os.remove(failed)
                generation += 1
                log.append("Csound plugin %s installed (%s): %s" % (name, digest[:12], out.splitlines()[-1:]))
            else:
                _write(failed, digest)
                log.append("Csound plugin %s NOT installed, its check failed: %s" % (name, out[-300:]))
        build_farm(stock, farm, link, readlink)
    except Exception as e:
        log.append("Csound plugin install failed: " + str(e))
    return log


def _read(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _write(path, text):
    with open(path, "w") as f:
        f.write(text + "\n")
