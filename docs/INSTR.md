# Csound `.instr` development notes

Sources: `reference/Nebulae_Development_Reference.pdf`, upstream `Code/nebulae/conductor.py`, `Code/instr/*`.
Desktop check: `python tools/instr2csd.py file.instr out.csd --set pitch=0.6 ...` builds the same orchestra the module's
`conductor.py` builds, then `csound -n out.csd` compiles and runs it offline (tested with Csound 6.18.1 portable).
## Csound version on the module: 6.09.1
- Firmware updates (`neb_update.zip`, really a tar.gz) only replace `Code/` (Python, instr, scripts). Csound comes
  from the factory OS image and is never updated by firmware.
- `Code/nebulae/ctcsound.py` (the Python binding, which must match libcsound's API) is **byte-identical to the one
  released with Csound 6.09.1** (July 2017); 6.09.0 differs by 16 lines, 6.10+ by 100+. The instr tester's
  `ctcsound_linux.py` matches 6.09.0. So: v2.1.2 modules run Csound 6.09.x. Pi 4 (USB-C) units ship a newer OS
  image; their version is unconfirmed. **The owner's unit is a Pi 4** (neb_log shows 3.8 GiB RAM), so for this unit
  6.09.1 is a lower bound / best guess, not a fact. Firmware updates would still install the 6.09.1 `ctcsound.py`
  (it is a ctypes binding and works across 6.x), so the file on the module does not prove the library version.
- Avoid opcodes/syntax added after 6.09 (check the "New in version" note in the Csound manual).
- `node tools/run_csound609.js out.csd 10` runs a CSD in Csound 6.09.1 (Emscripten build, float samples) the way the
  module does and reports `compileOrc` result, peak and NaN count. Setup: unzip `csound-emscripten-6.09.1.zip` from the
  Csound 6.09.1 GitHub release into `tools/csound609/`. Not the real ARM/ALSA runtime, but the same parser and opcodes.

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

## How a bad instrument becomes a boot loop (from upstream nebulae.py)
1. The selected bank/instr is saved to `Code/config/bootinstr.txt` and reloaded on every start.
2. `start()` calls `compileOrc()` **without checking the result**, then starts the performance thread.
3. If Csound fails (compile error, crash, perf thread ends), `run()` exits / Python dies, systemd restarts
   `nebulae.service`, which reloads the same instr -> loop every few seconds (boot LEDs each time).
4. Recovery: replace the file's contents with a working instrument under the **same name** (owner-verified), or remove
   it so `nebulae.py` falls back to the factory granular looper. `neb_log.txt` on the USB gets a new block per restart.

## Reading neb_log.txt
Each start of the Nebulae app (`nebulae.py` -> `logger.spill_basic_info`) appends a block: VERSION, VERSION_DATE, CPU/GPU
temp, `free -h`. The boot script (`checkfirmware.sh`, on the OS image, not in the repo) adds the
"mandatory_files ... reversion request" lines once per service start. Instrument changes from the selector add a
VERSION block without the mandatory/reversion lines.
- No RTC: the clock restarts from a saved time at each cold power-on, so timestamps jump **backwards** at power cycles.
- `buff/cache` ~88-90 MiB means a fresh kernel (cold boot). ~180+ MiB means the same kernel kept running.
- A boot loop shows as blocks every ~10-15 s, each with mandatory/reversion lines, and buff/cache staying ~185 MiB:
  that is the **service** restarting (app crash -> systemd restart), not the Pi rebooting.
- Csound's own error messages are **not** written here; they go to the systemd journal (`journalctl -u nebulae`).

## Known issues
- **GENDYN (`Instruments/GENDYN/gendyn.instr`) boot-loops on the owner's unit.** Investigation (2026-10-18):
  - Compiles (`compileOrc` = 0) and runs 30 s cleanly in **Csound 6.09.1** (the module's version) at default and
    extreme knob settings: peak ~0.5, no NaN. Same in 6.18 for 60 s. So it is **not** a parse error or a DSP blow-up
    in Csound itself, and the "old parser" theory below is now unlikely.
  - DSP is sound;
    `gendy` is built into libcsound, so not a missing opcode; its `knum` divide-by-zero guard exists back to 6.07.
  - So the failure is specific to the module's environment. Constructs used **only** by GENDYN (not by working
    instruments): `/* */` header with UTF-8 accents (`Generation`), global-space `gk.. init` lines plus a non-global
    `initcps init 13` in instr 0, a `\` line continuation in the `gendy` call, and `port` writing into its own global.
  - `instr/demos/gendyn_fixed.instr` removes all of them (plus: stereo `outs`, min/max frequency ordered, nebconfig).
    **Tested on hardware 2026-10-18: also boot-loops.** So the syntax quirks are ruled out; what both files share is
    the `gendy` opcode itself (plus butterlp/balance). Next suspect: `gendy` on the module's Csound build/ARM.
    Parked. (Original note: if it works and the cause matters, bisect by re-adding one construct at a time.
  - Owner's neb_log (2026-10-18) shows the loop: restarts every ~15 s with buff/cache ~183-188 MiB, so the Pi stays up
    and the Nebulae service restarts. That fits a crash or exit of the Python/Csound process during instrument start.
  - Remaining suspects are the real-time side: ALSA/realtime on ARM (double-precision build), CPU/underruns, or
    something in the Python app. Definitive answer needs the module's log: SSH in and run
    `journalctl -u nebulae -b` (or `-b -1` after a restart), or check `Code/log/formattedcsd.txt` and `neb_log.txt`.
  - Original also: mono `out` (left only), pitch above speed inverts min/max frequency (still stable in 6.18).
