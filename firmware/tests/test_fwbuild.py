"""tools/fwbuild.py: packing fidelity and guards.  Run:  python firmware/tests/test_fwbuild.py"""
import io
import os
import subprocess
import sys
import tarfile
import unittest

sys.dont_write_bytecode = True
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))
import fwbuild  # noqa: E402

SOURCE_ARCHIVE = os.path.join(REPO, fwbuild.read_source()["archive"])   # the unit's tree the base came from


def members(data_or_path):
    t = tarfile.open(fileobj=io.BytesIO(data_or_path)) if isinstance(data_or_path, bytes) else tarfile.open(
        data_or_path)
    out = {}
    for m in t.getmembers():
        out[m.name.rstrip("/")] = (m.type, m.mode, t.extractfile(m).read() if m.isfile() else None)
    return out


class TestPack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = fwbuild.tree(os.path.join(fwbuild.FW, "base"))
        cls.src = fwbuild.tree(os.path.join(fwbuild.FW, "src"))
        cls.meta, cls.default = fwbuild.archive_meta(SOURCE_ARCHIVE)

    def test_source_is_the_unit(self):
        self.assertEqual(fwbuild.read_source()["provisional"], "no")
        self.assertTrue(os.path.isfile(SOURCE_ARCHIVE), SOURCE_ARCHIVE)

    def test_base_repack_equals_unit_tree(self):
        """Every non-runtime file of the unit's archive, byte for byte and with its mode, and nothing else."""
        def files(m):
            return {n: v for n, v in m.items() if v[0] != tarfile.DIRTYPE}
        a = files(members(fwbuild.pack(self.base, self.meta, self.default)))
        b = {n: v for n, v in files(members(SOURCE_ARCHIVE)).items()
             if not fwbuild.is_runtime(n[len("QB_Nebulae_V2/"):])}
        self.assertEqual(sorted(a), sorted(b))
        for name in b:
            self.assertEqual(a[name][2], b[name][2], name)
            self.assertEqual(a[name][1], b[name][1], name)

    def test_pi4_changes_kept(self):
        """Qu-Bit's Pi 4 changes on the unit (not on GitHub) must survive into uf1."""
        sr = self.src["Code/nebulae/shiftregister.py"]
        self.assertIn(b"time.sleep(0.00001)", sr)
        self.assertEqual(sr, self.base["Code/nebulae/shiftregister.py"])
        self.assertEqual(self.src["Code/nebulae/digitaldata.py"], self.base["Code/nebulae/digitaldata.py"])
        self.assertIn(b"bank='factory', initial_startup=False):", self.src["Code/nebulae/controlhandler.py"])
        neb = self.src["Code/nebulae/nebulae.py"]
        self.assertEqual(neb.count(b"initial_startup=initial_startup"), neb.count(b"ch.ControlHandler("))   # every engine

    def test_uf1_archive_layout(self):
        data = fwbuild.pack(self.src, self.meta, self.default, version="v2_1_2_uf1")
        m = members(data)
        self.assertIn("QB_Nebulae_V2/Code/nebulae/nebulae.py", m)       # update.sh checks Code/nebulae/ is non-empty
        self.assertTrue(all(n == "QB_Nebulae_V2" or n.startswith("QB_Nebulae_V2/") for n in m))
        cfg = m["QB_Nebulae_V2/Code/config.txt"][2].decode()
        self.assertIn("VERSION=v2_1_2_uf1\n", cfg)
        self.assertEqual(m["QB_Nebulae_V2/Code/scripts/update.sh"][1], self.meta["QB_Nebulae_V2/Code/scripts/update.sh"][0])
        self.assertTrue(m["QB_Nebulae_V2/Code/scripts/update.sh"][1] & 0o111)          # unit's mode, executable
        self.assertEqual(m["QB_Nebulae_V2/Code/nebulae/instrpager.py"][1], 0o644)
        for rel, data_ in self.src.items():
            if rel != "Code/config.txt":
                self.assertEqual(m["QB_Nebulae_V2/" + rel][2], data_, rel)
        self.assertEqual(data, fwbuild.pack(self.src, self.meta, self.default, version="v2_1_2_uf1"))  # reproducible

    def test_gnu_tar_reads_it(self):
        out = os.path.join(fwbuild.FW, "dist", "test_gnu_tar.tgz")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(fwbuild.pack(self.src, self.meta, self.default, version="v2_1_2_uf1"))
        tar = "C:/Program Files/Git/usr/bin/tar.exe"
        env = dict(os.environ, PATH=os.path.dirname(tar) + os.pathsep + os.environ.get("PATH", ""))  # finds gzip
        r = subprocess.run([tar, "-tvzf", "/c" + out.replace("\\", "/")[2:]], capture_output=True, text=True,
                           env=env)
        os.remove(out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("QB_Nebulae_V2/Code/nebulae/ufmigrate.py", r.stdout)


class TestGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = fwbuild.tree(os.path.join(fwbuild.FW, "base"))
        cls.src = fwbuild.tree(os.path.join(fwbuild.FW, "src"))

    def errs(self, **changes):
        src = dict(self.src)
        for rel, data in changes.items():
            rel = rel.replace("__", "/").replace("_DOT_", ".")
            if data is None:
                src.pop(rel)
            else:
                src[rel] = data
        return fwbuild.guard(self.base, src)[0]

    def test_current_src_passes(self):
        self.assertEqual(fwbuild.guard(self.base, self.src)[0], [])

    def test_protected_paths(self):
        for rel in ["Code/scripts/update.sh", "Code/scripts/startup.sh", "Code/localfiles/config.txt",
                    "Code/nebulae/bootleds.py", "Code/nebulae/calibration_collector.py", "Code/config.txt"]:
            src = dict(self.src)
            src[rel] = src[rel] + b"\n# touched\n"
            self.assertTrue(any("protected" in e for e in fwbuild.guard(self.base, src)[0]), rel)

    def test_check_calibration_only_the_import(self):
        rel = "Code/nebulae/check_calibration.py"
        src = dict(self.src)
        src[rel] = src[rel].replace(b"import time\n", b"import time\nimport os\n")
        self.assertTrue(any("only the added" in e for e in fwbuild.guard(self.base, src)[0]))
        src[rel] = self.base[rel]                                   # the stock bug back is also fine
        self.assertEqual(fwbuild.guard(self.base, src)[0], [])

    def test_new_files_and_bytecode(self):
        for rel in ["Code/scripts/new.sh", "Code/nebulae/sub/x.py", "Code/nebulae/__pycache__/x.pyc", "x.txt"]:
            src = dict(self.src)
            src[rel] = b"x"
            self.assertTrue(fwbuild.guard(self.base, src)[0], rel)

    def test_mandatory_files(self):
        """An empty mandatory file would make checkfirmware.sh revert the unit to factory v1.0.0."""
        src = dict(self.src)
        src["Code/nebulae/ui.py"] = b""
        self.assertTrue(any("mandatory" in e for e in fwbuild.guard(self.base, src)[0]))

    def test_removed_crlf_nonascii(self):
        src = dict(self.src)
        src.pop("Code/nebulae/settings.py")
        self.assertTrue(any("removed" in e for e in fwbuild.guard(self.base, src)[0]))
        src = dict(self.src)
        src["Code/nebulae/ui.py"] = src["Code/nebulae/ui.py"].replace(b"\n", b"\r\n")
        self.assertTrue(any("CR line" in e for e in fwbuild.guard(self.base, src)[0]))
        src = dict(self.src)
        src["Code/nebulae/nebopts.py"] = src["Code/nebulae/nebopts.py"] + "# \u00e9\n".encode("utf-8")
        self.assertTrue(any("non-ASCII" in e for e in fwbuild.guard(self.base, src)[0]))


class TestImportDevice(unittest.TestCase):
    """--import-device on a temporary copy of firmware/: the unit's tree becomes the base, uf1 changes carry over."""

    def setUp(self):
        import shutil
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.saved = fwbuild.FW
        fw = os.path.join(self.tmp, "firmware")
        for part in ["base", "src"]:
            shutil.copytree(os.path.join(self.saved, part), os.path.join(fw, part))
        fwbuild.FW = fw
        self.base = fwbuild.tree(os.path.join(fw, "base"))
        self.src0 = fwbuild.tree(os.path.join(fw, "src"))

    def tearDown(self):
        import shutil
        fwbuild.FW = self.saved
        shutil.rmtree(self.tmp)

    def device_zip(self, extra):
        files = dict(self.base)
        files.update(extra)
        meta, default = fwbuild.archive_meta(SOURCE_ARCHIVE)
        p = os.path.join(self.tmp, "neb_update.zip")
        with open(p, "wb") as f:
            f.write(fwbuild.pack(files, meta, default))
        return p

    def test_clean_import(self):
        p = self.device_zip({
            "Code/scripts/startup.sh": self.base["Code/scripts/startup.sh"] + b"# pi4 image change\n",
            "Code/misc/calibration_data.txt": b"pitch,0.027,\n",
            "Code/config/bootinstr.txt": b"bank,puredata\n",
            "Code/log/neb_log.txt": b"log\n"})
        fwbuild.import_device(p)
        base = fwbuild.tree(os.path.join(fwbuild.FW, "base"))
        src = fwbuild.tree(os.path.join(fwbuild.FW, "src"))
        self.assertTrue(base["Code/scripts/startup.sh"].endswith(b"# pi4 image change\n"))
        self.assertEqual(src["Code/scripts/startup.sh"], base["Code/scripts/startup.sh"])
        for rel in ["Code/misc/calibration_data.txt", "Code/config/bootinstr.txt", "Code/log/neb_log.txt"]:
            self.assertNotIn(rel, base)
            self.assertNotIn(rel, src)
        self.assertIn("Code/nebulae/instrpager.py", src)
        errors, changed, added = fwbuild.guard(base, src)
        self.assertEqual(errors, [])
        _, c0, a0 = fwbuild.guard(self.base, self.src0)
        self.assertEqual(len(changed) + len(added), len(c0) + len(a0))     # every uf change carried over
        self.assertEqual(fwbuild.read_source()["provisional"], "no")

    def test_device_bytecode_skipped(self):
        p = self.device_zip({"Code/nebulae/ui.pyc": b"\x03\xf3\r\n"})
        fwbuild.import_device(p)
        self.assertNotIn("Code/nebulae/ui.pyc", fwbuild.tree(os.path.join(fwbuild.FW, "base")))

    def test_clean_merge(self):
        """The unit changed a file uf1 also changed, in a different place: merged, both changes kept."""
        src0 = fwbuild.tree(os.path.join(fwbuild.FW, "src"))
        p = self.device_zip({"Code/nebulae/ui.py": self.base["Code/nebulae/ui.py"] + b"# pi4 tweak\n"})
        fwbuild.import_device(p)
        ui = fwbuild.tree(os.path.join(fwbuild.FW, "src"))["Code/nebulae/ui.py"]
        self.assertTrue(ui.endswith(b"# pi4 tweak\n"))
        self.assertIn(b"import instrpager", ui)
        self.assertEqual(ui, src0["Code/nebulae/ui.py"] + b"# pi4 tweak\n")

    def conflicting_zip(self):
        rel = "Code/nebulae/control.py"
        src = fwbuild.tree(os.path.join(fwbuild.FW, "src"))[rel]
        line = next(l for l in self.base[rel].splitlines(True) if l not in src.splitlines(True))
        return rel, self.device_zip({rel: self.base[rel].replace(line, line.rstrip(b"\n") + b"  # pi4\n", 1)})

    def test_conflict_stops_then_resolved_copy_is_used(self):
        rel, p = self.conflicting_zip()
        before = [fwbuild.tree(os.path.join(fwbuild.FW, d)) for d in ("base", "src")]
        with self.assertRaises(SystemExit):
            fwbuild.import_device(p)
        self.assertEqual([fwbuild.tree(os.path.join(fwbuild.FW, d)) for d in ("base", "src")], before)
        merge_file = os.path.join(fwbuild.FW, fwbuild.MERGE_DIR, *rel.split("/"))
        with open(merge_file, "rb") as f:
            self.assertIn(b"<<<<<<< uf1", f.read())
        with self.assertRaises(SystemExit):                       # markers still there: still refused
            fwbuild.import_device(p)
        with open(merge_file, "wb") as f:
            f.write(before[1][rel] + b"# resolved\n")
        fwbuild.import_device(p)
        self.assertEqual(fwbuild.tree(os.path.join(fwbuild.FW, "src"))[rel], before[1][rel] + b"# resolved\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
