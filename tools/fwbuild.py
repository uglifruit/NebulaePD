#!/usr/bin/env python3
"""Build a Nebulae firmware update (neb_update.zip = tar.gz of QB_Nebulae_V2/Code/...) from firmware/src.

  python tools/fwbuild.py                 # uf1 from firmware/src, guarded against firmware/base
  python tools/fwbuild.py --from base     # repack the unmodified base (a revert package)
  python tools/fwbuild.py --check         # guards only, no output

Guards (the update path must survive any custom build, so a revert always works):
  - Code/scripts, Code/localfiles, Code/config, Code/misc, Code/log and the Python files run during boot/update
    before the app (bootleds.py, calibration_collector.py) are identical to the base;
  - check_calibration.py differs from the base only by the added `import neb_globals` line;
  - the unit's mandatory files (checkfirmware.sh's list) are present and non-empty;
  - new files are only Code/nebulae/*.py; no new .pyc or __pycache__;
  - changed/new .py files are ASCII with LF line ends.
The base must come from the unit itself (firmware/base/SOURCE.txt: provisional=no). With the provisional GitHub
base the build only writes neb_update_PROVISIONAL_DO_NOT_INSTALL.tgz, a name update.sh ignores.

File modes and owners are copied from the base archive (SOURCE.txt `archive=`); new files get 0644. The archive is
reproducible (sorted entries, fixed mtimes, gzip mtime 0): the same tree gives the same sha256. The fixed mtime is
2022-05-01: the unit has no RTC and its clock restarts around 2022-06-11 every boot, so later dates are "in the
future" there.
"""
import argparse
import gzip
import hashlib
import io
import os
import sys
import tarfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(REPO, "firmware")
VERSION = "v2_1_2_uf2"

PROTECTED_DIRS = ["Code/scripts/", "Code/localfiles/", "Code/config/", "Code/misc/", "Code/log/"]
PROTECTED_FILES = ["Code/nebulae/bootleds.py", "Code/nebulae/calibration_collector.py", "Code/config.txt"]
ONE_LINE_FIX = ("Code/nebulae/check_calibration.py", "import neb_globals\n")
# /home/alarm/mandatory_files.txt on the unit (outside the tree): checkfirmware.sh reverts to the factory v1.0.0
# tree if any of these is missing or empty under Code/
MANDATORY = ["nebulae/bootleds.py", "nebulae/conductor.py", "nebulae/controlhandler.py", "nebulae/nebulae.py",
             "nebulae/ui.py", "scripts/enable_inputs.sh", "scripts/mountfs.sh", "scripts/startup.sh",
             "scripts/sys_opt.sh", "scripts/update.sh"]


def tree(root):
    """{relative path under QB_Nebulae_V2/: bytes} for every file."""
    top = os.path.join(root, "QB_Nebulae_V2")
    out = {}
    for d, dirs, files in os.walk(top):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(d, f)
            rel = os.path.relpath(p, top).replace("\\", "/")
            with open(p, "rb") as fh:
                out[rel] = fh.read()
    return out


def read_source():
    info = {}
    with open(os.path.join(FW, "base", "SOURCE.txt")) as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                info[k.strip()] = v.strip()
    return info


def guard(base, src):
    errors, changed, added = [], [], []
    for m in MANDATORY:
        if not src.get("Code/" + m):
            errors.append("mandatory file missing or empty (checkfirmware.sh would revert to factory): Code/" + m)
    for rel in sorted(set(base) - set(src)):
        errors.append("removed from src: " + rel)
    for rel in sorted(src):
        if rel not in base:
            added.append(rel)
            if not (rel.startswith("Code/nebulae/") and rel.endswith(".py") and rel.count("/") == 2):
                errors.append("new file outside Code/nebulae/*.py: " + rel)
        elif src[rel] != base[rel]:
            changed.append(rel)
    for rel in changed:
        if any(rel.startswith(d) for d in PROTECTED_DIRS) or rel in PROTECTED_FILES:
            errors.append("protected file changed: " + rel)
        elif rel == ONE_LINE_FIX[0]:
            b = base[rel].decode("ascii").splitlines(True)
            s = src[rel].decode("ascii").splitlines(True)
            extra = list(s)
            for line in b:
                if line in extra:
                    extra.remove(line)
            if len(s) != len(b) + 1 or extra != [ONE_LINE_FIX[1]]:
                errors.append(rel + ": only the added '" + ONE_LINE_FIX[1].strip() + "' line is allowed")
        elif rel.endswith((".pyc",)) or "__pycache__" in rel:
            errors.append("bytecode changed: " + rel)
    for rel in changed + added:
        if rel.endswith(".py"):
            data = src[rel]
            if b"\r" in data:
                errors.append("CR line ends: " + rel)
            try:
                data.decode("ascii")
            except UnicodeDecodeError:
                errors.append("non-ASCII: " + rel)
    return errors, changed, added


def archive_meta(path):
    """{name: (mode, uid, gid, uname, gname)} from the base archive, plus a default for new entries."""
    meta, default = {}, (0o644, 1000, 1000, "alarm", "alarm")
    if path and os.path.isfile(path):
        with tarfile.open(path) as t:
            for m in t.getmembers():
                meta[m.name.rstrip("/")] = (m.mode, m.uid, m.gid, m.uname, m.gname)
        root = meta.get("QB_Nebulae_V2")
        if root:
            default = (0o644,) + root[1:]
    return meta, default


def pack(files, meta, default, version=None, mtime=1651363200):
    """tar.gz bytes of QB_Nebulae_V2/<files>; version rewrites Code/config.txt's VERSION line."""
    files = dict(files)
    if version:
        lines = files["Code/config.txt"].decode("ascii").splitlines(True)
        lines = ["VERSION=" + version + "\n" if l.startswith("VERSION=") else l for l in lines]
        files["Code/config.txt"] = "".join(lines).encode("ascii")
    dirs = set(["QB_Nebulae_V2"])
    for rel in files:
        parts = ("QB_Nebulae_V2/" + rel).split("/")[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:i]))
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as t:
        for name in sorted(dirs | set("QB_Nebulae_V2/" + r for r in files)):
            ti = tarfile.TarInfo(name)
            mode, uid, gid, uname, gname = meta.get(name, default)
            ti.uid, ti.gid, ti.uname, ti.gname, ti.mtime = uid, gid, uname, gname, mtime
            if name in dirs:
                ti.type, ti.mode = tarfile.DIRTYPE, 0o755
                t.addfile(ti)
            else:
                data = files[name[len("QB_Nebulae_V2/"):]]
                ti.size, ti.mode = len(data), mode
                t.addfile(ti, io.BytesIO(data))
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as g:
        g.write(raw.getvalue())
    return out.getvalue()


# runtime state inside the tree: never part of the base or a build (update.sh replaces the tree; ufmigrate restores)
RUNTIME = ["Code/config/bootinstr.txt", "Code/config/nebsettings.txt", "Code/config/buffer_cnt.txt",
           "Code/config/neb_options.txt", "Code/config/uf_migrated", "Code/config/boot_guard.txt", "Code/misc/calibration_data.txt"]
RUNTIME_DIRS = ["Code/log/"]
MERGE_DIR = "dist/merge"     # under firmware/: conflict files from --import-device, resolved by hand


def is_runtime(rel):
    """Runtime state, or bytecode Python 2 wrote next to a module on the unit (Code/nebulae/x.pyc)."""
    if rel in RUNTIME or any(rel.startswith(d) for d in RUNTIME_DIRS):
        return True
    return rel.startswith("Code/nebulae/") and rel.endswith(".pyc") and rel.count("/") == 2


def merge3(ours, base, theirs):
    """git merge-file: (merged bytes, number of conflicts)."""
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    paths = []
    for tag, data in (("uf1", ours), ("previous-base", base), ("unit", theirs)):
        p = os.path.join(d, tag)
        with open(p, "wb") as f:
            f.write(data)
        paths.append(p)
    r = subprocess.run(["git", "merge-file", "-p", "-L", "uf1", "-L", "previous-base", "-L", "unit"] + paths,
                       capture_output=True)
    import shutil
    shutil.rmtree(d)
    if r.returncode < 0 or r.returncode > 127:
        raise RuntimeError("git merge-file failed: " + r.stderr.decode(errors="replace"))
    return r.stdout, r.returncode


def write_tree(root, files):
    import shutil
    top = os.path.join(root, "QB_Nebulae_V2")
    if os.path.isdir(top):
        shutil.rmtree(top)
    for rel, data in files.items():
        p = os.path.join(top, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)


def import_device(archive, source_name="unit-backup"):
    """Make the unit's tree the base and carry the uf1 changes over. A file uf1 changed that the unit also changed
    gets a three-way merge (previous base = common ancestor). Clean merges are taken. Conflicts are written with
    markers to firmware/dist/merge/<path>, and nothing else is written; resolve the file there (no markers left)
    and run the import again, which then takes the resolved copy."""
    with tarfile.open(archive) as t:
        dev = {}
        for m in t.getmembers():
            if m.isfile() and m.name.startswith("QB_Nebulae_V2/"):
                rel = m.name[len("QB_Nebulae_V2/"):]
                if is_runtime(rel):
                    continue
                dev[rel] = t.extractfile(m).read()
    old = tree(os.path.join(FW, "base"))
    src = tree(os.path.join(FW, "src"))
    _, changed, added = guard(old, src)
    differs = sorted(r for r in set(old) | set(dev) if old.get(r) != dev.get(r))
    print("unit tree vs previous base: %d files differ" % len(differs))
    for rel in differs:
        print("  %s %s" % ("+" if rel not in old else "-" if rel not in dev else "~", rel))
    new_src = dict(dev)
    for rel in changed + added:
        new_src[rel] = src[rel]
    unresolved = []
    for rel in [r for r in changed + added if r in differs]:
        resolved = os.path.join(FW, MERGE_DIR, *rel.split("/"))
        if rel in added or rel not in dev:
            unresolved.append((rel, "uf1 adds it, the unit has or lacks its own copy"))
            continue
        if os.path.isfile(resolved):
            with open(resolved, "rb") as f:
                data = f.read()
            if b"<<<<<<<" not in data and b">>>>>>>" not in data:
                new_src[rel] = data
                print("  merged (resolved copy): " + rel)
                continue
        merged, n = merge3(src[rel], old[rel], dev[rel])
        if n == 0:
            new_src[rel] = merged
            print("  merged (clean): " + rel)
        else:
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            with open(resolved, "wb") as f:
                f.write(merged)
            unresolved.append((rel, "%d conflict(s), see %s" % (n, os.path.relpath(resolved, REPO))))
    if unresolved:
        print("CONFLICTS - nothing written. Resolve these, then run the import again:")
        for rel, why in unresolved:
            print("  %s: %s" % (rel, why))
        sys.exit(1)
    write_tree(os.path.join(FW, "base"), dev)
    write_tree(os.path.join(FW, "src"), new_src)
    rel_archive = os.path.relpath(os.path.abspath(archive), REPO).replace("\\", "/")
    with open(os.path.join(FW, "base", "SOURCE.txt"), "w", newline="\n") as f:
        f.write("source=%s\nprovisional=no\narchive=%s\nnote=the unit's own tree; runtime files (calibration, last "
                "instrument, settings, logs, bytecode compiled on the unit) left out\n" % (source_name, rel_archive))
    print("base <- %s (%d files); src = base + %d uf1 changes. Run the tests, then build." % (
        rel_archive, len(dev), len(changed) + len(added)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", choices=["src", "base"], default="src")
    ap.add_argument("--version", default=VERSION)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--import-device", metavar="NEB_UPDATE_ZIP",
                    help="replace the base with the unit's tree (firmware/device_image/neb_update.zip)")
    ap.add_argument("--source-name", default="unit-backup", help="source= label for SOURCE.txt on import")
    a = ap.parse_args()
    if a.import_device:
        import_device(a.import_device, a.source_name)
        return
    source = read_source()
    provisional = source.get("provisional", "yes") != "no"
    base = tree(os.path.join(FW, "base"))
    src = tree(os.path.join(FW, "src"))
    errors, changed, added = guard(base, src)
    print("base: %s (%s)" % (source.get("source", "?"), "PROVISIONAL" if provisional else "from the unit"))
    print("changed: %d  added: %d" % (len(changed), len(added)))
    for rel in changed:
        print("  M " + rel)
    for rel in added:
        print("  A " + rel)
    if errors:
        print("GUARD FAILED:")
        for e in errors:
            print("  " + e)
        sys.exit(1)
    print("guards OK")
    if a.check:
        return
    meta, default = archive_meta(source.get("archive") and os.path.join(REPO, source["archive"]))
    if a.frm == "base":
        data, version = pack(base, meta, default), "base"
    else:
        data, version = pack(src, meta, default, version=a.version), a.version
    name = "neb_update_PROVISIONAL_DO_NOT_INSTALL.tgz" if provisional else "neb_update.zip"
    outdir = os.path.join(FW, "dist", version)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, name)
    with open(out, "wb") as f:
        f.write(data)
    digest = hashlib.sha256(data).hexdigest()
    manifest = "version=%s\nbase=%s\nprovisional=%s\nsha256=%s\nfile=%s\n" % (
        version, source.get("source"), provisional, digest, name)
    manifest += "".join("M %s\n" % rel for rel in changed) + "".join("A %s\n" % rel for rel in added)
    # the same archive under names update.sh ignores, for fw_backup.instr's on-module Python 2 check
    for fname, payload in [("manifest.txt", manifest.encode("ascii")), ("neb_candidate.tgz", data),
                           ("neb_candidate_manifest.txt", manifest.encode("ascii"))]:
        with open(os.path.join(outdir, fname), "wb") as f:
            f.write(payload)
    print("wrote %s (%d bytes)\nsha256 %s" % (os.path.relpath(out, REPO), len(data), digest))
    print("for the on-module Python 2 check, copy neb_candidate.tgz + neb_candidate_manifest.txt to the stick")
    if provisional:
        print("PROVISIONAL base: not installable. Replace firmware/base with the unit's backup first (docs/FIRMWARE.md).")


if __name__ == "__main__":
    main()
