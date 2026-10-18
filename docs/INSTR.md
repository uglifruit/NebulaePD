# Csound `.instr` development notes

Sources: `reference/Nebulae_Development_Reference.pdf`, upstream `Code/nebulae/conductor.py`, `Code/instr/*`.
Csound is **not installed** on this PC yet, so `.instr` files here are unverified until tested on hardware or via the
official Instr Tester (`Instruments/Instr Tester/Neb_Instr_Tester.zip` in the upstream repo).

## File layout
```
nebconfigbegin ... nebconfigend     optional: sr, ksmps, -B, -b, button modes, *_alt defaults
<global tables / opcodes>
instr 1 ... endin                   mandatory; runs forever. Start other instrs from it.
```
`conductor.py` generates a CSD with `nchnls=2`, `0dbfs=1`, default `sr 48000`, `ksmps 128`, and wraps your code.
Config line forms: `ksmps,64` / `-B,512` / `freeze, triggered, rising` / `density_alt, 0.5`.
Button modes: triggered, latching, momentary, incremental (needs max). Edge: rising, falling, state.

## Globals (actual names from conductor.py — the channel name differs for start/size!)
| Global | Channel | Notes |
|---|---|---|
| gkpitch gkspeed | pitch speed | 0-1; pitch clicks to 0.6, speed detent 0.375-0.625 |
| **gkloopstart gkloopsize** | start size | V2 names; V1-ports also use these |
| gkdensity gkoverlap gkblend gkwindow | same | 0-1 |
| gkfreeze gkrecord gkreset gksource gkfilestate gksourcegate gksourcebuttonstate | | button/gate state |
| gkfilesel | file | file index (limited by file count) |
| `*_alt` versions | `*_alt` | e.g. gkloopstart_alt, gkblend_alt (pots only) |
| gkeol, gksizestatus, gkrecordstatus, gkbufferlength | out channels | Csound -> Python (EOL/pulse out, UI) |
| gilen[] gichn[] gSname[] gisr[] gipeak[] ginumfiles | arrays | up to 100 files; tables start at 400 |

Stereo files: right channel table snippet is on page 2 of the dev reference (offset 599).
Pulse output: write `gkeol` (cleared by Python each control cycle).

## Gotchas
- **V1-era ports** (Drip Water, Vinyl Dust, Bowed Drone, FM Grit, Four Osc...) were written for Nebulae V1 and some
  comments/mappings (grain rate, mix, "freeze" = record) don't match V2 labels. Four Osc even reads `gkrecord` as an
  oscillator gate. Treat their control comments as stale; rely on the code.
- Many have no `nebconfig`, so they run at defaults (ksmps 128). Heavier ones set `ksmps,1`..`4` (World of Echo
  uses `ksmps,1`) - high CPU; a bad config can stall boot (see Known issues).
- Instrument load happens at boot / on reload. A bad instrument that crashes Csound can **boot-loop** the module:
  keep a known-good drive and `revert_to_factory_firmware` in mind (manual p.23). Remove the offending `.instr` from the USB
  root to recover.
- Test IO (`e_testio.instr`) is the recommended minimal template.

## Known issues
- **GENDYN (`Instruments/GENDYN/gendyn.instr`) boot-loops (reboots every few seconds) on the owner's unit.**
  Excluded from this repo and not investigated yet. Do not copy it to the USB drive.
