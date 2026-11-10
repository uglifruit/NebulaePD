"""uf1 firmware logic tests (desktop Python 3).  Run:  python firmware/tests/test_firmware.py

Covers the new uf1 modules directly and the changed stock modules through py2shim (print statements rewritten,
hardware stubbed). It cannot prove Python 2 compatibility: compile every changed file with python2 as well.
"""
import inspect
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import py2shim  # noqa: E402

py2shim.install_hardware_stubs()
import instrpager  # noqa: E402
import nebopts  # noqa: E402
import ufmigrate  # noqa: E402
import pdsender  # noqa: E402
import scsender  # noqa: E402
import scengine  # noqa: E402
import bootguard  # noqa: E402

CHANGED = ["check_calibration", "control", "controlhandler", "filehandler", "fileloader", "nebulae", "pdsender", "ui",
           "instrpager", "nebopts", "ufmigrate", "scsender", "scengine", "bootguard"]


class TestSyntax(unittest.TestCase):
    def test_changed_files_compile(self):
        for name in CHANGED:
            py2shim.compile_check(os.path.join(py2shim.SRC, name + ".py"))

    def test_no_py3_only_syntax(self):
        # things Python 2.7 would reject, in the files uf1/uf2 touched. f-strings are found by the tokenizer (a regex
        # can't tell f"x" from b",f" or ">f"); the rest by pattern, outside comments
        import re
        import tokenize
        bad = re.compile(r'\bnonlocal\b|print\([^)]*\bend=|\basync\b|\bawait\b|:=')
        for name in CHANGED:
            path = os.path.join(py2shim.SRC, name + ".py")
            with open(path) as f:
                for i, line in enumerate(f, 1):
                    self.assertIsNone(bad.search(line.split("#")[0]), "%s.py:%d %s" % (name, i, line.strip()))
            with open(path) as f:
                for tok in tokenize.generate_tokens(f.readline):
                    kind = tokenize.tok_name[tok.type]
                    prefix = re.match(r"[A-Za-z]*", tok.string).group(0).lower() if kind == "STRING" else ""
                    self.assertFalse(kind == "FSTRING_START" or "f" in prefix,
                                     "%s.py:%d f-string %s" % (name, tok.start[0], tok.string[:20]))


class TestPager(unittest.TestCase):
    def test_pages_clamp(self):
        for n, pages in [(0, 1), (3, 1), (5, 1), (7, 2), (25, 5), (30, 5)]:
            p = instrpager.InstrPager(n)
            self.assertEqual(p.numPages(), pages, n)
            p.turn(10)
            self.assertEqual(p.page, pages - 1, n)              # clamped at the last page, no wrap
            p.turn(-10)
            self.assertEqual(p.page, 0, n)

    def test_cap_25(self):
        p = instrpager.InstrPager(30)
        p.showIndex(27)
        self.assertEqual(p.page, 0)                             # beyond the cap: page 1
        p.showIndex(24)
        self.assertEqual((p.page, p.slotIndex(4)), (4, 24))

    def test_slots_on_a_short_page(self):
        p = instrpager.InstrPager(7)
        p.turn(1)                                               # page 2 holds files 6 and 7
        self.assertEqual([p.slotIndex(i) for i in range(5)], [5, 6, None, None, None])
        self.assertIsNone(p.slotIndex(5))
        self.assertIsNone(p.slotIndex(-1))
        self.assertEqual(p.leds(), [0.3, 0.3, 0.0, 0.0, 0.0])   # lit = available
        self.assertEqual(p.leds(6), [0.3, 1.0, 0.0, 0.0, 0.0])  # the running one is bright

    def test_show_index_ge_5(self):
        p = instrpager.InstrPager(12)
        p.showIndex(7)
        self.assertEqual((p.page, p.offset()), (1, 5))
        self.assertEqual(p.leds(7), [0.3, 0.3, 1.0, 0.3, 0.3])
        self.assertEqual(p.leds(2), [0.3] * 5)                  # running one on another page

    def test_empty(self):
        p = instrpager.InstrPager(0)
        p.turn(3)
        self.assertIsNone(p.slotIndex(0))
        self.assertEqual(p.leds(), [0.0] * 5)


class TestOptions(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.path = os.path.join(self.d, "opts.txt")

    def tearDown(self):
        shutil.rmtree(self.d)

    def write(self, text):
        with open(self.path, "w") as f:
            f.write(text)

    def test_default_without_file(self):
        self.assertEqual(nebopts.get("pitch_coeff", self.path), 0.95)

    def test_value_comment_clamp_garbage(self):
        self.write("# tuning\npitch_coeff = 0.5  # half\n")
        self.assertEqual(nebopts.get("pitch_coeff", self.path), 0.5)
        self.write("PITCH_COEFF=7\n")
        self.assertEqual(nebopts.get("pitch_coeff", self.path), 1.0)
        self.write("pitch_coeff=0\n")
        self.assertEqual(nebopts.get("pitch_coeff", self.path), 0.05)
        self.write("pitch_coeff=fast\nnonsense line\n")
        self.assertEqual(nebopts.get("pitch_coeff", self.path), 0.95)
        self.write("pitch_coeff=nan\n")
        self.assertEqual(nebopts.get("pitch_coeff", self.path), 0.95)

    def test_copy_from_usb(self):
        usb = os.path.join(self.d, "usb")
        os.mkdir(usb)
        self.assertFalse(nebopts.copy_from_usb(usb, self.path))
        with open(os.path.join(usb, "neb_options.txt"), "w") as f:
            f.write("pitch_coeff=0.6\n")
        self.assertTrue(nebopts.copy_from_usb(usb, self.path))
        self.assertEqual(nebopts.get("pitch_coeff", self.path), 0.6)
        os.remove(os.path.join(usb, "neb_options.txt"))
        self.assertFalse(nebopts.copy_from_usb(usb, self.path))   # stick without the file keeps the last copy
        self.assertEqual(nebopts.get("pitch_coeff", self.path), 0.6)


CAL_GOOD = "start,0.01,\nsize,0.0,\ndensity,-0.002,\noverlap,0.0,\nblend,0.0,\nwindow,0.0,\nspeed,0.003,\npitch,0.027,\n"


class TestMigrate(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.code = os.path.join(self.d, "new") + "/"
        self.old = os.path.join(self.d, "old") + "/"
        for root in (self.code, self.old):
            os.makedirs(root + "config")
            os.makedirs(root + "misc")

    def tearDown(self):
        shutil.rmtree(self.d)

    def put(self, root, rel, text, mtime=None):
        with open(root + rel, "w") as f:
            f.write(text)
        if mtime is not None:
            os.utime(root + rel, (mtime, mtime))

    def read(self, root, rel):
        with open(root + rel) as f:
            return f.read()

    def test_restores_after_update(self):
        self.put(self.old, ufmigrate.CAL, CAL_GOOD)
        self.put(self.old, "config/bootinstr.txt", "bank,puredata\ninstr,07_shimmer\n")
        self.put(self.old, "config/nebsettings.txt", "x")
        self.put(self.code, ufmigrate.CAL, CAL_GOOD.replace("0.027", "0.3"))           # update.sh's forced one
        log = ufmigrate.migrate(self.code, self.old)
        self.assertEqual(self.read(self.code, ufmigrate.CAL), CAL_GOOD)
        self.assertIn("07_shimmer", self.read(self.code, "config/bootinstr.txt"))
        self.assertTrue(os.path.exists(self.code + ufmigrate.MARKER), log)
        # second start: marker present -> untouched
        self.put(self.code, ufmigrate.CAL, "changed")
        self.assertEqual(ufmigrate.migrate(self.code, self.old), [])
        self.assertEqual(self.read(self.code, ufmigrate.CAL), "changed")

    def test_frozen_clock(self):
        """The unit's clock restarts at the same moment every boot, so the forced calibration from the install boot
        can carry a time later than this boot's start. It must still be replaced."""
        now = time.time()
        self.put(self.old, ufmigrate.CAL, CAL_GOOD, mtime=now - 3600)
        self.put(self.code, ufmigrate.CAL, "forced at install", mtime=now + 30)
        ufmigrate.migrate(self.code, self.old)
        self.assertEqual(self.read(self.code, ufmigrate.CAL), CAL_GOOD)

    def test_settings_kept_if_present(self):
        self.put(self.old, ufmigrate.CAL, CAL_GOOD)
        self.put(self.old, "config/nebsettings.txt", "old")
        self.put(self.code, "config/nebsettings.txt", "new")
        ufmigrate.migrate(self.code, self.old)
        self.assertEqual(self.read(self.code, "config/nebsettings.txt"), "new")

    def test_unit_calibration_is_valid(self):
        """The calibration file from the unit's own backup (firmware/device) passes the restore check."""
        import tarfile
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "device", "neb_update.zip")
        if not os.path.isfile(p):
            self.skipTest("no firmware/device backup")
        with tarfile.open(p) as t:
            data = t.extractfile("QB_Nebulae_V2/Code/" + ufmigrate.CAL).read().decode("ascii")
        self.put(self.code, "unit_cal.txt", data)
        self.assertTrue(ufmigrate.valid_calibration(self.code + "unit_cal.txt"))

    def test_invalid_or_missing_old(self):
        self.put(self.old, ufmigrate.CAL, "start,abc,\n")
        self.put(self.code, ufmigrate.CAL, "new")
        ufmigrate.migrate(self.code, self.old)
        self.assertEqual(self.read(self.code, ufmigrate.CAL), "new")
        shutil.rmtree(self.old)
        os.remove(self.code + ufmigrate.MARKER)
        self.assertIn("no previous tree", ufmigrate.migrate(self.code, self.old)[0])
        self.assertFalse(ufmigrate.valid_calibration(self.d + "/nope.txt"))
        self.put(self.code, "x.txt", CAL_GOOD.replace("pitch,0.027", "pitch,9"))
        self.assertFalse(ufmigrate.valid_calibration(self.code + "x.txt"))

    def test_never_raises(self):
        self.assertTrue(ufmigrate.migrate(self.d + "/missing/", self.old)[-1].startswith("migration error"))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestPdSender(unittest.TestCase):
    def test_batch_bytes_equal_stock_stream(self):
        msgs = ["start 0.5", "pitch 0.6", "reset 0"]
        self.assertEqual(pdsender.PdSend.batch(None, msgs), b"start 0.5;pitch 0.6;reset 0;")

    def test_late_listener_and_reconnect(self):
        port = free_port()
        pdsender.PdSend.sport = port
        try:
            s = pdsender.PdSend()
            self.assertFalse(s.is_connected())
            self.assertFalse(s.retry())                 # rate-limited: too soon after the first attempt
            got = []
            srv = socket.socket()
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", port))
            srv.listen(1)

            def accept():
                c, _ = srv.accept()
                c.settimeout(2)
                data = b""
                while not data.endswith(b"b 2;"):
                    chunk = c.recv(100)
                    if not chunk:                        # peer closed: stop instead of spinning
                        break
                    data += chunk
                got.append(data)
                c.close()
            t = threading.Thread(target=accept)
            t.daemon = True                              # a failure must not hang the test run
            t.start()
            time.sleep(0.3)
            self.assertTrue(s.retry())
            s.send(["a 1", "b 2"])
            t.join(3)
            self.assertEqual(got, [b"a 1;b 2;"])
            srv.close()
            time.sleep(0.1)
            for _ in range(5):                           # peer gone: send fails and drops the connection
                s.send(["c 3"])
                if not s.is_connected():
                    break
                time.sleep(0.1)
            self.assertFalse(s.is_connected())
            s.close()
        finally:
            pdsender.PdSend.sport = 3000


class TestFileHandler(unittest.TestCase):
    def test_hide_exact_list(self):
        fh_mod = py2shim.load("filehandler")
        d = tempfile.mkdtemp() + "/"
        try:
            for n in ["b_two.pd", "a_one.pd", "_helper.pd", "x~.pd_linux", "y~.l_arm", "readme.md", "01_drone.pd"]:
                open(d + n, "w").close()
            fh = fh_mod.FileHandler(d, [".pd"], hide_prefix="_")
            self.assertEqual(fh.getFileNames(), ["01_drone", "a_one", "b_two"])
            self.assertEqual(fh.getIndex("drone"), None)          # stock: substring match hit 01_drone
            self.assertEqual(fh.getIndex("01_drone"), 0)
            stock = py2shim.load("filehandler", src=py2shim.BASE, register=False).FileHandler(d, ".pd")
            self.assertIn("readme", stock.getFileNames())            # the string-extension quirk uf1 removes
            self.assertEqual(stock.getIndex("drone"), 0)
        finally:
            shutil.rmtree(d)


class FakeADC(object):
    code = 2048

    def read_adc(self, ch):
        return FakeADC.code


class TestPitchFilter(unittest.TestCase):
    def response(self, src, coeff_file=None):
        sys.modules["MCP3208"].MCP3208 = lambda **k: FakeADC()
        py2shim.stub("digitaldata")
        ctl = py2shim.load("control", src=src, register=False)
        h = ctl.HybridData(4, "pitch", 0.0, 1.0, 0.6)
        h.offset = 0.0
        h.staticVal = 0.0

        def code_for(v):      # ADC code that reads as pitch v (inverse of HybridData's scaling)
            return int(round((1.0 - (v / h.scaling - h.minimum) / h.range) * 4095))
        FakeADC.code = code_for(0.2)
        for _ in range(300):
            h.getValue()
        settled = h.getValue()
        FakeADC.code = code_for(0.8)
        out = [h.getValue() for _ in range(100)]
        final = out[-1]
        jump = final - settled
        polls99 = next(i + 1 for i, v in enumerate(out) if abs(final - v) <= 0.01 * abs(jump))
        # steady input with +-1 LSB noise: output must not move
        base = FakeADC.code
        changes, prev = 0, h.getValue()
        for i in range(500):
            FakeADC.code = base + (1 if i % 2 else -1)
            v = h.getValue()
            changes += v != prev
            prev = v
        return settled, final, polls99, changes

    def test_stock_vs_uf1(self):
        s0, f0, p_stock, n_stock = self.response(py2shim.BASE)
        s1, f1, p_uf1, n_uf1 = self.response(py2shim.SRC)
        print("\n  pitch jump %.3f -> %.3f: polls to 99%%: stock %d, uf1 %d; output changes under +-1 LSB noise: "
              "stock %d, uf1 %d" % (s1, f1, p_stock, p_uf1, n_stock, n_uf1))
        self.assertAlmostEqual(f0, f1, places=3)
        self.assertGreaterEqual(p_stock, 10)
        self.assertLessEqual(p_uf1, 3)
        self.assertEqual(n_uf1, 0)


class TestSelector(unittest.TestCase):
    """Real controlhandler.py + ui.py (stubbed hardware): Speed = bank, Pitch = page, a button loads its slot."""

    def setUp(self):
        self.root = tempfile.mkdtemp().replace("\\", "/")
        self.dirs = {"/home/alarm/pd/": self.root + "/pd/", "/home/alarm/instr/": self.root + "/instr/",
                     "/home/alarm/QB_Nebulae_V2/Code/instr/": self.root + "/factory/"}
        for d in self.dirs.values():
            os.makedirs(d)
        self.pd = ["%02d_p" % i for i in range(1, 13)]           # 12 patches: pages 1-5, 6-10, 11-12
        for n in self.pd + ["_helper"]:
            open(self.dirs["/home/alarm/pd/"] + n + ".pd", "w").close()
        open(self.dirs["/home/alarm/pd/"] + "x~.pd_linux", "w").close()
        for n in ["a_granularlooper", "b_oneshot", "c_synth", "d_effects", "e_testio"]:
            open(self.dirs["/home/alarm/QB_Nebulae_V2/Code/instr/"] + n + ".instr", "w").close()
        fh_mod = py2shim.load("filehandler")
        real = fh_mod.FileHandler
        dirs = self.dirs
        fh_mod.FileHandler = lambda d, ext, **kw: real(dirs.get(d, d), ext, **kw)
        pdsender.PdSend.sport = 1                                # nothing listens there
        ch_mod = py2shim.load("controlhandler")
        ui_mod = py2shim.load("ui")
        py2shim.FakeControlChannel.script = {}
        self.ch = ch_mod.ControlHandler(None, 0, None, instr="07_p", bank="puredata")
        self.ui = ui_mod.UserInterface(self.ch)
        self.ch.setInstrSelBank("puredata")                      # as nebulae.loadUI does
        self.ui.setCurrentInstr("07_p")

    def tearDown(self):
        pdsender.PdSend.sport = 3000
        shutil.rmtree(self.root)

    def tick(self, n=1):
        for _ in range(n):
            self.ch.updateAll()
            self.ui.update()

    def press(self, name, polls=3):
        py2shim.FakeControlChannel.script[name] = [1] * polls + [0]
        self.tick(polls + 2)

    def leds(self):
        b = py2shim.FakeLedDriver.last.buttons
        return [b[k] for k in ["record", "next", "source", "reset", "freeze"]]

    def pitch_colour(self):
        return py2shim.FakeLedDriver.last.rgb["pitch_pos"][:3]

    def test_boot_index_ge_5(self):
        self.assertEqual((self.ch.getInstrSelIdx(), self.ch.getInstrSelOffset()), (6, 5))

    def pitch_steps(self, n):
        py2shim.FakeEncoderWorker.steps[(17, 27)] = n
        self.tick(2)                                                 # LEDs are drawn before the encoders are read

    def test_pitch_pages_button_loads(self):
        self.ch.enterInstrSelMode()
        self.tick()
        self.assertEqual(self.leds(), [0.3, 1.0, 0.3, 0.3, 0.3])     # page 2 (6-10); 07 is running = bright
        self.assertEqual(self.pitch_colour(), (4095, 1100, 0))       # orange = page 2
        self.pitch_steps(4)                                          # one detent = one page
        self.assertEqual(self.ui.pager.page, 2)
        self.assertEqual(self.leds(), [0.3, 0.3, 0.0, 0.0, 0.0])     # 11, 12 available, 3 slots empty
        self.assertEqual(self.pitch_colour(), (4095, 3395, 0))       # yellow = page 3
        self.press("source_instr")                                   # empty slot: nothing happens
        self.assertFalse(self.ui.getReloadRequest())
        self.pitch_steps(8)
        self.assertEqual(self.ui.pager.page, 2)                      # clamped at the last page
        self.pitch_steps(-3)
        self.assertEqual(self.ui.pager.page, 2)                      # less than a detent: no change
        self.pitch_steps(-1)
        self.assertEqual(self.ui.pager.page, 1)
        self.pitch_steps(-8)
        self.assertEqual(self.ui.pager.page, 0)
        self.assertEqual(self.pitch_colour(), (4095, 4095, 4095))    # white = page 1
        self.assertFalse(self.ui.getReloadRequest())
        self.press("freeze_instr")                                   # 5th button on page 1 = 05
        self.assertTrue(self.ui.getReloadRequest())
        self.assertEqual(self.ui.getNewInstr(), "05_p")
        self.assertEqual(self.ch.getInstrSelBank(), "puredata")

    def test_each_button_is_its_slot(self):
        for slot, name in enumerate(["record_instr", "file_instr", "source_instr", "reset_instr", "freeze_instr"]):
            self.setUp()
            self.ch.enterInstrSelMode()
            self.tick()
            self.press(name)
            self.assertTrue(self.ui.getReloadRequest(), name)
            self.assertEqual(self.ui.getNewInstr(), self.pd[5 + slot], name)   # page 2 = files 6-10
            self.tearDown()
        self.setUp()

    def test_clicks_leave_without_loading(self):
        for pin in (26, 22):                                         # Speed click, then Pitch click
            self.ch.enterInstrSelMode()
            self.tick()
            self.assertEqual(self.ch.mode(), "instr selector")
            py2shim.FakeSwitch.held[pin] = True
            self.tick()
            py2shim.FakeSwitch.held[pin] = False
            self.tick()                                              # the release closes the selector (no more
                                                                     # ticks: stock normal mode uses py2's has_key)
            self.assertEqual(self.ch.mode(), "puredata", pin)
            self.assertFalse(self.ui.getReloadRequest(), pin)

    def test_bank_switch_and_hidden(self):
        self.ch.enterInstrSelMode()
        self.tick()
        self.assertEqual(self.ui.puredata_fhandle.getFileNames(), self.pd)   # _helper hidden, externals not listed
        py2shim.FakeEncoderWorker.steps[(6, 13)] = -8                # Speed CCW: puredata -> factory
        self.tick(2)
        self.assertEqual(self.ch.getInstrSelBank(), "factory")
        self.assertEqual(self.leds(), [0.3] * 5)                     # 5 factory instruments, none running
        self.assertEqual(self.pitch_colour(), (4095, 4095, 4095))    # page 1
        py2shim.FakeEncoderWorker.steps[(6, 13)] = -8                # factory -> user (empty)
        self.tick(2)
        self.assertEqual(self.ch.getInstrSelBank(), "user")
        self.assertEqual(self.leds(), [0.0] * 5)
        self.press("record_instr")
        self.assertFalse(self.ui.getReloadRequest())                 # nothing to load in an empty bank
        py2shim.FakeEncoderWorker.steps[(6, 13)] = 16                # back CW past factory to puredata
        self.tick(2)
        py2shim.FakeEncoderWorker.steps[(6, 13)] = 8
        self.tick(2)
        self.assertEqual(self.ch.getInstrSelBank(), "puredata")
        self.assertEqual(self.ui.pager.page, 1)                      # back on the running patch's page

    def test_new_files_appear_on_open(self):
        open(self.dirs["/home/alarm/pd/"] + "13_new.pd", "w").close()
        self.ch.enterInstrSelMode()
        self.tick()
        self.assertEqual(self.ui.pager.count, 13)


class FakePdSock(object):
    def __init__(self):
        self.connected, self.sent, self.retries = True, [], 0

    def is_connected(self): return self.connected

    def retry(self):
        self.retries += 1
        self.connected = True
        return True

    def send(self, msgs): self.sent.append(list(msgs))

    def connect(self): self.connected = True

    def close(self): self.connected = False


class TestPdMode(unittest.TestCase):
    """controlhandler's Pd stream: stock messages every pass; alts once per connection only when enabled."""

    def make(self, alts_option):
        pdsender.PdSend.sport = 1
        real_get = nebopts.get
        nebopts.get = lambda key, *a: (1.0 if alts_option else 0.0) if key == "pd_alts_at_load" else real_get(key, *a)
        try:
            ch_mod = py2shim.load("controlhandler")
            py2shim.FakeControlChannel.script = {}
            ch = ch_mod.ControlHandler(None, 0, None, instr="x", bank="puredata")
        finally:
            nebopts.get = real_get
            pdsender.PdSend.sport = 3000
        ch.pdSock = FakePdSock()
        ch.enterPureDataMode()
        return ch

    def names(self, batch):
        return [m.split()[0] for m in batch]

    def test_default_is_stock_stream(self):
        ch = self.make(False)
        for _ in range(3):
            ch.updateAll()
        primary = [c.name for c in ch.channels]
        self.assertEqual([self.names(b) for b in ch.pdSock.sent], [primary] * 3)

    def test_restore_alt_to_default(self):
        ch = self.make(False)
        for chn in ch.altchannels:
            chn.setValue(0.77)
        ch.restoreAltToDefault()
        got = dict((c.name, c.getValue()) for c in ch.altchannels)
        self.assertEqual(got["speed_alt"], 23)                       # input gain back to 0 dB
        self.assertEqual(set(v for k, v in got.items() if k != "speed_alt"), {0})

    def test_alts_once_per_connection(self):
        ch = self.make(True)
        for _ in range(3):
            ch.updateAll()
        alts = [c.name for c in ch.altchannels]
        primary = [c.name for c in ch.channels]
        self.assertEqual([self.names(b) for b in ch.pdSock.sent], [alts + primary, primary, primary])
        ch.pdSock.connected = False                       # connection lost -> retried -> alts again
        ch.updateAll()
        self.assertEqual(ch.pdSock.retries, 1)
        self.assertEqual(self.names(ch.pdSock.sent[-1]), alts + primary)


class FakeLogger(object):
    usb_status = False

    def spill_basic_info(self): pass

    def mount_usb(self): pass

    def unmount_usb(self): pass


class TestFlatLoop(unittest.TestCase):
    """nebulae.py's main loop over many instrument switches: constant stack depth, Pd waited for."""

    def test_switches(self):
        state = {"switches": 0, "depths": [], "pd_alive": 0, "max_switches": 400}

        class HasKeyDict(dict):
            def has_key(self, k): return k in self

        class Csound(object):
            def setOption(self, o): pass
            def compileOrc(self, o): return 0
            def readScore(self, s): pass
            def start(self): pass
            def cleanup(self): pass
            def reset(self): pass
            def csound(self): return None

        class PerfThread(object):
            def __init__(self, c): self.stopped = False
            def play(self): pass
            def stop(self): self.stopped = True
            def join(self): pass
            def status(self):
                return 1 if self.stopped or state["switches"] >= state["max_switches"] else 0

        class CH(object):
            def __init__(self, *a, **k):
                state["depths"].append(len(inspect.stack()))
                self.instr_sel_idx, self.bank = 0, "factory"
                self.pd, self.restores = k.get("bank") == "puredata", 0
                state.setdefault("handlers", []).append(self)
            def setCsoundPerformanceThread(self, p): pass
            def enterPureDataMode(self): pass
            def updateAll(self): pass
            def restoreAltToDefault(self): self.restores += 1
            def printAllControls(self): pass
            def getInstrSelBank(self): return self.bank
            def setInstrSelBank(self, b): self.bank = b

        class UI(object):
            def __init__(self, ch):
                self.controlhandler, self.reload_flag, self.calls = ch, False, 0
            def update(self):
                self.calls += 1
                if self.calls % 2 == 0 and state["switches"] < state["max_switches"]:
                    state["switches"] += 1
                    self.reload_flag = True
                    self.controlhandler.bank = "puredata" if state["switches"] % 2 else "factory"
            def getReloadRequest(self): return self.reload_flag
            def getNewInstr(self): return "x%d" % state["switches"]
            def clearAllLEDs(self): pass
            def setCurrentInstr(self, i): pass

        class Popen(object):
            def __init__(self, cmd, **k):
                state["pd_alive"] += 1
                self.rc = None
            def poll(self): return self.rc
            def terminate(self):
                self.rc = 0
                state["pd_alive"] -= 1
            def kill(self): pass
            def wait(self): return self.rc

        py2shim.stub("ctcsound", Csound=Csound, CsoundPerformanceThread=PerfThread)
        py2shim.stub("controlhandler", ControlHandler=CH)
        py2shim.stub("conductor", Conductor=lambda: type("C", (), {
            "generate_orc": lambda s, i, b: None, "getConfigDict": lambda s: HasKeyDict(), "numFiles": lambda s: 0,
            "refreshFileHandler": lambda s: None, "curOrc": "", "curSco": ""})())
        py2shim.stub("ui", UserInterface=UI)
        py2shim.stub("fileloader", FileLoader=lambda: type("F", (), {"reload": lambda s: None})())
        py2shim.stub("logger", NebLogger=FakeLogger)
        py2shim.stub("neb_globals", remount_fs=False)
        py2shim.stub("ufmigrate", migrate=lambda: ["ok"])
        py2shim.stub("bootguard", on_app_start=lambda: False, mark_healthy=lambda: True, LIMIT=2, HEALTHY_S=20.0)
        real_popen, real_system, real_sleep = subprocess.Popen, os.system, time.sleep
        subprocess.Popen, os.system, time.sleep = Popen, (lambda c: 0), (lambda s: None)
        try:
            with self.assertRaises(SystemExit):
                py2shim.load("nebulae", register=False)
        finally:
            subprocess.Popen, os.system, time.sleep = real_popen, real_system, real_sleep
        d = state["depths"]
        print("\n  %d switches, stack depth at each start: min %d max %d" % (state["switches"], min(d), max(d)))
        self.assertEqual(state["switches"], state["max_switches"])
        self.assertEqual(len(d), state["max_switches"] + 2)     # + the safe instrument after Csound stopped
        self.assertEqual(min(d), max(d))
        self.assertEqual(state["pd_alive"], 0)
        pd = [h for h in state["handlers"] if h.pd]
        self.assertEqual(len(pd), state["max_switches"] // 2)
        self.assertTrue(all(h.restores == 1 for h in pd))           # every Pd load starts with alts at defaults


class TestScSender(unittest.TestCase):
    def test_osc_bytes(self):
        m = scsender.osc_message("/neb/pitch", 0.6)
        self.assertEqual(m[:12], b"/neb/pitch\0\0")
        self.assertEqual(m[12:16], b",f\0\0")
        self.assertEqual(len(m), 20)
        import struct
        self.assertAlmostEqual(struct.unpack(">f", m[16:])[0], 0.6, places=6)
        b = scsender.osc_bundle([m, m])
        self.assertEqual(b[:8], b"#bundle\0")
        self.assertEqual(struct.unpack(">Q", b[8:16])[0], 1)
        self.assertEqual(struct.unpack(">i", b[16:20])[0], 20)
        self.assertEqual(len(b), 16 + 2 * 24)
        self.assertEqual(len(scsender.osc_message("/neb/abcdefg", 1)) % 4, 0)    # 12 chars + NUL padding

    def test_change_and_resend(self):
        s = scsender.ScSend()
        try:
            msgs = ["pitch 0.6", "reset 0", "size 0.5"]
            self.assertEqual([n for n, v in s.select(msgs, 0)], ["pitch", "reset", "size"])   # first pass: all
            self.assertEqual(s.select(msgs, 100), [])                                     # nothing changed
            self.assertEqual(s.select(["pitch 0.7", "reset 0", "size 0.5"], 200), [("pitch", 0.7)])
            self.assertEqual([n for n, v in s.select(["pitch 0.7", "reset 0", "size 0.5"], 1100)],
                             ["pitch", "size"])                       # once a second all again, but not the trigger
            self.assertEqual(s.select(["pitch 0.7", "reset 1", "size 0.5"], 1200), [("reset", 1.0)])
            self.assertEqual(s.select(["garbage", "x y z", "pitch nan?"], 1300), [])
        finally:
            s.close()

    def test_udp_delivery(self):
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.bind(("127.0.0.1", 0))
        rx.settimeout(2)
        s = scsender.ScSend()
        s.sport = rx.getsockname()[1]
        try:
            s.send(["pitch 0.6", "freeze 1"])
            data = rx.recv(2048)
            self.assertTrue(data.startswith(b"#bundle\0"))
            self.assertIn(b"/neb/pitch\0", data)
            self.assertIn(b"/neb/freeze\0", data)
            s.close()
            s.send(["pitch 0.1"])                   # closed: nothing, no error
        finally:
            rx.close()


class TestBootGuard(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = os.path.join(self.d, "boot_guard.txt")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_two_failed_starts_then_safe(self):
        self.assertFalse(bootguard.on_app_start(self.p))     # 1st start
        self.assertFalse(bootguard.on_app_start(self.p))     # crash -> 2nd start
        self.assertTrue(bootguard.on_app_start(self.p))      # crash again -> safe instrument
        self.assertFalse(bootguard.on_app_start(self.p))     # the safe start counts as 1
        bootguard.mark_healthy(self.p)
        self.assertFalse(bootguard.on_app_start(self.p))
        self.assertFalse(bootguard.on_app_start(self.p))

    def test_healthy_run_resets(self):
        for _ in range(10):
            self.assertFalse(bootguard.on_app_start(self.p))
            bootguard.mark_healthy(self.p)

    def test_garbage_and_unwritable(self):
        with open(self.p, "w") as f:
            f.write("nonsense")
        self.assertFalse(bootguard.on_app_start(self.p))
        self.assertFalse(bootguard.on_app_start(os.path.join(self.d, "no", "dir", "x.txt")))   # never raises


class FakeProc(object):
    def __init__(self, rc=None):
        self.rc, self.terminated = rc, False

    def poll(self): return self.rc

    def terminate(self):
        self.terminated = True
        self.rc = 0

    def kill(self): self.rc = -9

    def wait(self): return self.rc


class TestScEngine(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp().replace("\\", "/") + "/"
        self.rt = self.d + "rt/"
        for rel in ("bin/sclang", "bin/scsynth", "lib/libscsynth.so.1"):
            os.makedirs(os.path.dirname(self.rt + rel), exist_ok=True)
            open(self.rt + rel, "w").close()
        os.makedirs(self.rt + "share/SCClassLibrary")
        self.patch = self.d + "p.scd"
        open(self.patch, "w").close()
        self.now = [0.0]
        self.procs = []

    def tearDown(self):
        shutil.rmtree(self.d)

    def engine(self, jackd_rc=None, sclang_rc=None):
        def popen(cmd, **k):
            p = FakeProc(jackd_rc if cmd[0] == "jackd" else sclang_rc)
            p.cmd, p.kw = cmd, k
            self.procs.append(p)
            return p

        def sleep(t):
            self.now[0] += t
        return scengine.ScEngine(self.patch, 256, 2, runtime=self.rt, work=self.d + "w/", popen=popen,
                                 clock=lambda: self.now[0], sleep=sleep)

    def test_commands_env_files(self):
        e = self.engine()
        self.assertEqual(e.start(), "starting")
        jack, sclang = self.procs
        self.assertEqual(jack.cmd, ["jackd", "-R", "-P75", "-dalsa", "-dhw:0", "-p256", "-n2", "-s", "-r48000"])
        self.assertEqual(jack.kw["env"]["JACK_NO_AUDIO_RESERVATION"], "1")
        self.assertEqual(sclang.cmd, ["sclang", "-D", "-l", self.d + "w/sclang_conf.yaml", self.patch])
        env = sclang.kw["env"]
        self.assertEqual(env["LD_LIBRARY_PATH"], self.rt + "lib")
        self.assertTrue(env["PATH"].startswith(self.rt + "bin:"))
        self.assertEqual(env["SC_JACK_DEFAULT_OUTPUTS"], "system:playback_1,system:playback_2")
        with open(self.d + "w/home/.config/SuperCollider/startup.scd") as f:
            startup = f.read()
        self.assertIn('ugenPluginsPath = "%splugins"' % self.rt, startup)
        self.assertIn("openUDPPort(3000)", startup)
        self.assertIn('File.use("%sw/ready"' % self.d, startup)
        with open(self.d + "w/sclang_conf.yaml") as f:
            self.assertIn("- %sshare/SCClassLibrary" % self.rt, f.read())

    def test_ready_then_crash_and_stop(self):
        e = self.engine()
        e.start()
        self.assertEqual(e.poll(), "starting")
        open(self.d + "w/ready", "w").close()        # the startup file's ServerBoot action
        self.now[0] += 1
        self.assertEqual(e.poll(), "ready")
        self.procs[1].rc = 1                          # sclang dies: the patch stopped
        self.assertEqual(e.poll(), "failed")
        self.assertIn("sclang exited", e.reason)
        real = os.system
        os.system = lambda c: 0
        try:
            e.stop()
        finally:
            os.system = real
        self.assertTrue(self.procs[0].terminated)     # jackd stopped too

    def test_ready_from_log_and_timeout(self):
        e = self.engine()
        e.start()
        with open(self.d + "w/sclang.log", "w") as f:
            f.write("blah\nSuperCollider 3 server ready.\n")
        self.now[0] += 1
        self.assertEqual(e.poll(), "ready")
        e2 = self.engine()
        e2.start()
        os.remove(self.d + "w/sclang.log")
        self.now[0] += scengine.START_TIMEOUT + 1
        self.assertEqual(e2.poll(), "failed")
        self.assertIn("did not start the server", e2.reason)

    def test_start_failures(self):
        self.assertEqual(self.engine(jackd_rc=1).start(), "failed")            # jackd can't open the device
        shutil.rmtree(self.rt + "bin")
        e = self.engine()
        self.assertEqual(e.start(), "failed")
        self.assertIn("runtime missing", e.reason)

    def test_install_from_usb(self):
        import tarfile
        src = self.d + "bundle/"
        for rel in ("bin/sclang", "bin/scsynth", "lib/libscsynth.so.1", "share/SCClassLibrary/Object.sc"):
            os.makedirs(os.path.dirname(src + rel), exist_ok=True)
            with open(src + rel, "w") as f:
                f.write(rel)
        tgz = self.d + "sc_runtime.tgz"
        with tarfile.open(tgz, "w:gz") as t:
            for name in ("bin", "lib", "share"):
                t.add(src + name, arcname=name)
        dest = self.d + "installed/"
        self.assertIsNone(scengine.install_from_usb(self.d + "nothing.tgz", dest))
        self.assertIn("installed", scengine.install_from_usb(tgz, dest))
        self.assertTrue(scengine.runtime_ok(dest))
        self.assertIn("up to date", scengine.install_from_usb(tgz, dest))
        with tarfile.open(self.d + "bad.tgz", "w:gz") as t:
            t.add(src + "bin", arcname="bin")
        self.assertIn("incomplete", scengine.install_from_usb(self.d + "bad.tgz", dest))
        self.assertTrue(scengine.runtime_ok(dest))      # the good install is kept


class TestFailover(unittest.TestCase):
    """nebulae.py's uf2 fallbacks, through the real main loop: every failure lands on factory/a_granularlooper."""

    def run_app(self, script, sc_behaviour=None, guard=False, compile_rc=0):
        """script: one entry per UI pass: None (idle), ("load", bank, instr), "csound_stop", "pd_die".
        When the script runs out, everything stops, so the app ends on the safe instrument."""
        state = {"script": list(script), "loads": [], "csound_stop": False, "pd_die": False, "sc_stops": 0,
                 "pd": []}
        sc_behaviour = sc_behaviour or {}

        class HasKeyDict(dict):
            def has_key(self, k): return k in self

        class Csound(object):
            def setOption(self, o): pass
            def compileOrc(self, o): return compile_rc if state.get("orc") == "broken" else 0
            def readScore(self, s): pass
            def start(self): pass
            def cleanup(self): pass
            def reset(self): pass
            def csound(self): return None

        class PerfThread(object):
            def __init__(self, c): self.stopped = False
            def play(self): pass
            def stop(self): self.stopped = True
            def join(self): pass
            def status(self):
                if state["csound_stop"]:
                    state["csound_stop"] = False
                    return 1
                return 1 if self.stopped or (not state["script"] and state["loads"][-1] == SAFE) else 0

        class CH(object):
            def __init__(self, *a, **k):
                self.bank, self.instr_sel_idx, self.next = k.get("bank"), 0, None
                state["loads"].append((k.get("bank"), a[3]))
            def setCsoundPerformanceThread(self, p): pass
            def enterPureDataMode(self): pass
            def updateAll(self): pass
            def restoreAltToDefault(self): pass
            def printAllControls(self): pass
            def getInstrSelBank(self): return self.next[0] if self.next else self.bank
            def setInstrSelBank(self, b): pass

        class UI(object):
            def __init__(self, ch):
                self.controlhandler, self.reload_flag = ch, False
            def update(self):
                if not state["script"]:
                    state["pd_die"] = True
                    return
                step = state["script"].pop(0)
                if step == "csound_stop":
                    state["csound_stop"] = True
                elif step == "pd_die":
                    state["pd_die"] = True
                elif step is not None:
                    self.controlhandler.next = step[1:]
                    self.reload_flag = True
            def getReloadRequest(self): return self.reload_flag
            def getNewInstr(self): return self.controlhandler.next[1]
            def clearAllLEDs(self): pass
            def setCurrentInstr(self, i): pass

        class Popen(object):
            def __init__(self, cmd, **k):
                self.rc = None
                state["pd"].append(self)
            def poll(self):
                if state["pd_die"] and self.rc is None:
                    state["pd_die"] = False
                    self.rc = 1
                return self.rc
            def terminate(self): self.rc = 0
            def kill(self): pass
            def wait(self): return self.rc

        class Engine(object):
            def __init__(self, patch, period, nperiods):
                self.name = os.path.basename(patch)[:-4]
                self.mode = sc_behaviour.get(self.name, "ok")
                self.reason, self.polls = "", 0
            def start(self):
                if self.mode == "fail_start":
                    self.reason = "runtime missing"
                    return "failed"
                return "starting"
            def poll(self):
                self.polls += 1
                if self.mode == "fail_start":
                    return "failed"
                if self.mode == "die" and self.polls > 2:
                    self.reason = "sclang exited"
                    return "failed"
                if not state["script"]:
                    self.reason = "end of test"
                    return "failed"
                return "ready"
            def stop(self): state["sc_stops"] += 1
            def report(self): return "report for " + self.name

        py2shim.stub("ctcsound", Csound=Csound, CsoundPerformanceThread=PerfThread)
        py2shim.stub("controlhandler", ControlHandler=CH)
        py2shim.stub("conductor", Conductor=lambda: type("C", (), {
            "generate_orc": lambda s, i, b: state.__setitem__("orc", i), "getConfigDict": lambda s: HasKeyDict(), "numFiles": lambda s: 0,
            "refreshFileHandler": lambda s: None, "curOrc": "", "curSco": ""})())
        py2shim.stub("ui", UserInterface=UI)
        py2shim.stub("fileloader", FileLoader=lambda: type("F", (), {"reload": lambda s: None})())
        py2shim.stub("logger", NebLogger=FakeLogger)
        py2shim.stub("neb_globals", remount_fs=False)
        py2shim.stub("ufmigrate", migrate=lambda: [])
        py2shim.stub("bootguard", on_app_start=lambda: guard, mark_healthy=lambda: True, LIMIT=2, HEALTHY_S=20.0)
        py2shim.stub("scengine", ScEngine=Engine, PATCH_DIR="/home/alarm/sc/")
        real = subprocess.Popen, os.system, time.sleep
        subprocess.Popen, os.system, time.sleep = Popen, (lambda c: 0), (lambda s: None)
        import contextlib
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                py2shim.load("nebulae", register=False)
        finally:
            subprocess.Popen, os.system, time.sleep = real
        state["notes"] = [l for l in out.getvalue().splitlines() if l.startswith("uf2:")]
        return state

    def test_pd_crash(self):
        st = self.run_app([("load", "puredata", "p1"), None, "pd_die", None])
        self.assertEqual(st["loads"], [SAFE, ("puredata", "p1"), SAFE])
        self.assertTrue(any("puredata/p1 failed (Pd exited" in n for n in st["notes"]), st["notes"])

    def test_sc_start_failure_and_crash(self):
        st = self.run_app([("load", "supercollider", "bad"), None, ("load", "supercollider", "dies"), None, None,
                           None], sc_behaviour={"bad": "fail_start", "dies": "die"})
        self.assertEqual(st["loads"], [SAFE, ("supercollider", "bad"), SAFE, ("supercollider", "dies"), SAFE])
        self.assertTrue(any("supercollider/bad failed (runtime missing)" in n for n in st["notes"]), st["notes"])
        self.assertTrue(any("supercollider/dies failed (sclang exited)" in n for n in st["notes"]), st["notes"])
        self.assertEqual(st["sc_stops"], 2)

    def test_sc_normal_switch(self):
        st = self.run_app([("load", "supercollider", "good"), None, None, ("load", "puredata", "p1"), None])
        self.assertEqual(st["loads"][:3], [SAFE, ("supercollider", "good"), ("puredata", "p1")])
        self.assertEqual(st["sc_stops"], 1)
        self.assertFalse(any("supercollider/good failed" in n for n in st["notes"]))

    def test_csound_compile_failure_and_stop(self):
        st = self.run_app([("load", "user", "broken"), None], compile_rc=-1)
        self.assertEqual(st["loads"][:2], [SAFE, SAFE])           # the broken one never got a ControlHandler
        self.assertTrue(any("user/broken failed (the Csound orchestra did not compile)" in n for n in st["notes"]))
        st = self.run_app([("load", "user", "stops"), "csound_stop", None])
        self.assertEqual(st["loads"][:3], [SAFE, ("user", "stops"), SAFE])
        self.assertTrue(any("user/stops failed (Csound stopped)" in n for n in st["notes"]), st["notes"])

    def test_boot_guard(self):
        st = self.run_app([None], guard=True)
        self.assertEqual(st["loads"][0], SAFE)
        self.assertTrue(any(n.startswith("uf2: boot guard") for n in st["notes"]), st["notes"])

    def test_safe_instrument_failing_stops(self):
        st = self.run_app([])          # the safe instrument stops at once: no endless reloading
        self.assertEqual(st["loads"], [SAFE])
        self.assertTrue(any("it is the safe instrument, stopping" in n for n in st["notes"]), st["notes"])


SAFE = ("factory", "a_granularlooper")


if __name__ == "__main__":
    unittest.main(verbosity=2)
