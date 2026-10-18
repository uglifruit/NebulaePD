# Qu-Bit Nebulae V2 — architecture, limits, protocols (for Pure Data developers)

Sources: `reference/Nebulae_Development_Reference.pdf` (official), and the
[QB_Nebulae_V2](https://github.com/Qu-Bit-Electronix/QB_Nebulae_V2) repo (MIT). Items marked **(unverified)** are
inferred or not stated by Qu-Bit; confirm on hardware.

## Hardware
- Raspberry Pi compute module inside; boot config sets ARM 1200 MHz, onboard audio off, I2C/SPI/I2S on
  (`Code/localfiles/config.txt`). `sys_opt.sh` pins the CPU governor to `performance`.
- Audio: I2S codec, stereo in / stereo out, 48 kHz. Two hardware variants: wm8731 (6-channel ADC) and
  pcm5102a (8-channel ADC).
- Controls: MCP3208 SPI ADC (pots + CV), GPIO gate/switch inputs, shift registers + LED driver, rotary encoders.
- **No CV outputs.** One gate/EOL pulse output (GPIO 16) — not controllable from Pd yet.
- OS: Arch Linux ARM; user `alarm`. Pd Vanilla installed. Pd version **(unverified)**.

## Facts from the v2.1.2 user manual (`reference/Nebulae_v2.1.2.pdf` if copied)
- 20HP, 48 kHz / 24-bit, true stereo I/O, **10 Vpp** in (AC-coupled) and out. Knobs/CV: **12-bit**. CV range -5..+5 V.
- Gate thresholds 0.4 V. **Pulse out = 5 V gate** (default instrument: fires on loop reset).
- Latest hardware revision is a **Pi 4** (USB-C port); older units are earlier Pis -> budget CPU for the slowest.
- **75 MB** of audio loaded total from USB (files beyond that are skipped); wav/flac/aif, any rate (resampled to 48k).
- USB must be FAT32; files must be in the **root** of the drive. `neb_log.txt` is written to the drive at boot.
- Filesystem is read-only most of the time (confirmed by manual) -> do not rely on writing files from Pd.
- Pi 4 variant: manual says no firmware update needed.
- Source+Speed = hardware input level (so `speed_alt` is not yours). Source+Pitch click = restore all secondaries.
- Technobear's patches (`external/NebulaePatches`) show a working PD pattern: `netreceive 3000`, `loadbang -> ; pd dsp 1`,
  and a custom ARM external (`clds~.pd_linux`) shipped alongside the .pd. SuperCollider needs his custom firmware.

## Software stack
```
 hardware (ADC/GPIO/encoders) ──► Python control app (Code/nebulae/*.py, Python 2-era)
                                        │  controlhandler.py: smoothing, alt-mode, pot pickup
                                        │  pdsender.py: TCP socket → localhost:3000, "name value;"
                                        ▼
                                 Pd: pd -rt -r 48000 -nogui <patch>   (scripts/run_pd_patch.sh, via sudo)
                                        │  [netreceive 3000] in YOUR patch
                                        ▼
                                  codec audio I/O  (adc~ / dac~)
```
- Instruments are either Csound `.instr` files or Pd patches, chosen from the instrument selector's Pd bank
  (see `docs/DEPLOY.md`). The older dev PDF said PD needed a non-default .instr loaded first; v2.1.2 removed that.
- When in Pd mode, Csound is muted and the Python app streams every primary control as a text message.
- Pd runs with `-rt` (realtime priority) at 48 kHz, no GUI. Block size / audio buffer / latency **(unverified)**.
- DSP: with `-nogui` something must turn DSP on. Technobear's clds.pd uses loadbang -> `; pd dsp 1`; the official template does not (its file has no loadbang/dsp
  message); the launcher may. This repo's `nebulae_controls` sends `; pd dsp 1` after 300 ms to be safe.

## Control protocol (summary — details in `PROTOCOL.md`)
Plain-text FUDI over TCP port 3000 (`[netreceive 3000]`): `name value;`. The patch needs exactly one
`[netreceive 3000]` (the port is taken by the first). Official template routes each name to `[s name]`.

## Files
- USB-drive audio is copied to `/home/alarm/audio` at boot. Use `readsf~`, `soundfiler` + `[array define]`.
- `writesf~` / `tabwrite~` for recording. The filesystem is normally read-only on the Nebulae (the Python app
  remounts rw to write) **(unverified for Pd)** — record to RAM arrays or confirm the writable path first.

## Constraints to design around
| Constraint | Consequence |
|---|---|
| Raspberry Pi CPU, Pd runs single-threaded | Keep voices/grains/FFT small; test CPU on hardware; use `[block~]` sparingly. |
| Pd Vanilla only | No third-party externals unless compiled for ARM and installed (not supported officially). Avoid `expr` if the Pd version is old **(unverified)**. |
| Fixed button behaviour in Pd | No `nebconfig` for Pd: you cannot change triggered/latching modes, alt defaults or click points. |
| No pulse/gate out from Pd | Cannot drive EOL output (planned). |
| Controls arrive as discrete messages | Smooth them (`pack f 20` → `line~`) to avoid zipper noise. |
| Only 8 knobs + 5 buttons (+ alt layer, + encoders) | 20 CV-addressable params max; alt layer is pot-only (no CV). |
| No Pd mode in the Instr Tester yet | Use `sim/` in this repo to test on a PC. |

## Reference Pd instruments in upstream repo
`Instruments/PD Template`, `Durm`, `Plasma Membrane`, `ReconetC!`, `Rhythmic Chords` (copy in `upstream/` for study).
