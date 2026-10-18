# Getting a patch onto the Nebulae

Per the official reference (page 5):
1. Put your `.pd` file where the Nebulae looks for Pd patches. **The exact USB folder is not documented in the PDF or
   README — check the user manual / Qu-Bit support, or inspect a stock USB drive.** (`handleuserfiles.sh` in the
   upstream `Code/scripts/` copies user content at boot; read it to confirm.)
2. Load any factory `.instr` other than the default.
3. Hold the **Speed** encoder, turn right until only the positive speed LED is green.
4. Your Pd patches appear alphabetically on the button LEDs — hence the `00_`, `01_` prefixes. Press a button, then
   press the Speed encoder to load. Press the Pitch encoder to cancel.

Patches must contain `[netreceive 3000]` (embedded in every patch here). Patches here are single self-contained files.
Audio files from USB are in `/home/alarm/audio`.

## Desktop testing
1. Install Pd vanilla (Windows: `C:\Program Files\Pd`).
2. Open a patch from `patches/`, turn DSP on.
3. Drive controls with `sim/sim_controls.pd` (same Pd session) or `python sim/send_fudi.py density 0.7 pitch 0.6`.
4. Headless smoke test: `pd -nogui -noaudio -stderr -open patches/01_drone.pd -send "; pd quit"` (no output = no load errors).
