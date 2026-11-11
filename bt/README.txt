bt_keyboard - the Nebulae as a Bluetooth keyboard (docs/BLUETOOTH.md in the NebulaePD repo)

Keep this folder in the stick root, next to bt_test.instr.

  btkbd         the Bluetooth keyboard program (BTstack, free for personal non-commercial use)
  run.sh        starts it; the instrument copies it into the module's RAM
  probe.txt     written by the module: what it found about its Bluetooth
  log.txt       written by the module: what happened last time
  pairing.tlv   written by the module after pairing with your PC. Delete it to pair with a different PC
                (and remove "Nebulae" from the PC's Bluetooth devices).

Nothing is installed on the module's SD card. Bluetooth is only on while a bt instrument is loaded.
