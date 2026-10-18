# Getting a patch onto the Nebulae

Per the official reference (page 5):
1. Copy the `.pd` file to the **root of the FAT32 USB drive** (not in a folder). At boot, `*.pd` is copied to
   `/home/alarm/pd` (`handleuserfiles.sh`). To load while powered: hold **File** and press **Source**.
2. Hold the **Speed** encoder ~2-3 s to open the instrument selector (firmware v2.1.2 manual, p.24). Turn Speed to pick
   the bank: negative LED = `.instr`, both = Factory, **positive LED = Pure Data bank**. (v2.1.2: PD files can be
   loaded directly from the main granular instrument — no need to load another .instr first.)
3. Patches appear alphabetically across the 5 button LEDs (hence `00_`, `01_` prefixes). Press a button, then click
   Speed to load. Click Pitch to cancel. Pitch encoder scrolls when there are more than 5 files.
4. Nebulae boots into the last-used instrument (v2.1.2).

Patches must contain `[netreceive 3000]` (embedded in every patch here). Patches here are single self-contained files.
Audio files from USB are in `/home/alarm/audio`.

## Desktop testing
1. Install Pd vanilla (Windows: `C:\Program Files\Pd`).
2. Open a patch from `patches/`, turn DSP on.
3. Drive controls with `sim/sim_controls.pd` (same Pd session) or `python sim/send_fudi.py density 0.7 pitch 0.6`.
4. Headless smoke test: `pd -nogui -noaudio -stderr -open patches/01_drone.pd -send "; pd quit"` (no output = no load errors).
