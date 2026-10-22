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
- **GENDYN (`Instruments/GENDYN/gendyn.instr`) boot-loops on the owner's unit**, and so does our first rewrite
  `instr/demos/gendyn_fixed.instr` (tested 2026-10-18). Root cause still unconfirmed (needs the journal, see below).
  - What is ruled out: parse errors (compiles in 6.09.1 and 6.18), the syntax quirks (`/* */` + UTF-8 header, global
    `init` lines, `\` continuation, `port` into its own global: the rewrite removed them all), CRLF (every upstream
    instr is CRLF), a missing opcode (`gendy` and `butterlp` are both in core libcsound 6.03-6.18), a `gendy` change
    between versions (`Opcodes/gendy.c` is semantically identical 6.03.2-6.18.1), `--realtime` init races (perf waits
    for `init_done`), and a clean exit (`nebulae.service` is `Restart=on-failure`, runs as root; `sys.exit()` from
    `run()` exits 0 and would not loop). So it is a **crash** (Csound segfault or a Python exception, non-zero exit).
  - Opcodes used **only** by GENDYN among all Qu-Bit instruments: `gendy` and `butterlp`. Neither can crash on
    reading of the C source, which is why the journal is needed.
  - Real bug found (2026-10-22): the hardware's Pitch range is **-0.30..1.30** (`control.py` HybridData), not 0..1.
    Pitch < 0 makes `kminfreq` negative, `gendy`'s phase runs backwards and its interpolation ramps without bound:
    peak 1028 after 8 s, 17000 after 2 min (6.09.1). ALSA output clips, so this is a sound bug, not the crash.
  - Mapping quirks in the original: `port` approaches targets from below and `gendy` truncates, so Blend at 0 gives
    `int(0.99..)` = 0 → `gendy` falls back to 20 points (a true 1 point is near-DC), and Window never reaches
    distribution 5 (expon).
  - **`instr/gendyn_orc.instr` (2026-10-22, awaiting hardware):** the gendy algorithm and the 4750 Hz Butterworth
    ported line for line from `gendy.c`/`butter.c` into a `setksmps 1` UDO (the construct the factory Granular
    Looper uses), so no `gendy`/`butterlp`. Frequencies clamped >= 13 Hz, Blend = 2-20 points (rounded), Window = 6
    equal zones, stereo out, looper's buffer config. Offline: same RMS/zero-crossing/centroid statistics as the
    original over 60 s, peak <= 0.73 at every extreme, no NaN. CPU ~3.5x the original (~13% of a desktop core in
    wasm). If it plays, `gendy` (or `butterlp`) on the module's build was the culprit. If it also loops, the cause is
    outside the DSP: capture the log.
  - Original also: mono `out` (left only).

## Capturing the crash log (no SSH): `instr/diag_log.instr`
`nebulae.service` runs as root and Csound/Python errors go to the systemd journal, which is in RAM (`/var/log` is
tmpfs) and survives service restarts but not power-off. `diag_log.instr` uses `system_i` (plugin `system_call`) to
mount the stick and write `neb_diag.txt`: service journal, `dmesg`, Csound/OS versions, `checkfirmware.sh`, then beeps
at ~10 s. Procedure: let the bad instrument boot-loop a few times, **don't power off**, replace the looping file on the
stick with `diag_log.instr` under the **same name**, plug it back in; the next service restart loads it. No beep =
`system_i` missing on that build. The shell script avoids `$` and `;` (Csound macro/comment characters); verified in
6.09.1 that the string arrives intact (wasm has no `system_i`, so only the module can run it).
`node tools/run_csound609.js file.csd secs out.wav` also writes a stereo float WAV of the render.
