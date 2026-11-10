#!/usr/bin/env python3
"""Build the SuperCollider runtime bundle and the probe's stick folder (docs/FIRMWARE.md, Stage 2).

  python tools/scbundle.py      # -> firmware/dist/sc_probe/  (copy its contents to the USB stick root)

Inputs (gitignored, under external/), checked against pinned sha256s:
  technobear_fw/neb_update*.zip   Technobear's 2.2.2 firmware: supercollider 3.10.4-2 + sc3-plugins 3.10.0-3 (armv7h)
  avahi_deb/libavahi-{client,common}3_0.8-5+deb11u2_armhf.deb   Debian 11, verified against the archive index
Bundle layout (unpacked to /tmp/sc on the module):
  bin/sclang bin/scsynth   lib/libscsynth.so.1*  lib/libavahi-{client,common}.so.3  lib/libreadline.so.7 -> the
  card's /usr/lib/libreadline.so.8 (same 12 functions)   plugins/*.so (core + sc3-plugins, without the two Stk
  plugins, which need stk 4.5.1; the card has 4.6.2)   share/SCClassLibrary  share/Extensions/SC3plugins (no help)
  sclang_conf.yaml
Nothing is executed; the archive is reproducible (sorted entries, fixed mtime, gzip mtime 0).
"""
import glob
import gzip
import hashlib
import io
import lzma
import os
import shutil
import sys
import tarfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "firmware", "dist", "sc_probe")
MTIME = 1651363200  # 2022-05-01: the module's clock restarts around 2022-06-11 (no RTC)

TB_ZIP_SHA = "b7e37e11c954d00b2958124f1001ba61f61476636c4483324ec23d3316ed1416"
DEBS = {
    "libavahi-client3_0.8-5+deb11u2_armhf.deb": "250ec4e04b445e947298f81e5be65a180a7a07a436cf5eac52b5444e894afff0",
    "libavahi-common3_0.8-5+deb11u2_armhf.deb": "5524a261c699f059eba1396d95fa825f936dfa34e877e6fcd053d16cde12ec09",
}
PKG_DIR = "QB_Nebulae_V2/Code/packages/"
SC_PKG = PKG_DIR + "supercollider-3.10.4-2-armv7h.pkg.tar.xz"
PLUGINS_PKG = PKG_DIR + "sc3-plugins-3.10.0-3-armv7h.pkg.tar.xz"
PROBE = os.path.join(REPO, "sc", "probe")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_tb_zip():
    for p in sorted(glob.glob(os.path.join(REPO, "external", "technobear_fw", "neb_update*.zip"))):
        if sha256(p) == TB_ZIP_SHA:
            return p
    sys.exit("Technobear's neb_update.zip (sha256 %s) not found in external/technobear_fw/" % TB_ZIP_SHA)


def deb_data(path):
    """Members of a .deb's data.tar.* (a .deb is an ar archive)."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"!<arch>\n", path
    pos = 8
    while pos < len(data):
        name = data[pos:pos + 16].decode().strip().rstrip("/")
        size = int(data[pos + 48:pos + 58].decode().strip())
        body = data[pos + 60:pos + 60 + size]
        pos += 60 + size + (size & 1)
        if name.startswith("data.tar"):
            return tarfile.open(fileobj=io.BytesIO(body))
    sys.exit("no data.tar in " + path)


class Bundle(object):
    def __init__(self):
        self.files = {}     # path -> (mode, bytes)
        self.links = {}     # path -> target

    def add(self, path, mode, data):
        self.files[path] = (mode, data)

    def link(self, path, target):
        self.links[path] = target

    def take(self, tar, prefix, dest, skip=lambda rel: False):
        """Copy members under `prefix` to `dest`, keeping symlinks and modes."""
        n = 0
        for m in tar.getmembers():
            if not m.name.startswith(prefix):
                continue
            rel = m.name[len(prefix):].lstrip("/")
            if (not rel and m.name != prefix) or skip(rel):
                continue
            target = dest + rel     # rel is empty when `prefix` names a single file
            if m.issym():
                self.link(target, m.linkname)
            elif m.isfile():
                self.add(target, m.mode & 0o777, tar.extractfile(m).read())
                n += 1
        return n

    def tgz(self):
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as t:
            dirs = set()
            for p in list(self.files) + list(self.links):
                parts = p.split("/")[:-1]
                for i in range(1, len(parts) + 1):
                    dirs.add("/".join(parts[:i]))
            for p in sorted(dirs | set(self.files) | set(self.links)):
                ti = tarfile.TarInfo(p)
                ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = MTIME, 0, 0, "root", "root"
                if p in dirs:
                    ti.type, ti.mode = tarfile.DIRTYPE, 0o755
                    t.addfile(ti)
                elif p in self.links:
                    ti.type, ti.linkname, ti.mode = tarfile.SYMTYPE, self.links[p], 0o777
                    t.addfile(ti)
                else:
                    mode, data = self.files[p]
                    ti.size, ti.mode = len(data), mode
                    t.addfile(ti, io.BytesIO(data))
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode="wb", mtime=0, compresslevel=9) as g:
            g.write(raw.getvalue())
        return out.getvalue()


def main():
    tb = find_tb_zip()
    for name, want in DEBS.items():
        p = os.path.join(REPO, "external", "avahi_deb", name)
        if not os.path.isfile(p) or sha256(p) != want:
            sys.exit("missing or changed: external/avahi_deb/" + name)
    b = Bundle()
    with tarfile.open(tb) as fw:
        sc = tarfile.open(fileobj=io.BytesIO(lzma.decompress(fw.extractfile(SC_PKG).read())))
        pl = tarfile.open(fileobj=io.BytesIO(lzma.decompress(fw.extractfile(PLUGINS_PKG).read())))
    for exe in ("sclang", "scsynth"):
        b.take(sc, "usr/bin/" + exe, "bin/" + exe)
    b.take(sc, "usr/lib/", "lib/", skip=lambda rel: not rel.startswith("libscsynth.so"))
    n_core = b.take(sc, "usr/lib/SuperCollider/plugins/", "plugins/")
    n_ext = b.take(pl, "usr/lib/SuperCollider/plugins/", "plugins/", skip=lambda rel: rel.startswith("Stk"))
    b.take(sc, "usr/share/SuperCollider/SCClassLibrary/", "share/SCClassLibrary/")
    b.take(pl, "usr/share/SuperCollider/Extensions/SC3plugins/", "share/Extensions/SC3plugins/",
           skip=lambda rel: "HelpSource" in rel.split("/") or rel.endswith(".schelp"))
    for name in DEBS:
        d = deb_data(os.path.join(REPO, "external", "avahi_deb", name))
        for m in d.getmembers():
            base = os.path.basename(m.name)
            if m.name.startswith("./usr/lib/arm-linux-gnueabihf/libavahi-") and ".so.3" in base:
                if m.issym():
                    b.link("lib/" + base, m.linkname)
                elif m.isfile():
                    b.add("lib/" + base, 0o755, d.extractfile(m).read())
    b.link("lib/libreadline.so.7", "/usr/lib/libreadline.so.8")
    with open(os.path.join(PROBE, "sclang_conf.yaml"), "rb") as f:
        b.add("sclang_conf.yaml", 0o644, f.read())
    for need in ("bin/sclang", "bin/scsynth", "lib/libscsynth.so.1.0.0", "lib/libavahi-client.so.3.2.9",
                 "lib/libavahi-common.so.3.5.4", "share/SCClassLibrary/Common/Core/Object.sc"):
        assert need in b.files, need
    for need in ("lib/libscsynth.so.1", "lib/libavahi-client.so.3", "lib/libavahi-common.so.3"):
        assert need in b.links, need
    data = b.tgz()

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    folder = os.path.join(OUT, "neb_scprobe")
    os.makedirs(folder)
    with open(os.path.join(folder, "sc_runtime.tgz"), "wb") as f:
        f.write(data)
    for name in ("run.sh", "probe_nrt.scd", "probe_rt.scd"):
        with open(os.path.join(PROBE, name), "rb") as f:
            text = f.read().replace(b"\r\n", b"\n")
        with open(os.path.join(folder, name), "wb") as f:
            f.write(text)
    shutil.copyfile(os.path.join(REPO, "instr", "sc_probe.instr"), os.path.join(OUT, "000_sc_probe.instr"))
    print("bundle: %d files, %d links, %d core + %d sc3 plugins, %.1f MB, sha256 %s" % (
        len(b.files), len(b.links), n_core, n_ext, len(data) / 1e6, hashlib.sha256(data).hexdigest()))
    print("wrote %s: 000_sc_probe.instr + neb_scprobe/ -> copy both to the stick root"
          % os.path.relpath(OUT, REPO))


if __name__ == "__main__":
    main()
