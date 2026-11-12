#!/usr/bin/env python3
"""Cheat sheet of the Nebulae selector banks (uf1/uf2 paged selector), from the USB stick's files.

  python tools/stick_manifest.py D:\\                                   # what the stick holds now
  python tools/stick_manifest.py D:\\ --add firmware/dist/stage_uf2/2_install   # ... after copying those files too
  python tools/stick_manifest.py D:\\ --write D:\\nebulae_banks.txt     # also save it (the module ignores .txt)

Mirrors the firmware: the module copies the stick's .instr / .pd / .scd files into its banks at each load (a bank
is replaced only when the stick has files of that type), sorts them like filehandler.py (whole path, ignoring case:
digits before letters), hides "_" files in the Pd and SC banks, and shows at most 25 per bank, five per Pitch-light
colour. The factory bank is fixed in the firmware.
"""
import argparse
import os
import sys

FACTORY = ["a_granularlooper", "b_oneshot", "c_synth", "d_effects", "e_testio"]
BANKS = [  # (title, Speed position / light, extension, hide "_" files, stick folder name on the module)
    ("Csound, user bank", "Speed anticlockwise (left light)", ".instr", False),
    ("Factory (built in)", "Speed in the middle (both lights)", None, False),
    ("Pd", "Speed clockwise (right light green)", ".pd", True),
    ("SuperCollider", "Speed clockwise again (right light BLUE)", ".scd", True),
]
COLOURS = ["white", "orange", "yellow", "blue", "green"]
BUTTONS = ["Record", "File", "Source", "Reset", "Freeze"]
MAX_FILES = 25


def names(folders, ext, hide):
    found = {}
    for d in folders:
        try:
            for f in os.listdir(d):
                if f.lower().endswith(ext) and os.path.isfile(os.path.join(d, f)):
                    found[f[:-len(ext)]] = True
        except OSError:
            pass
    out = [n for n in found if not (hide and n.startswith("_"))]
    # filehandler.py sorts the full path with key (v.upper(), v[0].islower()); the folder is the same for all
    return sorted(out, key=lambda n: (n.upper(), n[0].islower()))


def sheet(folders):
    lines = []
    for title, where, ext, hide in BANKS:
        files = FACTORY if ext is None else names(folders, ext, hide)
        lines.append("=" * 78)
        lines.append("%s  -  %s  -  %d file%s" % (title, where, len(files), "" if len(files) == 1 else "s"))
        if not files:
            lines.append("  (empty: the module keeps the files it copied last time, if any)")
            continue
        if len(files) > MAX_FILES:
            lines.append("  NOTE: only the first %d are reachable" % MAX_FILES)
        for page in range((min(len(files), MAX_FILES) + 4) // 5):
            group = files[page * 5:page * 5 + 5]
            lines.append("  [%d-%d] Pitch light %s" % (page * 5 + 1, page * 5 + 5, COLOURS[page]))
            for i, n in enumerate(group):
                lines.append("      %-7s %2d  %s" % (BUTTONS[i], page * 5 + i + 1, n))
    lines.append("=" * 78)
    lines.append("Hold Speed 1.5 s = selector. Pitch turn = group of five. Lit button = loads at once. "
                 "Pitch/Speed click = leave.")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stick", help="the USB stick root (e.g. D:\\)")
    ap.add_argument("--add", action="append", default=[], help="also count files from this folder (to be copied)")
    ap.add_argument("--write", help="save the sheet to this file")
    a = ap.parse_args()
    if not os.path.isdir(a.stick):
        sys.exit("not found: " + a.stick)
    text = sheet([a.stick] + a.add)
    sys.stdout.write(text)
    if a.write:
        with open(a.write, "w", newline="\r\n") as f:
            f.write(text)
        print("written to " + a.write)


if __name__ == "__main__":
    main()
