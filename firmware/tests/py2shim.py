"""Load the module's Python 2 firmware files under the desktop's Python 3, for logic tests.

Only `print x` statements are rewritten (to `print(x)`); everything else runs as written. Hardware and audio modules
are replaced by stubs. This checks logic, not Python 2 compatibility: a real `python2 -m py_compile` on every
changed file is still required (see docs/FIRMWARE.md).
"""
import os
import re
import sys
import types

sys.dont_write_bytecode = True   # never leave __pycache__ inside firmware/src

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "QB_Nebulae_V2", "Code", "nebulae")
BASE = os.path.join(ROOT, "base", "QB_Nebulae_V2", "Code", "nebulae")

PRINT_RE = re.compile(r"^(\s*)print(?:\s+(.*?))?\s*$")


def py2_to_py3(text):
    out = []
    for line in text.split("\n"):
        m = PRINT_RE.match(line)
        if m and not (m.group(2) or "").startswith("("):
            line = m.group(1) + "print(" + (m.group(2) or "") + ")"
        out.append(line)
    return "\n".join(out)


def load(name, src=SRC, register=True):
    path = os.path.join(src, name + ".py")
    with open(path) as f:
        code = py2_to_py3(f.read())
    mod = types.ModuleType(name)
    mod.__file__ = path
    if register:
        sys.modules[name] = mod
    exec(compile(code, path, "exec"), mod.__dict__)
    return mod


def compile_check(path):
    """Syntax smoke test of a Python 2 file (after the print rewrite)."""
    with open(path) as f:
        compile(py2_to_py3(f.read()), path, "exec")


def stub(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    if "." in name:
        parent, child = name.rsplit(".", 1)
        if parent not in sys.modules:
            stub(parent)
        setattr(sys.modules[parent], child, mod)
    return mod


# --------------------------------------------------------------------------------------------------- hardware stubs
class FakeGPIO(object):
    BCM = OUT = IN = PUD_UP = 0
    pins = {}

    @staticmethod
    def setmode(*a): pass

    @staticmethod
    def setwarnings(*a): pass

    @staticmethod
    def setup(*a, **k): pass

    @classmethod
    def output(cls, pin, val): cls.pins[pin] = val

    @classmethod
    def input(cls, pin): return cls.pins.get(("in", pin), 1)

    @staticmethod
    def cleanup(): pass


class FakeSwitch(object):
    """ui.py's encoder clicks: state() is driven by FakeSwitch.held[pin]."""
    held = {}

    def __init__(self, pin):
        self.pin = pin
        self.prev = self.cur = False

    def update(self):
        self.prev, self.cur = self.cur, bool(FakeSwitch.held.get(self.pin, False))

    def risingEdge(self): return self.cur and not self.prev

    def fallingEdge(self): return self.prev and not self.cur

    def state(self): return self.cur

    def prevState(self): return self.prev


class FakeEncoderWorker(object):
    steps = {}

    def __init__(self, a, b):
        self.key = (a, b)

    def start(self): pass

    def stop(self): pass

    def get_steps(self):
        s = FakeEncoderWorker.steps.get(self.key, 0)
        FakeEncoderWorker.steps[self.key] = 0
        return s


class Color(object):
    def __init__(self, r=4095, g=4095, b=4095):
        self.r, self.g, self.b = r, g, b

    def red(self): return self.r

    def green(self): return self.g

    def blue(self): return self.b


class FakeLedDriver(object):
    last = None

    def __init__(self):
        self.buttons, self.rgb = {}, {}
        FakeLedDriver.last = self

    def update(self): pass

    def set_button_led(self, name, bright): self.buttons[name] = bright

    def set_rgb(self, name, r, g, b, bright=1.0): self.rgb[name] = (r, g, b, bright)

    def cleanup(self): pass


class FakeShiftRegister(object):
    def update(self): pass

    def state(self, pin): return 0


class FakeControlChannel(object):
    """Stands in for control.ControlChannel. Values come from FakeControlChannel.script[name] (a list consumed one
    per update(), last value held) or stay at the init value."""
    script = {}

    def __init__(self, csound, name, init=0, source="static", data_channel=-1, **kw):
        self.name, self.source = name, source
        self.curVal = self.prevVal = init if init is not None else 0
        self.staticVal = self.curVal

    def update(self):
        seq = FakeControlChannel.script.get(self.name)
        self.prevVal = self.curVal
        if seq:
            self.curVal = seq.pop(0) if len(seq) > 1 else seq[0]

    def getValue(self): return self.curVal

    def getPrevValue(self): return self.prevVal

    def setValue(self, v): self.curVal = v

    def getStaticVal(self): return self.staticVal

    def getLEDValue(self): return self.curVal

    def getPotValue(self): return self.curVal

    def setModeChangeValue(self, v): pass

    def setIgnoreHID(self, s): pass

    def setIgnoreGate(self, s): self.ignore_gate = s

    def setIgnoreNextButton(self): pass

    def muteCSound(self, s): pass

    def hasChanged(self): return self.curVal != self.prevVal

    def getTrigSource(self): return "button"


class FakeCommChannel(object):
    def __init__(self, csound, name): pass

    def update(self): pass

    def getState(self): return 0

    def fallingEdge(self): return False


class FakeSettings(object):
    def __init__(self, cfg=None): pass

    def read(self): pass

    def load(self, name): return 0.5 if not name.endswith(("record", "freeze", "source", "file")) else 0

    def update(self, now): pass

    def write(self): pass

    def save(self, name, val): pass

    def getDefault(self, name):
        # the stock defaults file from the base tree
        with open(os.path.join(os.path.dirname(BASE), "config", "defaultnebsettings.txt")) as f:
            for line in f:
                key, _, val = line.strip().partition(",")
                if key == name:
                    return float(val) if "." in val else int(val)
        return 0


def install_hardware_stubs():
    stub("RPi")
    stub("RPi.GPIO", **{k: getattr(FakeGPIO, k) for k in dir(FakeGPIO) if not k.startswith("_")})
    stub("Adafruit_GPIO")
    stub("Adafruit_GPIO.SPI", SpiDev=lambda *a: None)
    stub("MCP3208", MCP3208=lambda **k: None)
    stub("ctcsound")
    stub("switch", Switch=FakeSwitch)
    stub("shiftregister", ShiftRegister=FakeShiftRegister, PIN_RESET=0, PIN_RECORD=3, PIN_FREEZE=4, PIN_SOURCE=5,
         PIN_SOURCE_GATE=6, PIN_NEXT=7)
    stub("encoder", Encoder=types.SimpleNamespace(Worker=FakeEncoderWorker))
    stub("leddriver", LedDriver=FakeLedDriver, Color=Color)
    stub("control", ControlChannel=FakeControlChannel, CommChannel=FakeCommChannel)
    stub("settings", SettingManager=FakeSettings)
    stub("wavewriter", WaveWriter=lambda: None)
    stub("numpy")
    sys.path.insert(0, SRC)       # py2/3-compatible uf1 modules (instrpager, nebopts, ufmigrate, pdsender) import as-is
