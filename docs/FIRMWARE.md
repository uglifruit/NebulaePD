# Custom firmware — safety, backup, install, revert

Goal: a custom Nebulae firmware for the owner's **Pi 4** unit (stock v2.1.2) with:
- a paged instrument selector;
- faster Pitch CV;
- robustness fixes;
- later, a Pd back-channel (EOL/LEDs) and SuperCollider.

**Stock v2 must always be one step away.** Plan: `Stage 0` (this page, no firmware change) → `uf1` (selector,
Pitch, fixes) → `uf1b` (back-channel) → `uf2` (SuperCollider).

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
- **The installer lives inside the firmware it replaces.** Custom builds therefore never change `Code/scripts/`,
  `Code/localfiles/` or the Python files that run before the app (`bootleds.py`, `check_calibration.py`,
  `calibration_collector.py`). The one exception is a one-line import fix. So a broken custom app can never stop the next USB update, including a revert.
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
   - `neb_pitchlog_*.txt` — the capture from step 2.
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

## Status
- 2026-11-09: Stage 0 tools written and offline-tested. **Not yet run on hardware.**
  - `fw_backup.instr` was tested in Csound 6.09.1 with `system_i` stubbed (silent / ok beeps / fail tone). Its shell script ran in a fake module tree: backup and layout correct, no overwrite on a 2nd run, a corrupt backup gives the fail tone.
  - `99_pitchlog` was tested with a simulated firmware stream. At 4 ms polls, 90 % of a jump takes 6 polls at coefficient 0.33 and 1 poll at 0.95.
