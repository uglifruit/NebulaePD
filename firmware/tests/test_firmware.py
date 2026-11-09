"""uf1 firmware logic tests (desktop Python 3).  Run:  python firmware/tests/test_firmware.py

Covers the new uf1 modules directly and the changed stock modules through py2shim (print statements rewritten,
hardware stubbed). It cannot prove Python 2 compatibility: compile every changed file with python2 as well.
"""
import inspect
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

CHANGED = ["check_calibration", "control", "controlhandler", "filehandler", "fileloader", "nebulae", "pdsender", "ui",
           "instrpager", "nebopts", "ufmigrate"]


class TestSyntax(unittest.TestCase):
    def test_changed_files_compile(self):
        for name in CHANGED:
            py2shim.compile_check(os.path.join(py2shim.SRC, name + ".py"))

    def test_no_py3_only_syntax(self):
        # things Python 2.7 would reject, in the lines uf1 touched
        import re
        bad = re.compile(r'(^|[^\w])f"|(^|[^\w])f\'|\bnonlocal\b|print\([^)]*\bend=|\basync\b|\bawait\b|:=')
        for name in CHANGED:
            with open(os.path.join(py2shim.SRC, name + ".py")) as f:
                for i, line in enumerate(f, 1):
                    self.assertIsNone(bad.search(line.split("#")[0]), "%s.py:%d %s" % (name, i, line.strip()))


class TestPager(unittest.TestCase):
    def test_pages_and_wrap(self):
        for n, pages in [(0, 1), (3, 1), (5, 1), (7, 2), (25, 5), (30, 5)]:
            p = instrpager.InstrPager(n)
            self.assertEqual(p.numPages(), pages, n)
            seen = []
            for _ in range(pages + 1):
                seen.append(p.page)
                p.nextPage()
            self.assertEqual(seen, list(range(pages)) + [0], n)

    def test_cap_25(self):
        p = instrpager.InstrPager(30)
        p.goto(27)
        self.assertEqual(p.index(), 0)        # beyond the cap: back to the first slot
        p.goto(24)
        self.assertEqual((p.page, p.cursor, p.index()), (4, 4, 24))

    def test_cursor_clamp_and_short_page(self):
        p = instrpager.InstrPager(7)
        p.move(10)
        self.assertEqual(p.cursor, 4)
        p.nextPage()                          # page 2 has 2 files: cursor clamps to the last one
        self.assertEqual((p.page, p.cursor, p.index()), (1, 1, 6))
        self.assertEqual(p.leds(), [0.3, 1.0, 0.0, 0.0, 0.0])
        p.move(-9)
        self.assertEqual(p.index(), 5)

    def test_goto_index_ge_5(self):
        p = instrpager.InstrPager(12)
        p.goto(7)
        self.assertEqual((p.page, p.cursor, p.offset()), (1, 2, 5))
        self.assertEqual(p.leds(), [0.3, 0.3, 1.0, 0.3, 0.3])

    def test_empty(self):
        p = instrpager.InstrPager(0)
        p.nextPage()
        p.move(3)
        self.assertIsNone(p.index())
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
        boot = time.time()
        self.put(self.old, ufmigrate.CAL, CAL_GOOD)
        self.put(self.old, "config/bootinstr.txt", "bank,puredata\ninstr,07_shimmer\n")
        self.put(self.old, "config/nebsettings.txt", "x")
        self.put(self.code, ufmigrate.CAL, CAL_GOOD.replace("0.027", "0.3"), mtime=boot - 60)  # forced, last boot
        log = ufmigrate.migrate(self.code, self.old, booted_at=boot)
        self.assertEqual(self.read(self.code, ufmigrate.CAL), CAL_GOOD)
        self.assertIn("07_shimmer", self.read(self.code, "config/bootinstr.txt"))
        self.assertTrue(os.path.exists(self.code + ufmigrate.MARKER), log)
        # second start: marker present -> untouched
        self.put(self.code, ufmigrate.CAL, "changed")
        self.assertEqual(ufmigrate.migrate(self.code, self.old, booted_at=boot), [])
        self.assertEqual(self.read(self.code, ufmigrate.CAL), "changed")

    def test_calibrated_this_boot_wins(self):
        boot = time.time() - 30
        self.put(self.old, ufmigrate.CAL, CAL_GOOD)
        self.put(self.old, "config/bootinstr.txt", "bank,factory\n")
        self.put(self.code, ufmigrate.CAL, "pitch held at boot", mtime=boot + 5)
        ufmigrate.migrate(self.code, self.old, booted_at=boot)
        self.assertEqual(self.read(self.code, ufmigrate.CAL), "pitch held at boot")
        self.assertFalse(os.path.exists(self.code + "config/bootinstr.txt"))

    def test_invalid_or_missing_old(self):
        boot = time.time()
        self.put(self.old, ufmigrate.CAL, "start,abc,\n")
        self.put(self.code, ufmigrate.CAL, "new", mtime=boot - 60)
        ufmigrate.migrate(self.code, self.old, booted_at=boot)
        self.assertEqual(self.read(self.code, ufmigrate.CAL), "new")
        shutil.rmtree(self.old)
        os.remove(self.code + ufmigrate.MARKER)
        self.assertIn("no previous tree", ufmigrate.migrate(self.code, self.old, booted_at=boot)[0])
        self.assertFalse(ufmigrate.valid_calibration(self.d + "/nope.txt"))
        self.put(self.code, "x.txt", CAL_GOOD.replace("pitch,0.027", "pitch,9"))
        self.assertFalse(ufmigrate.valid_calibration(self.code + "x.txt"))

    def test_unknown_boot_time_keeps_stock(self):
        self.put(self.old, ufmigrate.CAL, CAL_GOOD)
        self.put(self.code, ufmigrate.CAL, "forced")
        ufmigrate.migrate(self.code, self.old, booted_at=None)
        self.assertEqual(self.read(self.code, ufmigrate.CAL), "forced")

    def test_never_raises(self):
        self.assertTrue(ufmigrate.migrate(self.d + "/missing/", self.old, booted_at=0)[-1].startswith(
            "migration error"))


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
                    data += c.recv(100)
                got.append(data)
                c.close()
            t = threading.Thread(target=accept)
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
    """Real controlhandler.py + ui.py (stubbed hardware): Next pages, Pitch moves the cursor, Reset loads."""

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

    def test_paging_cursor_load(self):
        self.ch.enterInstrSelMode()
        self.tick()
        self.assertEqual(self.leds(), [0.3, 1.0, 0.3, 0.3, 0.3])     # page 2 (6-10), cursor on 07
        self.assertEqual(self.pitch_colour(), (4095, 1100, 0))       # orange = page 2
        self.press("file_instr")                                     # one press held 3 polls = one page
        self.assertEqual(self.ui.pager.page, 2)
        self.assertEqual(self.leds(), [0.3, 1.0, 0.0, 0.0, 0.0])     # 11, 12; cursor stays on slot 2
        self.assertEqual(self.pitch_colour(), (4095, 3395, 0))       # yellow = page 3
        self.press("file_instr")
        self.assertEqual(self.ui.pager.page, 0)
        self.assertEqual(self.pitch_colour(), (4095, 4095, 4095))    # white = page 1
        py2shim.FakeEncoderWorker.steps[(17, 27)] = 9                # Pitch encoder: cursor clamps at slot 5
        self.tick(2)                                                 # LEDs are drawn before the encoders are read
        self.assertEqual(self.leds(), [0.3, 0.3, 0.3, 0.3, 1.0])
        for name in ["record_instr", "source_instr", "freeze_instr"]:
            self.press(name)                                         # unused in the selector
        self.assertFalse(self.ui.getReloadRequest())
        self.press("reset_instr")
        self.assertTrue(self.ui.getReloadRequest())
        self.assertEqual(self.ui.getNewInstr(), "05_p")
        self.assertEqual(self.ch.getInstrSelBank(), "puredata")

    def test_bank_switch_and_hidden(self):
        self.ch.enterInstrSelMode()
        self.tick()
        self.assertEqual(self.ui.puredata_fhandle.getFileNames(), self.pd)   # _helper hidden, externals not listed
        py2shim.FakeEncoderWorker.steps[(6, 13)] = -8                # Speed: puredata -> factory
        self.tick(2)
        self.assertEqual(self.ch.getInstrSelBank(), "factory")
        self.assertEqual(self.leds(), [1.0, 0.3, 0.3, 0.3, 0.3])
        py2shim.FakeEncoderWorker.steps[(6, 13)] = -8                # factory -> user (empty)
        self.tick(2)
        self.assertEqual(self.ch.getInstrSelBank(), "user")
        self.assertEqual(self.leds(), [0.0] * 5)
        self.press("reset_instr")
        self.assertFalse(self.ui.getReloadRequest())                 # nothing to load in an empty bank

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


class TestFlatLoop(unittest.TestCase):
    """nebulae.py's main loop over many instrument switches: constant stack depth, Pd waited for."""

    def test_switches(self):
        state = {"switches": 0, "depths": [], "pd_alive": 0, "max_switches": 400}

        class HasKeyDict(dict):
            def has_key(self, k): return k in self

        class Csound(object):
            def setOption(self, o): pass
            def compileOrc(self, o): pass
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
            def setCsoundPerformanceThread(self, p): pass
            def enterPureDataMode(self): pass
            def updateAll(self): pass
            def restoreAltToDefault(self): pass
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
        py2shim.stub("logger", NebLogger=lambda: type("L", (), {"spill_basic_info": lambda s: None})())
        py2shim.stub("neb_globals", remount_fs=False)
        py2shim.stub("ufmigrate", migrate=lambda: ["ok"])
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
        self.assertEqual(len(d), state["max_switches"] + 1)
        self.assertEqual(min(d), max(d))
        self.assertEqual(state["pd_alive"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
