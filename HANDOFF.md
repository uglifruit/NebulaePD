# Handoff — NebulaePD (for a new Claude instance)

Last updated 2026-10-18. Read this first, then `docs/PROTOCOL.md`, then the doc for whatever you're touching.

## 1. What this is
- **Goal:** Pure Data instruments (later Csound `.instr`, maybe SuperCollider) for the owner's **Qu-Bit Nebulae V2**
  Eurorack module.
- **Hardware:** Pi 4 revision (USB-C, 4 GB), firmware **v2.1.2**.
- **Repo:** private GitHub `uglifruit/NebulaePD`, branch `main`. Local path `C:\Users\andyu\Documents\NebulaePD`
  (Windows 10; Git Bash and PowerShell both available).
- **The owner:**
  - tests every patch on real hardware;
  - names files on the USB root with numeric prefixes (`01_…`), because the instrument selector is alphabetical
    across 5 buttons;
  - wants design choices offered as options with a recommendation, and often answers with a variant of their own;
  - after changes: commit, update the user guide and docs, and push when asked.

## 2. Status
| Item | State |
|---|---|
| `patches/03_gloop.pd` | Gloop-style 4-head looper. **Confirmed working on hardware.** User guide: `patches/03_gloop_README.md`; design: `docs/GLOOP.md` |
| `patches/04_glitch.pd` | Port of the owner's Workshop Computer #57 Glitch (clock-synced beat-repeater, Glitch + Stutter modes). Offline-tested, **awaiting hardware test**. Guide: `patches/04_glitch_README.md`; design: `docs/GLITCH.md`; builder `tools/glitch.py` |
| `patches/02_echo.pd` | Stereo tape echo + freeze. Offline-tested, no hardware report |
| `patches/00_template.pd`, `01_drone.pd` | Template / demo. No hardware report |
| `instr/` | Csound template + 6 factory demos (V1 ports). `docs/INSTR.md` |
| GENDYN (`gendyn.instr`) | Boot-loops the module, and so does our rewrite `instr/demos/gendyn_fixed.instr`. **Parked by the user.** Both pass in Csound 6.09.1 and 6.18 on the desktop; suspect is `gendy` on the module's build. The next step would be SSH plus `journalctl -u nebulae` |

**Roadmap** (not started):
- Gloop effects pass: delay, reverb, bit crush, wavefold, tape saturation/hiss/age, tilt EQ. The user picked "core first".
- Optional soft limiter on the gloop output.
- Csound work.
- Possible custom-firmware LED mod. Only offered so far; the user chose stock firmware.

## 3. Repo layout
```
patches/        deliverable .pd files (one self-contained file each, copied to USB root) + *_README.md user guides
lib/            nebulae_controls.pd (netreceive 3000 -> route -> [s name]) - also embedded in every patch
sim/            sim_controls.pd (GUI sliders), send_fudi.py (TCP sender), test_*.pd (offline batch tests)
tools/gen.py    GENERATES every .pd (Canvas builder, echo/drone/template, test scenarios)  <- source of truth
tools/gloop.py  03_gloop builder (heads, writer, recorder, takeover, ui)
tools/instr2csd.py   wrap .instr into the .csd the module builds;  tools/run_csound609.js  run it in Csound 6.09.1
tools/wavpeaks.py    per-50 ms peaks of a (float) WAV - how test renders are checked
docs/           ARCHITECTURE, PROTOCOL, DEPLOY, INSTR, GLOOP
reference/      Qu-Bit dev reference PDF;  upstream/  a few MIT files copied from Qu-Bit's repo
external/       (gitignored) clones of Qu-Bit-Electronix/QB_Nebulae_V2 and TheTechnobear/NebulaePatches - re-clone if missing
tools/csound609/ (gitignored) unzipped csound-emscripten-6.09.1 from the Csound 6.09.1 GitHub release
```
**Never hand-edit generated .pd files.** Edit `tools/gen.py` / `tools/gloop.py`, run `python tools/gen.py` from the repo
root, and commit both. `.gitattributes` keeps `.pd/.instr/.csd` LF.

## 4. Nebulae facts that matter (verified from upstream source)
- **How a Pd patch is launched:**
  - The Python app (`Code/nebulae/*.py`, Python 2) runs `pd -rt -callback -nogui -audiobuf 5 /home/alarm/pd/<name>.pd`.
  - USB-root `*.pd` files are copied to `/home/alarm/pd` at boot. Audio files go to `/home/alarm/audio`.
  - The patch must turn on DSP itself: `loadbang -> delay 300 -> ; pd dsp 1`.
- **Control protocol:**
  - TCP to `[netreceive 3000]`, FUDI `name value;`.
  - **Every primary value is resent about every 1 ms, changed or not.** Use `[change]` for button edges, and ignore edges
    for about 1 s after load (stored latch states arrive straight away).
  - **Alt values (`*_alt`) are sent only while Source is held.**
  - `file` is **incremental** (0..number of audio files − 1), not 0/1. Use `filestate` (the raw button) for presses.
  - `reset` is a pulse. `freeze`/`record` latch on the rising edge. `source` latches on the falling edge, and a long hold
    enters the alt layer without toggling.
  - `speed_alt` (input gain) and `reset_alt` belong to the Nebulae itself.
  - Clicking Pitch while holding Source resets **all** alt values to defaults (`pitch_alt` default is 0).
- **Control ranges:**
  - `speed`: 0.5 = stop, 0.625 = 1× forward, 0.375 = 1× reverse (the encoder click toggles between them), ends = 4×.
  - `pitch`: click = 0.6; ×5 octaves for 1V/oct (`round(p*60)-36` semitones).
  - `pitch_alt`: an absolute 0..1 accumulator moved by the encoder in about 0.002 steps.
- **LEDs:** Pd **cannot** set any LED.
  - `ui.py` draws them all: button LEDs show each button's latch/flash state; the Speed and Pitch RGB LEDs show those
    encoders.
  - The only usable "display" is latch state. That's why 03_gloop selects the head from the Source and Freeze toggles.
- **Csound:**
  - `Code/nebulae/ctcsound.py` is byte-identical to the Csound **6.09.1** release, but firmware updates don't touch
    Csound, and the Pi 4 image is newer, so the library version on this unit is unconfirmed.
  - The orchestra wrapper is `conductor.py`; `instr2csd.py` mirrors it.
- **Boot loop mechanism:** `bootinstr.txt` remembers the last instrument. `nebulae.py` never checks `compileOrc`, and a
  crash makes systemd restart the app, so it loads the same instrument again.
  - Recovery: overwrite the bad file with a working one under the same name (owner-verified).
  - In `neb_log.txt`, a loop shows as blocks every ~15 s with buff/cache ~185 MiB: the app is restarting, not the Pi.
- **Pd version on the module: unknown.** Write for old vanilla Pd:
  - no `expr`, and no signal into `lop~`'s cutoff inlet (send floats);
  - `[*~ <arg>]` when the right inlet takes floats (argless `*~` wants a signal);
  - `[table]` rather than `[array define]`;
  - escape `,` and `;` in comments (`gen.py`'s `text()` does this);
  - write `$1` as `\$1` in generated text (Python `"seed \\$1"`); an unescaped `$1` expands at load time
    ("argument number out of range").

## 5. How to test (do this before handing anything over)
```bash
python tools/gen.py                                   # regenerate everything
PD="/c/Program Files/Pd/bin/pd.com"                   # Pd 0.57 is installed
"$PD" -nogui -noaudio -stderr -open patches/X.pd -send "; pd quit"      # load check: no output = OK
"$PD" -nogui -batch -r 48000 -stderr -open sim/test_03_gloop.pd         # scripted offline run
```
- Test builds swap `adc~` for a blip source and script control messages as `(ms, msg)` steps. See `gloop_*_test()` and
  `echo_patch(test=...)` in `gen.py`.
- Pass `wav=<absolute Windows path>` to record the output, then run `python tools/wavpeaks.py file.wav`.
- **`writesf~` drops audio in `-batch` runs.** They finish in well under a second, its disk thread falls behind, and
  WAVs come out short and time-shifted. 04_glitch tests record with `tabwrite~` into tables and save with
  `soundfiler write` at quit, which is deterministic. Older gloop and echo WAV results may have been affected.
- `pd.com -batch` is synchronous: a whole test runs in a fraction of a second.
- **WAV time 0 = DSP start = real 0.3 s.**
- Trust WAV peaks, not `env~` prints; `env~` readings misled twice.
- For gloop debugging, set `gloop.DEBUG_HEAD = n` to print a head's phase and index.
- Csound check: `python tools/instr2csd.py f.instr out.csd --set pitch=0.6 ...`, then
  `node tools/run_csound609.js out.csd 10`. It reports the `compileOrc` result, the peak and a NaN count.

## 6. Tool and environment gotchas (learned the hard way)
- The Bash tool mangles heredocs and `\\` escapes. Write scripts with the Write tool, then run them.
- Pd on Windows can't open Git-Bash `/c/...` relative paths reliably. Use `C:/Users/...` absolute paths.
- `python -I` hides user site-packages (`pypdf` and `pymupdf` are installed there). Drop `-I` for your own scripts.
- Downloads and untrusted material go in the session scratchpad, which is session-only. `tools/csound609/` holds the
  persistent Csound 6.09.1 copy.
- The GitHub MCP server failed to connect in this session. `gh` CLI works (logged in as `uglifruit`).

## 7. 03_gloop design summary (keep consistent when extending)
- **Head select:** head = 1 + Source + 2×Freeze, read from the latch states, so the LEDs show it.
- **Buttons:** Reset = restart heads; File = pause/resume the selected head; Record = rec/close/overdub;
  alt Record = clear; alt File = grid off/4/8/16.
- **Per-head knobs with takeover:** start = position, size = sub-loop size, density = jitter, overlap = pan,
  speed = rate.
- **Global:** window = crossfade, blend = dry/loop. Alt: start…overlap = head volumes 1–4, blend = degrade,
  window = wobble.
- **Pitch:** Pitch/V/oct = **global** transpose; Source+Pitch = selected head's interval. Its takeover re-baselines
  after 150 ms of silence and ignores jumps over 0.2 (the alt-reset click).
- **Engine:** stereo 2-min `table`s. The writer is an `rpole~` counter + `tabread~` old sample + degrade/overdub +
  `tabwrite~`, both restarted on each wrap by a metro (the loop is a whole number of 64-sample blocks). Each head is a
  `phasor~` with `samphold~` latching position/size/jitter at the wrap, then `tabread4~` → edge fade → vol² → pan →
  `throw~`. A new loop or Reset sends a phase reset (no frequency glide, or the phase drifts).
