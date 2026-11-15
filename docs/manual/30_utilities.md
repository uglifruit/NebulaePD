# Utilities on the stick

These aren't instruments. Each does one job, then lets audio pass (or plays a test sound).

| File | Bank | What it does | What you hear / get |
|---|---|---|---|
| **999_fw_backup** | Csound user | Backs up the module's own firmware to `neb_fwbackup/` on the stick (the revert package, first run only, never overwritten), and writes an inventory: OS, versions, packages, boot files, the hash of every firmware file. Changes nothing on the module | Audio passes through. Then every 4 s: **three high beeps** = done and verified; **one long low tone** = something failed (see `inventory_*.txt`) |

Safe to keep on the stick. It only runs when you load it.

**Parked (since 2026-11-15):** the Csound user bank holds 25, and it was full, so `999_fw_backup.instr` now waits
in the stick's `parked/` folder, where the selector doesn't see it. Before a firmware update, move it to the stick
root (the last instrument in the bank drops out of reach meanwhile), then move it back.

## Off the stick (since 2026-11-15)
These did their job and were taken off. To use one again, copy it back to the stick root: `instr/bt_test.instr` as `bt_test.instr`, `patches/99_pitchlog.pd` as `ZZ_pitchlog.pd`, `sc/01_sctest.scd` as is.

| File | Bank | What it does | What you hear / get |
|---|---|---|---|
| **bt_test** | Csound user | The Bluetooth check: tests the radio chip's power and serial line (`diag.txt`), starts the Bluetooth stack (`probe.txt`), then acts as a keyboard that types "Hello from the Nebulae" every 10 s once paired | Blips while waiting to pair, a chime when connected, a low tone on failure. Files in `bt_keyboard/` |
| **ZZ_pitchlog** | Pd | Measures how the firmware delivers Pitch: Reset starts a 20 s capture of every Pitch message. Run `999_fw_backup` afterwards to copy the capture to the stick | Nothing special. Used for the timing measurements |
| **01_sctest** | SuperCollider | Checks that SuperCollider runs and every control arrives: a plucked saw | Reset plays a note |
