# Utilities on the stick

These aren't instruments. Each one does one job, then lets audio pass (or plays a test sound).

| File | Bank | What it does | What you hear / get |
|---|---|---|---|
| **999_fw_backup** | Csound user | Backs up the module's own firmware to `neb_fwbackup/` on the stick (the revert package, first run only, never overwritten), and writes an inventory: OS, versions, packages, boot files, the hash of every firmware file. Changes nothing on the module | Audio passes through. Then every 4 s: **three high beeps** = done and verified; **one long low tone** = something failed (see `inventory_*.txt`) |
| **bt_test** | Csound user | The Bluetooth check: tests the radio chip's power and serial line (`diag.txt`), starts the Bluetooth stack (`probe.txt`), then acts as a keyboard that types "Hello from the Nebulae" every 10 s once paired | Blips while waiting to pair, a chime when connected, a low tone on failure. Files in `bt_keyboard/` |
| **ZZ_pitchlog** | Pd | Measures how the firmware delivers Pitch: Reset starts a 20 s capture of every Pitch message. Run `999_fw_backup` afterwards to copy the capture to the stick | Nothing special. Used for the timing measurements |
| **01_sctest** | SuperCollider | Checks that SuperCollider runs and every control arrives: a plucked saw | Reset plays a note |

Safe to keep on the stick. They only run when you load them.
