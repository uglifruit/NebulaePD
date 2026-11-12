bt_keyboard - the Nebulae as a Bluetooth keyboard (guide: docs/STORYTELLER.md in the NebulaePD repo)

Keep this folder in the stick root, next to bt_storyteller.instr and bt_test.instr.

  btkbd          the Bluetooth keyboard program (BTstack, free for personal non-commercial use)
  run.sh         starts it; the instrument copies it into the module's RAM
  narrator.py    the storyteller: turns what happens to the module into data + poetry
  phrases.py     its voice: every line it can write. Edit freely (plain text in Python lists);
                 only use letters, digits, space and . , ! ? ( ) - : % ' / ; = + [ ] < > *
  settings.txt   data lines (full / short / off), pace (seconds between lines), codas (%)
  hide_data      (optional: an empty file with this name = data off)

Written by the module:
  pairing.tlv    after pairing with your PC. Delete it to pair with a different PC
                 (and remove "Nebulae" from the PC's Bluetooth devices).
  narrator.log   what the storyteller wrote; log.txt: the Bluetooth side.
                 The three runs before are kept as narrator.log.1 .. .3 and log.txt.1 .. .3
  probe.txt, diag.txt   from bt_test

Nothing is installed on the module's SD card. Bluetooth is only on while a bt instrument is loaded.
