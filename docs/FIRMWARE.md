# Custom firmware — safety, backup, install, revert

Goal: a custom Nebulae firmware for the owner's **Pi 4** unit (stock v2.1.2) with:
- a paged instrument selector;
- faster Pitch CV;
- robustness fixes;
- later, a Pd back-channel (EOL/LEDs) and SuperCollider.

**Stock v2 must always be one step away.** Plan: `Stage 0` (this page, no firmware change) → `uf1` (selector,
Pitch, fixes, Pd externals copied from the stick, `_`-prefixed abstractions hidden from the selector) → `uf1b` (back-channel) → `uf2` (SuperCollider).

## To do
**Owner (on hardware): the uf1 install session.** Files are staged in `firmware/dist/stage1_stick/`. Use the
cloned card; the original stays in the drawer as STOCK.
1. **Precheck.** Copy `1_precheck/*` to the stick root (no `neb_update.zip` in the root yet). Boot and load
   `000_fw_backup` from the user bank.
   - **Three beeps** = backup fine and uf1 passed the module's Python 2 check. Go on.
   - **Low tone** = stop and bring the stick back.
2. **Install.** Power off. Copy `2_install/neb_update.zip` and `99_pitchlog.pd` to the stick root. **Unplug every
   CV/gate cable**, then power on. Expect the update LEDs and a reboot.
3. **Test** with the list in "Hardware test" (Stage 1 below). End by loading `000_fw_backup` again, which collects
   the new pitch log and the migration result, and copy the stick's `neb_fwbackup/` folder (the newest
   `inventory_*.txt` and `neb_pitchlog_*.txt`) to `firmware/device/`.

**Next session (Claude):**
1. Newest inventory: `Firmware updated to: v2_1_2_uf1`, the `uf_migrated` content ("restored calibration…"), and
   `PRECHECK_OK`.
2. `python tools/pitchlog.py` on the uf1 capture; compare with the stock one (Stage 0 results below).
3. Go through the owner's hardware test notes.

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

## What the SD image showed (2026-11-09)
Read offline from `SDImage/nebulae_stock_pi4.img` with WSL `debugfs` (read-only).
- **System:**
  - Arch Linux ARM, 32-bit (`linux-rpi 5.15.43`, `kernel7.img`), glibc 2.35, 280 packages, from mid-2022;
  - **Pd 0.52.2**, Csound 6.11.0, Python 2.7.18;
  - jack2 1.9.21 and liblo are installed. SuperCollider is not.
- **The unit's firmware tree is not GitHub's v2.1.2.** Qu-Bit's Pi 4 port (2022) changed five files, all marked
  `VERSION=v2_1_2`:
  - `shiftregister.py`: a 10 µs sleep between bit reads, presumably because the Pi 4 is too fast for the button
    shift register;
  - `digitaldata.py`: the incremental value is updated in one step, so another thread can't read it half-done;
  - `nebulae.py` / `controlhandler.py`: an `initial_startup` flag, passed around but its use commented out (no effect);
  - `localfiles/nebulae.service`: `User=root`.

  `firmware/base` is now this tree (`firmware/device_image/neb_update.zip`, packed from the image with the unit's
  modes and owners). uf1 was rebased onto it with a three-way merge, which kept all five changes. A uf1 built on
  GitHub's tree would have dropped them.
- **`/home/alarm/checkfirmware.sh`** (run by `nebulae.service` at every boot, outside the firmware tree) has its own
  revert:
  - if any file in `/home/alarm/mandatory_files.txt` is missing or empty under `Code/`, or the stick root holds a
    file named **`revert_to_factory_firmware`**, it deletes `QB_Nebulae_V2/` and unpacks
    `/home/alarm/neb_factory_fw.zip`;
  - that factory tree is **v1.0.0 (2018)**, older than the Pi 4 port, so it may not run properly on this unit. Use
    it only if nothing else works, then install v2.1.2 again from USB;
  - `fwbuild` refuses any build that lacks one of the mandatory files.
- **Qu-Bit's official "Nebulae v2 Pi 4 Disk Image"** (free download, qubitelectronix.com/alternate-firmware) is
  `SDImage/nebulae_6gb_11_15.img`, dated 2022-11-15, 6,211,764,224 bytes, SHA256
  `A64E1F20DBEC814CA9888B1C52C543F06AE122159D4B635C8DB30E0BD056046F`. Compared read-only with the owner's card:
  - same master: identical partition table, same ext4 filesystem (same creation time), same 280 packages, same
    `checkfirmware.sh`, mandatory list, service file and factory v1.0.0 package. The "errors seen" ext4 flag is in
    Qu-Bit's image too;
  - **the firmware code is identical**, so `firmware/base` is Qu-Bit's official Pi 4 build. Only the runtime files
    differ;
  - Qu-Bit's image carries another unit's calibration, which is why their page says to recalibrate V/oct after
    flashing. It also holds Qu-Bit's bench leftovers (a test patch, a test instrument and a few large test
    recordings) instead of the owner's files;
  - so the owner's own image is the one to restore. Qu-Bit's is an independent fallback (recalibrate after it).
- `/home/alarm/backup/new/neb_update.zip` is the update Qu-Bit installed on 2022-06-02. It differs from GitHub only in
  `digitaldata.py` and `nebulae.service`; the other three Pi 4 changes were made in place afterwards.

## Stage 0 results (module run, 2026-11-10)
- `fw_backup.instr` worked: `system_i` runs shell commands on this Csound. `firmware/device/` holds its output.
  Its `neb_update.zip` has the same code as `firmware/device_image/neb_update.zip`; only `bootinstr.txt` differs.
- **Inventory:**
  - hardware and system: Raspberry Pi 4 Model B Rev 1.5 (BCM2711, 4 GB), 32-bit armv7l, governor `performance`;
  - **CPU clock: 1200 MHz** (`arm_freq=1200`);
  - software: Pd 0.52.2, Csound 6.11 (double), Python 2.7.18, jackd present, no SuperCollider;
  - space: root 951 MB free (82 % used), `/dev/shm` 128 MB, stick 960 MB.
- **No real clock.** The Pi has no RTC and no network, so every boot starts at about 2022-06-11 12:13 UTC.
  Nothing may rely on file times:
  - `ufmigrate` no longer uses them;
  - `fwbuild` stamps files 2022-05-01, because 2026 dates were "in the future" for tar on the unit.
- **uf1 precheck:**
  - `PY2_COMPILE_OK` for every uf1 file (build `802db7e1…`).
  - The self-test then stopped on a bug in the test line itself: Python 2 refuses an unbound method called with
    `None`. Fixed with `im_func`.
  - Since then, `ufmigrate.py` changed, so the next run checks again.
  - The result sounds now include the precheck, so three beeps mean it passed.
- **Pitch log** (`tools/pitchlog.py firmware/device/neb_pitchlog_220611_121645.txt`):
  - **Poll pass: 5.3 ms mean** (median 5.5, 4–8 ms), one `pitch` message per pass.
  - **The Pitch filter steps twice per pass.** `ui.set_pitch_amount()` calls `setValue("pitch", …)` every pass,
    and that reads the ADC and filters again. So stock is effectively 1 − 0.67² = 0.55 per pass.
  - The capture hit the 1.30 clip (1.00 ↔ 1.30), so rising edges look instant. Falling edges are clean:
    **90 % in ~4 passes (~21 ms), settled in ~7 (~37 ms)**. That is the glide 08_resonator shows.
  - With 0.95 (twice per pass) a jump should settle in about 1 pass (~5 ms).
  - For the uf1 comparison, use an in-range step: Pitch clicked to centre, CV 0 V ↔ 1 V.

## Stage 0 — back up, measure, prove the revert path
Do these in order. Nothing on the module changes until step 5, and step 5 reinstalls exactly what is already
there.

**1. Image the SD card (last-resort restore).**
1. Power the case off and take the microSD card out of the Pi 4 on the back of the module.
2. Windows can read only the small boot partition, not the ext4 system partition. **Never accept "Format" or
   "Scan and fix".**
3. Run Win32 Disk Imager as administrator and pick the card's boot-partition letter as Device. It reads the whole
   card anyway. Tick "Read Only Allocated Partitions" and click **Read**.
4. Put the card back.

To restore later, use **Write** with the same image (any card of 8 GB or more).

**Done 2026-11-09:** `SDImage/nebulae_stock_pi4.img` (gitignored; keep a second copy off this PC).
- 6,211,764,224 bytes, SHA256 `BE1766FA3675FD8FF6B7B37C9C0C778F148D6637925E7BCDD07739BD75AC0C56`.
- Card layout (29.7 GB card): MBR, p1 200 MB FAT16 `/boot`, p2 6.0 GB ext4 root (4.7 GB used, 1.3 GB free); the
  rest of the card is unpartitioned. The ext4 superblock carries the "errors seen" flag (state 3), which is common
  after power-off without shutdown; the image is a faithful copy either way.
- Facts read from `/boot`:
  - 32-bit kernel only (`kernel7.img`, no `kernel8.img`), so the userland is presumably armv7h. The inventory will
    confirm.
  - `config.txt` is byte-for-byte the Pi 3-era `Code/localfiles/config.txt` (`arm_freq=1200`, `gpu_freq=75`,
    `core_freq=400`). So this Pi 4 runs underclocked from its 1500 MHz default. Left as is (see "Deliberately not
    fixed").
  - `cmdline.txt`: `root=/dev/mmcblk0p2 rw rootwait …`.

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
1. Copy `neb_fwbackup/neb_update.zip` (or `firmware/device_image/neb_update.zip`, the same code from the SD image) to
   the stick **root**.
2. **Unplug every cable from the module's CV/gate jacks** (forced recalibration), then power on.
3. Expect:
   - green cycling LEDs (installing);
   - a reboot;
   - "Firmware updated to: v2_1_2" in `neb_log.txt`;
   - the zip gone from the root.
4. Play a few instruments.

## Reverting from a custom build (any time)
In order of preference:
1. **Swap cards:** put the STOCK card back in the Pi 4. Seconds, nothing to install.
2. **USB:** put `neb_fwbackup/neb_update.zip` or `firmware/device_image/neb_update.zip` in the stick root, unplug all
   CV/gate cables, and power on.
3. **SD image:** write `SDImage/nebulae_stock_pi4.img` to a card (Win32 Disk Imager **Write**, or Raspberry Pi
   Imager "Use custom" with OS customisation off). If that is lost, Qu-Bit's `nebulae_6gb_11_15.img` gives the same
   firmware, but V/oct must then be recalibrated (hold Pitch at power-on, nothing patched).
4. Emergency only: a file named `revert_to_factory_firmware` in the stick root makes `checkfirmware.sh` install the
   factory v1.0.0 tree (see above). Then do 2.

## Stage 1 — uf1 (`v2_1_2_uf1`)
Built from `firmware/src` by `tools/fwbuild.py`. `git diff --no-index firmware/base firmware/src` is the whole
change set. The base is the unit's own tree (from the SD image), so `fwbuild` writes an installable
`neb_update.zip`. **Hold it until the on-module Python 2 precheck passes** (Stage 0 step 3 with `neb_candidate.tgz`).

### What changes for the player
- **Instrument selector** (hold Speed 1.5 s, as stock):

  | Control | Action |
  |---|---|
  | Speed turn | Bank, as stock: CCW = your Csound instruments, middle = factory, CW = Pd patches (each sorted alphabetically) |
  | **Pitch turn** | Page of five: 1–5, 6–10, 11–15, 16–20, 21–25. One detent per page (`sel_page_steps`), stops at the first and last page |
  | **Pitch LEDs** | Page colour: white, orange, yellow, blue, green (the octave colours) |
  | **The five buttons** | Left to right = the five patches on the page. A press **loads that patch at once** |
  | Pitch or Speed click | Leave without loading |

  - Button LEDs: lit = a patch is there, bright = the one running now, off = empty slot (a press does nothing).
  - The selector opens on the running instrument's page.
  - Decided by the owner (2026-11-10), replacing the first uf1 design (Next = page, Pitch = cursor, Reset = load).
  - Up to 25 files per bank are reachable.
  - File lists are re-read each time the selector opens, so new files on the stick show up without a reboot.
- **Alt layer reset on every Pd patch load** (including a reload and the patch at boot). Every `*_alt` goes back to
  `defaultnebsettings.txt`: 0, except input gain `speed_alt` = 23 (0 dB). Alt knobs then need to move before they
  take over again, as after Source + Pitch click.
  - Stock did this only for Csound instrument changes.
  - Pd patches got whatever the last Csound instrument had saved, because Pd mode never saves alt values.
- **Pitch CV:** the firmware's one-pole goes from 0.33 to **0.95** per filter step. The filter steps twice per
  5.3 ms poll pass, so a jump should settle in about 1 pass (~5 ms) instead of ~7 (~37 ms, measured on stock).
  Steady CV is still held by the hysteresis and stability gate (±1 LSB noise gives 0 output changes in both).
- **`neb_options.txt`** in the stick root (optional, copied at each instrument load, kept when the stick has none):
  ```
  pitch_coeff = 0.95     # 0.05-1.0 per filter step (2 per poll pass); 0.33 = stock glide
  sel_page_steps = 4     # 1-16 Pitch encoder steps per selector page (4 = one detent, usually)
  pd_alts_at_load = 0    # 1 = also send the (default) alt values once when a Pd patch connects
  ```
- **Pd externals:** `.pd_linux`, `.l_arm` and `.l_arm64` files in the stick root are copied next to the patches, so
  `[clds~]`-style objects load (as in Technobear's firmware).
- **Hidden helper patches:** `.pd` files starting with `_` are copied but not listed (use them as abstractions).
- **After a firmware update:** the first start restores calibration, last instrument, alt settings and
  `neb_options.txt` from the replaced tree (`/home/alarm/backup/old`).
  - The calibration is restored only if the old file is valid.
  - It runs on the first start of a new tree only, whatever the time says (the clock is not real). Holding Pitch
    at power-on on that one boot is overridden by the restore. Recalibrate on any later boot.
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
python firmware/tests/test_firmware.py   # 28 logic tests: stock modules via firmware/tests/py2shim.py, hardware stubbed
python firmware/tests/test_fwbuild.py    # 15: base repack == unit tree, Pi 4 changes kept, guards, --import-device
python tools/fwbuild.py --check          # guards only
python tools/fwbuild.py                  # -> firmware/dist/v2_1_2_uf1/ (+ neb_candidate.* for the on-module check)
python tools/fwbuild.py --from base      # the base, repacked (a revert zip for the base)
python tools/fwbuild.py --import-device firmware/device_image/neb_update.zip --source-name sd-image-2026-11-09
```
- `--import-device` makes a unit tree the base. Each file that both uf1 and the unit changed gets a three-way merge
  (`git merge-file`, previous base as ancestor):
  - clean merges are taken;
  - a conflict is written with markers to `firmware/dist/merge/<path>` and nothing else is written;
  - edit that file until no markers are left, then run the import again, which takes it.

  Runtime files and the `.pyc` files Python 2 wrote on the unit are left out.
- Edit `firmware/src` only. `firmware/base` is the reference tree.
- `firmware/` is stored without line-ending conversion (`.gitattributes`).
- The tests run with bytecode writing off, so `firmware/src` gets no new `__pycache__`.
- Desktop tests can't prove Python 2.7 compatibility. Use the on-module precheck in `fw_backup.instr`: a
  micromamba-based local Python 2.7 install was blocked by the session's permission rules.

### Hardware test (owner, after the installable build)
1. Unplug all CV/gate cables. Put `neb_update.zip` in the stick root and boot. Expect the update animation and
   reboots, and "Firmware updated to: v2_1_2_uf1" in `neb_log.txt`.
2. The last instrument and calibration should be back (the restore). V/oct should track as before. Play a Pd patch
   and a Csound instrument.
3. Selector (your Pd bank has 11 files = 3 pages):
   - Speed CCW/middle/CW gives user Csound / factory / Pd;
   - Pitch turn steps through the pages, one detent each, and the Pitch LED colour shows the page. If it feels too
     fast or slow, put `sel_page_steps = 8` (or 2) in `neb_options.txt`;
   - lit buttons = patches on that page, bright = the running one; pressing a lit button loads it at once, a dark
     one does nothing;
   - Pitch or Speed click leaves without loading;
   - power off and on while on a file of page 2 or 3: the selector should open on that page.
4. `99_pitchlog` again: Pitch clicked to centre, a 0 V ↔ 1 V square into Pitch CV, press Reset, wait for the end
   beeps. Then 08_resonator by ear on big V/oct jumps.
5. Revert drill: the Stage 0 backup zip goes back to v2_1_2. Then reinstall uf1. (The STOCK card is the faster
   way back, but this proves the USB path from uf1.)

## Status
- 2026-11-09: Stage 0 tools written and offline-tested. **Not yet run on hardware.**
  - `fw_backup.instr` was tested in Csound 6.09.1 with `system_i` stubbed (silent / ok beeps / fail tone). Its shell script ran in a fake module tree: backup and layout correct, no overwrite on a 2nd run, a corrupt backup gives the fail tone.
  - `99_pitchlog` was tested with a simulated firmware stream. At 4 ms polls, 90 % of a jump takes 6 polls at coefficient 0.33 and 1 poll at 0.95.
- 2026-11-09: uf1 written on the provisional GitHub base.
  - 26 logic tests and 10 build tests pass. The batched FUDI stream was checked against real Pd 0.57.
  - `fw_backup.instr` gained the on-module Python 2 precheck (its shell path is tested here; python2 itself runs only
    on the module).
  - **Not compiled with Python 2 yet. Not installed.**
- 2026-11-09: SD imaged (Stage 0 step 1) and read offline. The unit's tree, which includes Qu-Bit's Pi 4 changes, is
  now the base. uf1 was rebased with a three-way merge.
  - 27 logic tests and 15 build tests pass.
  - `pdsender.connect()` now closes a failed socket. On Windows, a timed-out attempt could otherwise connect later,
    which made the retry test fail.
  - Installable `neb_update.zip` sha256 `802db7e19d695a891b75b45b210bc0e6e38fcbde547c3451fcb9928da7c4682d`.
  - **Still not compiled with Python 2. Not installed.**
- 2026-11-10: Stage 0 run on the module (results above). Clock-free `ufmigrate`, past file dates in `fwbuild`,
  `fw_backup` beeps include the precheck (shell logic tested in WSL in 4 scenarios).
  - 28 logic tests and 15 build tests pass.
  - uf1 `neb_update.zip` sha256 `1b761767d1a4dfedfbf978c5c3b4d42d7b14d6820ff0d4d4043db2abe0c3b81d`.
  - **Not installed yet.**
- 2026-11-10: selector redesigned to the owner's spec (Pitch = page, a button loads its patch at once, Pitch or Speed
  click leaves). 30 logic tests and 15 build tests pass.
