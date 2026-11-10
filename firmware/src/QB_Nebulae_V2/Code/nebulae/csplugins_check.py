# uf2: checks one Csound plugin in this module's Csound, in its own process (csplugins.run_check). Python 2.
#   python2 csplugins_check.py <folder holding only the plugin> <plugin file name>
# Exit status 0 = OK. With any plugin present, an orchestra with core opcodes must compile and run (Csound skips a
# library it can't load, so this proves only that the plugin doesn't break Csound). libpearls.so must also load, run
# and make sound: the orchestra below is Pearls' own tools/verify_plugin.py at the
# commit of its prebuilt (635ce93, XponentOneAudio/QB_Nebulae_V2, MIT): synth mode, so it sounds without input.
import os
import sys

os.environ["OPCODE6DIR64"] = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # the firmware's own ctcsound.py
import ctcsound

CORE_ORC = """
sr = 48000
ksmps = 64
nchnls = 2
0dbfs = 1
instr 1
a1 oscili 0.1, 440
krms rms a1
chnset krms, "check_rms"
outs a1, a1
endin
"""

PEARLS_ORC = """
sr = 48000
ksmps = 64
nchnls = 2
0dbfs = 1
instr 1
a0 init 0
a1, a2, kgate, kled, kres, kq, kf, kc, kio, ksc pearls a0, a0, 0.3, 0.5, 0.5, 0.8, 0.6, 0.75, 0.2, 0.8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0
krms rms a1 + a2
chnset krms, "check_rms"
outs a1, a2
endin
"""


def perform(orc, seconds):
    c = ctcsound.Csound()
    for option in ["-n", "-d", "-m0"]:
        c.setOption(option)
    if c.compileOrc(orc) != 0:
        return None, 0
    c.readScore("i1 0 %f\n" % seconds)
    c.start()
    peak, cycles = 0.0, 0
    while c.performKsmps() == 0:
        peak = max(peak, c.controlChannel("check_rms")[0])
        cycles += 1
    c.cleanup()
    c.reset()
    return peak, cycles


def main():
    name = sys.argv[2]
    peak, cycles = perform(CORE_ORC, 0.3)
    if peak is None or cycles < 150 or peak < 0.01:
        print("FAIL: Csound does not run normally with %s loaded (%s, %d cycles)" % (name, peak, cycles))
        return 1
    if name == "libpearls.so":
        peak, cycles = perform(PEARLS_ORC, 1.2)
        if peak is None:
            print("FAIL: an orchestra using pearls did not compile (opcode not loaded)")
            return 1
        if cycles < 700 or peak < 0.001:
            print("FAIL: pearls did not run (%d cycles, rms %f)" % (cycles, peak))
            return 1
        print("OK: pearls loaded and running (output rms %.3f)" % peak)
        return 0
    # Csound skips a library it can't load, so for plugins other than Pearls this only proves they don't break it
    print("OK: Csound runs normally with %s present (its opcodes are not checked)" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
