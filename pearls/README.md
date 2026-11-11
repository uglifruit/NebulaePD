# Pearls (Beads) stick files

The two files that put Pearls on the Nebulae with our uf2 firmware. They are kept here so that a working Pearls can
always be recovered from GitHub.

| File | sha256 |
|---|---|
| `pearls.instr` | `9ed05e5feae3b9cbf93cb207b20f3614b0de514827221f2bb8f04923ba558519` |
| `csound_plugins/libpearls.so` | `9ccae0ddbba0ad7476e25953b7922c5d2c73983db94806ac8e9173b7df91038f` |

## Install
Copy `pearls.instr` **and the `csound_plugins` folder** to the stick root. The module needs uf2 or later. The first
instrument load installs the plugin, and `neb_log.txt` says `uf2: Csound plugin libpearls.so installed`. `pearls`
then appears in the Csound user bank (Speed anticlockwise). Leave both on the stick.

How to play and test it: `docs/PEARLS_GUIDE.md`.

## Provenance
- Pearls 8, by XponentOneAudio: github.com/XponentOneAudio/QB_Nebulae_V2, commit `635ce93`, `Code/beads_port/`.
  Both files are unmodified.
- `pearls.instr` is byte-identical to the file at that commit.
- `libpearls.so` (armv7, portable) was rebuilt from that commit with Pearls' `tools/build_prebuilt.sh`, and is
  byte-identical to Pearls' own prebuilt binary. See `docs/PEARLS.md`.
- This folder is marked `-text` in `.gitattributes`, so git stores the files byte-exact.

## Licence
MIT: Qu-Bit Electronix (the Nebulae v2 firmware repository, under which Pearls is published) and Emilie Gillet (the
Beads DSP and stmlib compiled into the plugin). Both notices are in `LICENSE.txt`. Pearls is unofficial and has no
affiliation with Mutable Instruments or Qu-Bit Electronix.
