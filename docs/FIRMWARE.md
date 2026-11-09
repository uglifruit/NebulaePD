# Custom firmware — safety, backup, install, revert

Goal: a custom Nebulae firmware for the owner's **Pi 4** unit (stock v2.1.2) with:
- a paged instrument selector;
- faster Pitch CV;
- robustness fixes;
- later, a Pd back-channel (EOL/LEDs) and SuperCollider.

**Stock v2 must always be one step away.** Plan: `Stage 0` (this page, no firmware change) → `uf1` (selector,
Pitch, fixes, Pd externals copied from the stick, `_`-prefixed abstractions hidden from the selector) → `uf1b` (back-channel) → `uf2` (SuperCollider).

## To do
**Owner (on hardware), in one session:**
1. Stage 0 steps 1–5 below. For step 3, also copy `firmware/dist/v2_1_2_uf1/neb_candidate.tgz` and
   `neb_candidate_manifest.txt` to the stick root, so the backup run checks uf1 with the module's own Python 2.
   Nothing is installed by this.
2. Copy the stick's `neb_fwbackup/` folder to `firmware/device/`.

**Next session (Claude), once `firmware/device/` exists:**
1. Read `inventory_*.txt`:
   - the "uf1 precheck" section must show `PY2_COMPILE_OK` and `PY2_SELFTEST_OK`;
   - check the arch, glibc, Pd version, `checkfirmware.sh`, and whether `/boot/config.txt` underclocks the Pi 4.
2. `python tools/pitchlog.py firmware/device/neb_pitchlog_*.txt` gives the real poll rate and stock Pitch slew. Put
   them in HANDOFF §4.
3. `python tools/fwbuild.py --import-device firmware/device/neb_update.zip`. It stops on conflicts if the unit's
   tree differs from GitHub's in a file uf1 changes; merge those by hand.
4. Run `python firmware/tests/test_firmware.py` and `test_fwbuild.py`, then `python tools/fwbuild.py`, which now
   writes an installable `neb_update.zip`.
5. Hand over the uf1 install with the hardware test list (Stage 1 below).

**Decided (owner, 2026-11-09):** every Pd patch load resets the alt layer to its defaults. Because of that,
`pd_alts_at_load` can only send the defaults, which our patches already start with, so it is harmless. It stays off
as it gains nothing.

## How updates work (from upstream source)
- At boot, `/home/alarm/checkfirmware.sh` runs `Code/scripts/startup.sh`. The script is on the OS image and isn't user-updatable.
- `startup.sh` runs `Code/scripts/update.sh`, which looks for **`neb_update.zip` in the stick's root**. Despite its name, that file is a tar.gz of `QB_Nebulae_V2/Code/...`. `update.sh` then:
  1. moves the current tree to `/home/alarm/backup/old`;
  2. installs the new one;
  3. **forces a CV recalibration** (it assumes nothing is patched);
  4. logs "Firmware updated to: …" in `neb_log.txt`;
  5. **deletes the zip from the stick**;
  6. reboots.
- The update replaces the whole tree, so these go back to the new tree's copies:
  - calibration;
  - last instrument (`bootinstr.txt`);
  - alt settings (`nebsettings.txt`).

  Your `/home/alarm/{audio,pd,instr}` files are not touched.
- **The installer lives inside the firmware it replaces.** Custom builds therefore never change:
  - `Code/scripts/` or `Code/localfiles/`;
  - `Code/config.txt`, except the VERSION line that the build sets;
  - `bootleds.py` or `calibration_collector.py`;
  - `check_calibration.py`, except the one-line import fix.

  `tools/fwbuild.py` refuses to build if they differ. The install itself (`tar` + `mv` in `update.sh`) runs before
  any Python. A Python bug in the custom app, even in `control.py`/`controlhandler.py`, which the forced calibration
  imports, can't stop the next USB update, including a revert.
- Don't use Qu-Bit's public `FirmwareUpdates/v_2_1_2/neb_update.zip` to revert this unit.
  - It is Pi 3-era: its `startup.sh` writes Pi 3 clock settings into `/boot/config.txt` on every boot.
  - The Pi 4 image may differ from it.
  - Revert with **your unit's own backup** (below).

## Stage 0 — back up, measure, prove the revert path
Do these in order. Nothing on the module changes until step 5, and step 5 reinstalls exactly what is already
there.

**1. Image the SD card (last-resort restore).**
1. Power the case off and take the microSD card out of the Pi 4 on the back of the module.
2. In Win32 Disk Imager, choose a file name like `nebulae_pi4_stock_YYYYMMDD.img`, tick "Read Only Allocated Partitions" **off**, and click **Read**.
3. Tick an MD5 hash and note it.
4. Put the card back.

To restore later, use **Write** with the same image.

**2. Measure the stock Pitch response (`patches/99_pitchlog.pd`).**
1. Copy `99_pitchlog.pd` to the stick's root and boot.
2. Select it in the Pd bank (hold Speed 1.5 s, …).
3. Patch a stepped V/oct into the **Pitch CV jack**: a square LFO or a sequencer, about 1 Hz, 0 V ↔ 3 V or more. Leave the Pitch encoder alone.
4. Press **Reset**. You'll hear a high beep and the raw pitch as a sine tone.
5. Wait for the 20 s capture to end (two higher beeps).

The log sits in RAM (`/dev/shm`), so **don't power off** before step 3. Another Reset starts a new capture and replaces the old one.

**3. Back up and inventory (`instr/fw_backup.instr`).**
1. Copy `fw_backup.instr` to the stick's root, re-insert the stick, and select it in the **user** bank. Audio passes through.
2. Wait for the result. It repeats every 4 s:
   - **three short high beeps** = done and verified;
   - **one long low tone** = something failed: send me the `inventory_*.txt`;
   - **nothing after 2 minutes** = `system_i` is missing on this Csound build.
3. Power off and copy the stick's **`neb_fwbackup/`** folder to `firmware/device/` in this repo, and to a second place. It contains:
   - `neb_update.zip` — **your revert package** (your unit's exact firmware tree). It is made only on the first run and later runs never overwrite it;
   - `inventory_*.txt` — OS, CPU and clocks, Pd/Csound/Python versions, packages, libraries, disk, `checkfirmware.sh`, `/boot/config.txt`;
   - `code_sha256_*.txt`, `checkfirmware.sh`, `boot_config.txt`, `nebulae.service`, `backup_old.tgz` (the previous tree, if any);
   - `neb_pitchlog_*.txt` — the capture from step 2;
   - with `neb_candidate.tgz` on the stick: the inventory's "uf1 precheck" section holds the module's own
     `python2 -m py_compile` of every uf1 file and a short self-test.
4. Analyse the capture with `python tools/pitchlog.py firmware/device/neb_pitchlog_*.txt`.

**4. Leave the stick's `neb_fwbackup/` folder in place.** `update.sh` only looks at `neb_update.zip` in the **root**, so it is ignored where it is.

**5. Revert drill (proves the USB path on this Pi 4 before anything is changed).**
1. Copy `neb_fwbackup/neb_update.zip` to the stick **root**.
2. **Unplug every cable from the module's CV/gate jacks** (forced recalibration), then power on.
3. Expect:
   - green cycling LEDs (installing);
   - a reboot;
   - "Firmware updated to: v2_1_2" in `neb_log.txt`;
   - the zip gone from the root.
4. Play a few instruments.

## Reverting from a custom build (any time)
- Put `neb_fwbackup/neb_update.zip` in the stick root, unplug all CV/gate cables, and power on.
- If the module doesn't reach the update step at all, write the SD image back (step 1).

## Stage 1 — uf1 (`v2_1_2_uf1`)
Built from `firmware/src` by `tools/fwbuild.py`. `git diff --no-index firmware/base firmware/src` is the whole
change set. **Not yet installable:** the base is still Qu-Bit's GitHub v2.1.2 until the unit's backup arrives.

### What changes for the player
- **Instrument selector** (hold Speed 1.5 s, as stock):

  | Control | Action |
  |---|---|
  | Speed turn | Bank (user ← factory → Pd), as stock |
  | **Next** | Next page: 1–5 → 6–10 → 11–15 → 16–20 → 21–25 → 1–5. Only as many pages as there are files |
  | **Pitch LED** | Page colour: white, orange, yellow, blue, green (the octave colours) |
  | **Pitch turn** | Cursor within the page |
  | **Reset** | Load the instrument under the cursor (Speed click also loads, as stock) |
  | Pitch click | Cancel, as stock |
  | Record / Source / Freeze | Nothing in the selector |

  - Button LEDs: cursor = full, other files on the page = dim, empty slots = off.
  - The selector opens on the running instrument's page.
  - Up to 25 files per bank are reachable.
  - File lists are re-read each time the selector opens, so new files on the stick show up without a reboot.
- **Alt layer reset on every Pd patch load** (including a reload and the patch at boot). Every `*_alt` goes back to
  `defaultnebsettings.txt`: 0, except input gain `speed_alt` = 23 (0 dB). Alt knobs then need to move before they
  take over again, as after Source + Pitch click.
  - Stock did this only for Csound instrument changes.
  - Pd patches got whatever the last Csound instrument had saved, because Pd mode never saves alt values.
- **Pitch CV:** the firmware's one-pole goes from 0.33 to **0.95** per poll. A 3-octave jump settles in 2 polls
  instead of 12. Steady CV is still held by the hysteresis and stability gate (±1 LSB noise gives 0 output changes in
  both).
- **`neb_options.txt`** in the stick root (optional, copied at each instrument load, kept when the stick has none):
  ```
  pitch_coeff = 0.95     # 0.05-1.0; 0.33 = stock glide
  pd_alts_at_load = 0    # 1 = also send the (default) alt values once when a Pd patch connects
  ```
- **Pd externals:** `.pd_linux`, `.l_arm` and `.l_arm64` files in the stick root are copied next to the patches, so
  `[clds~]`-style objects load (as in Technobear's firmware).
- **Hidden helper patches:** `.pd` files starting with `_` are copied but not listed (use them as abstractions).
- **After a firmware update:** the first start restores calibration, last instrument, alt settings and
  `neb_options.txt` from the replaced tree (`/home/alarm/backup/old`).
  - The calibration is restored only if the old file is valid.
  - Nothing is restored if Pitch was held at power-on (deliberate recalibration and reset) or the boot time is
    unknown.
  - The first uf1 install still runs stock's forced calibration: unplug all CV/gate cables for it.

### Fixes (no behaviour change otherwise)
- Hold Pitch at power-on now also resets the settings, as the code intended: `check_calibration.py` was missing
  `import neb_globals` and crashed after calibrating.
- The selector showed and reselected files 6+ wrongly after boot (`idx % 5` with offset `idx / 5`).
- Name matching was by substring of the path, so `drone` matched `01_drone`. It is now exact.
- `FileHandler(dir, ".pd")` iterated the string's characters, so it globbed `*.`, `*p` and `*d`. Any file ending in
  "d" was listed. It now uses real extension lists.
- `ui.py` referred to `puredatainstr_fhandle`, which doesn't exist (a crash in an edit function).
- `getNewInstr` crashed on an out-of-range index, and "reload current" crashed when the file was gone.
- **Pd connection:** stock tried to connect once, 2 s after launching Pd. A slow-loading patch then got no controls
  for the whole session. uf1 retries every 250 ms, also after a lost connection.
- Each pass's messages now go out in one `sendall`, giving the same bytes as the stock stream. Real Pd received
  750/750 messages in order.
- The main loop no longer recurses on every instrument change. Stock's stack grew per switch until a crash after a
  few hundred switches.
- Switching away from Pd waits up to 2 s for Pd to exit before the next engine opens the audio device.

### Developer workflow
```bash
python firmware/tests/test_firmware.py   # 26 logic tests: stock modules via firmware/tests/py2shim.py, hardware stubbed
python firmware/tests/test_fwbuild.py    # packer fidelity (base repack == Qu-Bit zip), guards, --import-device
python tools/fwbuild.py --check          # guards only
python tools/fwbuild.py                  # -> firmware/dist/v2_1_2_uf1/ (+ neb_candidate.* for the on-module check)
python tools/fwbuild.py --from base      # the base, repacked (a revert zip for the base)
python tools/fwbuild.py --import-device firmware/device/neb_update.zip
```
- Edit `firmware/src` only. `firmware/base` is the reference tree.
- `firmware/` is stored without line-ending conversion (`.gitattributes`).
- The tests run with bytecode writing off, so `firmware/src` gets no new `__pycache__`.
- Desktop tests can't prove Python 2.7 compatibility. Use the on-module precheck in `fw_backup.instr`: a
  micromamba-based local Python 2.7 install was blocked by the session's permission rules.

### Hardware test (owner, after the installable build)
1. Unplug all CV/gate cables. Put `neb_update.zip` in the stick root and boot. Expect the update animation and
   reboots, and "Firmware updated to: v2_1_2_uf1" in `neb_log.txt`.
2. The last instrument and calibration should be back (the restore). Play a Pd patch and a Csound instrument.
3. Selector: 7+ Pd files on the stick. Check the paging and LEDs, Reset to load, booting into file 7 opens page 2,
   and `_helper.pd` is hidden.
4. `99_pitchlog` capture again (compare with Stage 0), and 08_resonator by ear on big V/oct jumps.
5. Revert drill: the Stage 0 backup zip goes back to v2_1_2. Then reinstall uf1.

## Status
- 2026-11-09: Stage 0 tools written and offline-tested. **Not yet run on hardware.**
  - `fw_backup.instr` was tested in Csound 6.09.1 with `system_i` stubbed (silent / ok beeps / fail tone). Its shell script ran in a fake module tree: backup and layout correct, no overwrite on a 2nd run, a corrupt backup gives the fail tone.
  - `99_pitchlog` was tested with a simulated firmware stream. At 4 ms polls, 90 % of a jump takes 6 polls at coefficient 0.33 and 1 poll at 0.95.
- 2026-11-09: uf1 written on the provisional GitHub base.
  - 26 logic tests and 10 build tests pass. The batched FUDI stream was checked against real Pd 0.57.
  - `fw_backup.instr` gained the on-module Python 2 precheck (its shell path is tested here; python2 itself runs only
    on the module).
  - **Not compiled with Python 2 yet. Not installed.**
