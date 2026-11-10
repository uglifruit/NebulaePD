# Pearls (Beads) on the Pi 4 Nebulae, in uf2

Pearls is XponentOneAudio's unofficial port of Mutable Instruments **Beads** to the Nebulae v2
(github.com/XponentOneAudio/QB_Nebulae_V2, `Code/beads_port`, MIT). It is a Csound plugin opcode (`libpearls.so`)
plus an instrument (`pearls.instr`). Clone for reading: `external/xponent_QB_Nebulae_V2` (gitignored).

**Why their firmware isn't used:**
- It is built on GitHub's v2.1.2, which lacks Qu-Bit's Pi 4 changes; they say "if yours has a Pi 4, don't install
  this yet".
- Its installer is run from `Code/scripts/startup.sh`, which our build guards never allow.

**Decided (owner, 2026-11-10):** use Pearls' plugin on our uf2, with Pearls' small firmware hooks ported in.

## Provenance (checked 2026-11-10)
- **Reproducible build.** The plugin was rebuilt from source commit `635ce93` ("Pearls 8") with `tools/build_prebuilt.sh`:
  - same compiler: `arm-linux-gnueabihf-g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`, installed in WSL with
    `wsl -u root apt-get install g++-arm-linux-gnueabihf make`;
  - Csound 6.09.1 headers;
  - the result is **byte-identical** to the published `prebuilt/armv7/libpearls.so` (sha256
    `9ccae0ddbba0ad7476e25953b7922c5d2c73983db94806ac8e9173b7df91038f`). The prebuilt is exactly the public source.
- **Upstream DSP.** The vendored Beads DSP + stmlib were compared with pichenettes/eurorack `f4cfa76` and
  pichenettes/stmlib `e3bd7c9`:
  - 43 of 51 files are identical;
  - the 8 that differ carry only additions marked "Nebulae port": reverse-grain probability, stereo spread,
    buffer read/write for load and save, a gate-output sink for EOL, pitch quantisation, and
    `BEADS_NO_HARDWARE_24K`. Each defaults to Beads' behaviour.
- **Fit with this unit:**
  - the binary is ELF32 ARM hard-float and needs only libc/libm/libstdc++/libgcc (GLIBC 2.17, GLIBCXX 3.4), all on
    the card;
  - it targets the Csound plugin API used by 6.08–6.18; the card runs 6.11, as on the Pi 3 where it was confirmed;
  - it reads the gates through `/dev/gpiomem` GPLEV0 only, at the same offset on the BCM2711 (Pi 4).
- WSL build trees: `~/pearls_build` (Pearls at 635ce93), `~/mi_upstream` (MI's repositories).

## Plan
1. **Firmware hooks** from Pearls' fork, ported into uf2. Inactive for other instruments; about 120 lines:
   - `controlhandler.py`: `ignoregate`, `eol,engine`, `ignorealtgate`;
   - `ui.py`: Pearls LED feedback (`ui,pearls`);
   - `settings.py`: the `new_val` crash fix.
2. **A private plugin folder.** `/home/alarm/csound_plugins` holds links to every stock plugin in
   `/usr/lib/csound/plugins64-6.0` plus the checked `libpearls.so`, and uf2 points Csound there with
   `OPCODE6DIR64`.
   - Csound's own folder is never written, so a stock revert leaves a stock system.
   - Pearls' `boot_install.sh` copied into the shared folder; we don't.
3. **Install from the stick** (`fileloader`):
   - a new `libpearls.so` is first checked with Pearls' `verify_plugin.py` approach: it must load and run in the
     module's Csound from a temporary folder;
   - only then is it linked in, and `pearls.instr` added to the user bank.
4. **Tests:**
   - the plugin in Csound on the PC, through Pearls' harnesses;
   - our firmware tests;
   - then the owner's hardware test.
