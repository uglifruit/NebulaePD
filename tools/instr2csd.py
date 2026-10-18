#!/usr/bin/env python3
"""Wrap a Nebulae .instr file into a standalone .csd, mirroring upstream Code/nebulae/conductor.py.

  python tools/instr2csd.py instr/demos/synth_voice.instr out.csd --secs 10 --set pitch=0.6 speed=0.5
  csound -n out.csd            # compile + run offline, no audio device
  csound -o out.wav out.csd    # render to a file to listen / inspect

Control channels default to 0 (as chnexport does) unless set with --set name=value. On the module the
Python app pushes the real knob values, so test a few positions.
"""
import argparse

HEADER = """
nchnls=2
0dbfs=1
gkpitch chnexport "pitch", 1
gkspeed chnexport "speed", 1
gkloopstart chnexport "start", 1
gkloopsize chnexport "size", 1
gkdensity chnexport "density", 1
gkoverlap chnexport "overlap", 1
gkwindow chnexport "window", 1
gkfilesel chnexport "file", 1
gkfreeze chnexport "freeze", 1
gkreset chnexport "reset", 1
gkblend chnexport "blend", 1
gkrecord chnexport "record", 1
gkfilestate chnexport "filestate", 1
gksource chnexport "source", 1
gksourcegate chnexport "sourcegate", 1
gksourcebuttonstate chnexport "source_state", 1
gkeol chnexport "eol", 2
gksizestatus chnexport "sizestatus", 2
gkrecordstatus chnexport "recordstatus", 2
gkbufferlength chnexport "bufferlength", 2
gkloopstart_alt chnexport "start_alt", 1
gkloopsize_alt chnexport "size_alt", 1
gkdensity_alt chnexport "density_alt", 1
gkoverlap_alt chnexport "overlap_alt", 1
gkwindow_alt chnexport "window_alt", 1
gkfreeze_alt chnexport "freeze_alt", 1
gkrecord_alt chnexport "record_alt", 1
gkfile_alt chnexport "file_alt", 1
gkreset_alt chnexport "reset_alt", 1
gksource_alt chnexport "source_alt", 1
gkpitch_alt chnexport "pitch_alt", 1
gkblend_alt chnexport "blend_alt", 1
gilen[] init 100
gichn[] init 100
gSname[] init 100
gisr[] init 100
gipeak[] init 100
ginumfiles init 0
"""


def parse(path):
    config, orc, inside = {}, [], False
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("nebconfigbegin"):
                inside = True
            if inside:
                if line.startswith("nebconfigend"):
                    inside = False
                elif not line.startswith("nebconfigbegin"):
                    parts = line.rstrip().split(",")
                    config[parts[0]] = parts[1:]
            else:
                orc.append(line)
    return config, "".join(orc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instr")
    ap.add_argument("csd")
    ap.add_argument("--secs", type=float, default=10)
    ap.add_argument("--set", nargs="*", default=[], help="channel=value, e.g. pitch=0.6")
    a = ap.parse_args()
    config, orc = parse(a.instr)
    ksmps = config.get("ksmps", ["128"])[0].strip()
    sr = config.get("sr", ["48000"])[0].strip()
    preamble = f"ksmps = {ksmps}\nsr = {sr}\n"
    # Set control channels at load (instr 0 runs before instr 1 starts at t=1, as on the module).
    sets = "".join(f'chnset {float(v)}, "{k}"\n' for k, v in (s.split("=") for s in a.set))
    score = f"f 0 {a.secs}\ni1 1 -10\n"
    with open(a.csd, "w", encoding="utf-8") as f:
        f.write("<CsoundSynthesizer>\n<CsOptions>\n-d\n</CsOptions>\n<CsInstruments>\n")
        f.write(preamble + HEADER + sets + orc)
        f.write("\n</CsInstruments>\n<CsScore>\n" + score + "</CsScore>\n</CsoundSynthesizer>\n")
    print("wrote", a.csd, "ksmps", ksmps, "sr", sr)


if __name__ == "__main__":
    main()
