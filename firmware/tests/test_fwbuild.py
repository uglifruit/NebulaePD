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

STOCK = os.path.join(REPO, "external", "QB_Nebulae_V2", "FirmwareUpdates", "v_2_1_2", "neb_update.zip")


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
        cls.meta, cls.default = fwbuild.archive_meta(STOCK)

    def test_base_repack_equals_stock_zip(self):
        if not os.path.isfile(STOCK):
            self.skipTest("external/ clone missing")
        a = members(fwbuild.pack(self.base, self.meta, self.default))
        b = members(STOCK)
        self.assertEqual(sorted(a), sorted(b))
        for name in b:
            self.assertEqual(a[name][0], b[name][0], name)
            self.assertEqual(a[name][2], b[name][2], name)
            if b[name][0] != tarfile.DIRTYPE:
                self.assertEqual(a[name][1], b[name][1], name)

    def test_uf1_archive_layout(self):
        data = fwbuild.pack(self.src, self.meta, self.default, version="v2_1_2_uf1")
        m = members(data)
        self.assertIn("QB_Nebulae_V2/Code/nebulae/nebulae.py", m)       # update.sh checks Code/nebulae/ is non-empty
        self.assertTrue(all(n == "QB_Nebulae_V2" or n.startswith("QB_Nebulae_V2/") for n in m))
        cfg = m["QB_Nebulae_V2/Code/config.txt"][2].decode()
        self.assertIn("VERSION=v2_1_2_uf1\n", cfg)
        self.assertEqual(m["QB_Nebulae_V2/Code/scripts/update.sh"][1], 0o755)
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
        r = subprocess.run(["C:/Program Files/Git/usr/bin/tar.exe", "-tvzf", "/c" + out.replace("\\", "/")[2:]],
                           capture_output=True, text=True)
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

    def tearDown(self):
        import shutil
        fwbuild.FW = self.saved
        shutil.rmtree(self.tmp)

    def device_zip(self, extra):
        files = dict(self.base)
        files.update(extra)
        meta, default = fwbuild.archive_meta(STOCK)
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
        self.assertEqual(len(changed) + len(added), 11)
        self.assertEqual(fwbuild.read_source()["provisional"], "no")

    def test_conflict_stops(self):
        p = self.device_zip({"Code/nebulae/ui.py": self.base["Code/nebulae/ui.py"] + b"# pi4 tweak\n"})
        before = fwbuild.tree(os.path.join(fwbuild.FW, "src"))
        with self.assertRaises(SystemExit):
            fwbuild.import_device(p)
        self.assertEqual(fwbuild.tree(os.path.join(fwbuild.FW, "src")), before)   # nothing written


if __name__ == "__main__":
    unittest.main(verbosity=2)
