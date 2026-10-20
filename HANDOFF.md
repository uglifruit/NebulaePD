# Handoff — NebulaePD (for a new Claude instance)

Last updated 2026-10-20. Read this first, then `docs/PROTOCOL.md`, then the doc for whatever you're touching.
For a **new instrument**, see §8.

## 1. What this is
- **Goal:** Pure Data instruments (later Csound `.instr`, maybe SuperCollider) for the owner's **Qu-Bit Nebulae V2**
  Eurorack module.
- **Hardware:** Pi 4 revision (USB-C, 4 GB), firmware **v2.1.2**.
- **Repo:** private GitHub `uglifruit/NebulaePD`, branch `main`. Local path `C:\Users\andyu\Documents\NebulaePD`
  (Windows 10; Git Bash and PowerShell both available).
- **The owner** (GitHub `uglifruit`) is also the author of the Workshop Computer **Glitch** firmware (program 57) that
  04_glitch ports. They:
  - test every patch on real hardware;
  - name files on the USB root with numeric prefixes (`01_…`), because the instrument selector is alphabetical
    across 5 buttons. **The next instrument is `07_…`**;
  - want design choices offered as options with a recommendation (AskUserQuestion works well), and often answer with
    a variant of their own;
  - like ports to be "operationally and philosophically" faithful, but **don't copy the original's hardware limits**
    (e.g. 04_glitch's buffer is 43 s, not the WC's 2.33 s);
  - after changes: commit, update the user guide and docs. **Push only when asked** (they usually say "push").

## 2. Status
| Item | State |
|---|---|
| `patches/03_gloop.pd` | Gloop-style 4-head looper. **Confirmed working on hardware.** Guide `patches/03_gloop_README.md`; design `docs/GLOOP.md`; builder `tools/gloop.py` |
| `patches/04_glitch.pd` | Port of WC #57 Glitch: clock-synced beat-repeater, Glitch + Stutter modes. **Core confirmed working on hardware.** Pitch (transpose glitches, V/oct), Speed (pitch ramp across repeats) and slice-locked pitch-down on pass-through were added afterwards: offline-tested, **awaiting hardware**. Guide `patches/04_glitch_README.md`; design `docs/GLITCH.md`; builder `tools/glitch.py` |
| `patches/05_spectral.pd` | "Spectral Clouds+" after the owner's WorkshopSpectral (WC port of Kammerl's Spectral Clouds): random log-band gates, probability, smoothing, texture, normal/sealed freeze, plus true stereo + spread, spectral pitch (V/oct, peak-locked), band drift, gather, re-capture, tape on the alt layer. Offline-tested, **awaiting hardware** (main risk: CPU burst per hop, see `docs/SPECTRAL.md`). Guide `patches/05_spectral_README.md`; design `docs/SPECTRAL.md`; builder `tools/spectral.py` |
| `patches/06_topo.pd` | Clocked drum-pattern generator (Grids-style map, our own data) + 6-voice analog-model (808/909) drum synth; mutation (Record burst, Window auto, Speed drift), Freeze = lock, File = home. First hardware try (2026-10-20): the FM kit sounded like bleeps and Fill CCW kept playing → rebuilt (analog models, 3 kits, Fill dead zone). **Re-test 2026-10-20: much better, patterns behave as expected on hardware.** Not yet reported: per-kit sound detail, mutation/home/drift in depth. Guide `patches/06_topo_README.md`; design `docs/TOPO.md`; builder `tools/topo.py` |
| `patches/02_echo.pd` | Stereo tape echo + freeze. Offline-tested, no hardware report |
| `patches/00_template.pd`, `01_drone.pd` | Template / demo. No hardware report |
| `instr/` | Csound template + 6 factory demos (V1 ports). `docs/INSTR.md` |
| GENDYN (`gendyn.instr`) | Boot-loops the module, and so does our rewrite `instr/demos/gendyn_fixed.instr`. **Parked by the user.** Both pass in Csound 6.09.1 and 6.18 on the desktop; suspect is `gendy` on the module's build. The next step would be SSH plus `journalctl -u nebulae` |

**Roadmap** (not started):
- 05_spectral: hardware feedback. If it crackles, rebuild with `N = 1024` in `tools/spectral.py` (verified offline).
- 04_glitch: hardware feedback on Pitch/Speed/pass-through pitch-down.
- 06_topo: hardware feedback (sound balance, clock feel). Later idea from the owner: Source cycles through named sample
  kits. But the Source latch also toggles on the Source gate jack (06's step-1 reset), so reset would have to move.
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
tools/gloop.py  03_gloop builder (heads, writer, recorder, takeover, ui; press() helper)
tools/glitch.py 04_glitch builder (ui, clock, glitch, stutter, shuffle, pass_rate, writer, reader, beat_source)
tools/spectral.py 05_spectral builder (ui, tables, bands, stft: ana/pool/syn per side, tape, test_source; pickup())
tools/topo.py   06_topo builder (NODES map, KITS (3 kits); ui, pos, mapq, thr, steps, mutate, voices, test_clock)
tools/wavpeaks.py    per-50 ms peaks of a (float) WAV
tools/wavcheck.py    beats / clicks / freq / holds / spec: sample-level checks of test renders (see its docstring)
tools/instr2csd.py   wrap .instr into the .csd the module builds;  tools/run_csound609.js  run it in Csound 6.09.1
docs/           ARCHITECTURE, PROTOCOL, DEPLOY, INSTR, GLOOP, GLITCH, SPECTRAL, TOPO
reference/      Qu-Bit dev reference PDF;  upstream/  a few MIT files copied from Qu-Bit's repo
external/       (gitignored) clones of Qu-Bit-Electronix/QB_Nebulae_V2 and TheTechnobear/NebulaePatches - re-clone if missing
tools/csound609/ (gitignored) unzipped csound-emscripten-6.09.1 from the Csound 6.09.1 GitHub release
```
**Never hand-edit generated .pd files.** Edit the builders, run `python tools/gen.py` from the repo root, and commit
both. `.gitattributes` keeps `.pd/.instr/.csd` LF (the CRLF warnings on .py/.md at commit are harmless).

## 4. Nebulae facts that matter (verified from upstream source)
- **How a Pd patch is launched:**
  - The Python app (`Code/nebulae/*.py`, Python 2) runs `pd -rt -callback -nogui -audiobuf 5 /home/alarm/pd/<name>.pd`.
  - USB-root `*.pd` files are copied to `/home/alarm/pd` at boot. Audio files go to `/home/alarm/audio`.
  - The patch must turn on DSP itself: `loadbang -> delay 300 -> ; pd dsp 1`.
  - Sample rate is 48 kHz (both looper patches assume it, and both work on hardware).
- **Control protocol:**
  - TCP to `[netreceive 3000]`, FUDI `name value;`.
  - **Every primary value is resent about every 1 ms, changed or not.** Use `[change]` for button edges, and ignore edges
    for about 1 s after load (stored latch states arrive straight away). `gloop.press(..., primed=...)` does both.
  - **Alt values (`*_alt`) are sent only while Source is held.**
  - `file` is **incremental** (0..number of audio files − 1), not 0/1. Use `filestate` (the raw button) for presses.
    (Note: `controlhandler.py`'s puredata default config lists `file` as latching, so this is unverified. `filestate` is
    safe either way.)
  - `reset` is a pulse. `freeze`/`record` latch on the rising edge. `source` latches on the falling edge, and a long hold
    enters the alt layer without toggling.
  - `speed_alt` (input gain) and `reset_alt` belong to the Nebulae itself. `speed_alt` does reach Pd (0..32, 1 per
    detent, click = 23 = 0 dB); 06_topo uses it for swing (no audio input there), but the gain carries over.
  - Clicking Pitch while holding Source resets **all** alt values to defaults (`pitch_alt` default is 0).
- **Gate inputs (from `controlhandler.py`/`digitaldata.py`): no gate input stays high while a gate is held.**
  - `reset` and `sourcegate` are **triggers**: a short pulse per rising edge. **Reset is the clock input**
    (04_glitch). Its button doubles as tap tempo.
  - `freeze` and `record` **toggle** on each gate rising edge.
  - `filestate` ignores the gate jack (button only).
  - To get a held gate, use a **pot's CV jack** as a comparator (04_glitch: Start > 0.5 = gate).
  - Clock pulses reach Pd with about **1–3 ms jitter** (poll loop + TCP + block). 04_glitch ignores beat changes under
    5 ms and ends slices ~3 ms early, plus a 30 ms grace period.
- **Control ranges:**
  - `speed`: 0.5 = stop, 0.625 = 1× forward, 0.375 = 1× reverse (the encoder click toggles between them), ends = 4×.
    **The Speed value persists across instruments**, so a patch may load with Speed on a click.
  - `pitch`: click = 0.6; ×5 octaves for 1V/oct (`round(p*60)-36` semitones).
  - `pitch_alt`: an absolute 0..1 accumulator moved by the encoder in about 0.002 steps.
  - Every pot sums its own CV jack (so "CV mod" needs no extra mapping).
- **Outputs:** stereo audio only. Pd can't drive the gate/EOL output and there are no CV outs.
- **LEDs:** Pd **cannot** set any LED.
  - `ui.py` draws them all: button LEDs show each button's latch/flash state; the Speed and Pitch RGB LEDs show those
    encoders.
  - The only usable "display" is latch state. That's why 03_gloop selects the head from the Source and Freeze toggles,
    and 04_glitch shows mode/force/freeze on Source/Record/Freeze.
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
    ("argument number out of range");
  - `wrap~` only on **positive** input (old Pd's `wrap~` was wrong for negatives); `floor(z) = z − wrap~(z)`.

## 5. How to test (do this before handing anything over)
```bash
python tools/gen.py                                   # regenerate everything
PD="/c/Program Files/Pd/bin/pd.com"                   # Pd 0.57 is installed
"$PD" -nogui -noaudio -stderr -open C:/Users/andyu/Documents/NebulaePD/patches/X.pd -send "; pd quit"  # load check: no output = OK
"$PD" -nogui -batch -r 48000 -stderr -open C:/.../sim/test_X.pd                                        # scripted offline run
# 04_glitch with WAVs (any scratch dir, absolute path):
python tools/gen.py --wav C:/path/to/scratch     # writes scratch/t_{glitch,stutter,freeze,pitch}.pd -> .wav
"$PD" -nogui -batch -r 48000 -stderr -open C:/path/to/scratch/t_glitch.pd
python tools/wavcheck.py beats C:/path/to/scratch/t_glitch.wav
# 05_spectral: the same --wav run also writes scratch/s_{calib,bands,freeze,pitch,gather,tape,drift,recapture}.pd
python tools/wavcheck.py spec C:/path/to/scratch/s_pitch.wav 0.5 7 0.5      # rms, peaks, octave bands (numpy)
```
- Test builds swap `adc~` for a scripted source and send control messages as `(ms, msg)` steps. See `gloop_*_test()`,
  `glitch_*_test()` and `echo_patch(test=...)` in `gen.py`. 04_glitch's `beat_source` sends Reset pulses every 500 ms
  and a rising 440 Hz ramp per beat (odd beats 1.0, even 0.5), so "the previous beat" shows up as swapped levels.
- **`writesf~` drops audio in `-batch` runs.** They finish in well under a second, its disk thread falls behind, and
  WAVs come out short and time-shifted. **Record with `tabwrite~` into tables and `soundfiler write` just before
  `pd quit`** (see the end of `glitch.glitch_patch`). Older gloop/echo WAV results may have been affected; their
  harnesses still use `writesf~`.
- `pd.com -batch` is synchronous: a whole test runs in a fraction of a second. Run tests one after another, not in
  parallel.
- **WAV time 0 = DSP start = logical 0.3 s.**
- Check with `tools/wavcheck.py`:
  - `beats`: peaks per beat;
  - `clicks`: sample jumps; a full-scale 440 Hz sine moves ≤ 0.058/sample, so use 0.07, or lower for quiet renders;
  - `freq`: zero-crossing frequency;
  - `holds`: decimation hold lengths + bitcrush grid.
- Trust WAV samples, not `env~` prints; `env~` readings misled twice.
- For gloop debugging, set `gloop.DEBUG_HEAD = n` to print a head's phase and index.
- Csound check: `python tools/instr2csd.py f.instr out.csd --set pitch=0.6 ...`, then
  `node tools/run_csound609.js out.csd 10`. It reports the `compileOrc` result, the peak and a NaN count.

## 6. Tool, Pd and environment gotchas (learned the hard way)
- **Bash tool:**
  - It mangles heredocs and `\\` escapes. Write scripts with the Write tool, then run them.
  - Exception: `git commit -F - <<'EOF'` works for commit messages.
- Pd on Windows can't open Git-Bash `/c/...` relative paths reliably. Use `C:/Users/...` absolute paths.
- **DSP order between subpatches isn't guaranteed.** If a reader must see samples a writer wrote in the same block, add
  a dummy signal connection from the writer to the reader (04_glitch: the writer's `outlet~` goes to the reader's
  spare `inlet~`). Also beware `send~`/`receive~` mixing with direct paths: a one-block offset combs at partial blends.
  Use `inlet~`/`outlet~` subpatches.
- **`tabread4~`** at an integer index returns that exact sample. It clamps near the table ends, so keep a guard or
  accept a glitch at the wrap. Use a **power-of-two table** if you index with `/N → wrap~ → *N` (exact in float32).
- **`[f]` output fans out to every connection.** Use separate `[f]`s per destination, or `[v name]` for shared state.
- Message ordering: `[t b b b]` fires right to left. Everything sent in one logical instant lands in the same DSP block,
  which is how 04_glitch keeps per-slice parameters and the counter reset aligned.
- `python -I` hides user site-packages (`pypdf` and `pymupdf` are installed there). Drop `-I` for your own scripts.
- Downloads and untrusted material go in the session scratchpad, which is session-only. `tools/csound609/` holds the
  persistent Csound 6.09.1 copy.
- **GitHub:** the MCP server fails to connect; use the `gh` CLI (logged in as `uglifruit`). Plain `git push origin
  main` works. Reading another repo's raw file: `gh api repos/OWNER/REPO/contents/PATH -H "Accept:
  application/vnd.github.raw"`.

## 7. Design summaries (keep consistent when extending)
### 03_gloop
- **Head select:** head = 1 + Source + 2×Freeze, read from the latch states, so the LEDs show it.
- **Buttons:** Reset = restart heads; File = pause/resume the selected head; Record = rec/close/overdub;
  alt Record = clear; alt File = grid off/4/8/16.
- **Per-head knobs with takeover:** start = position, size = sub-loop size, density = jitter, overlap = pan,
  speed = rate.
- **Global:** window = crossfade, blend = dry/loop. Alt: start…overlap = head volumes 1–4, blend = degrade,
  window = wobble.
- **Pitch:** Pitch/V/oct = **global** transpose; Source+Pitch = selected head's interval. Its takeover re-baselines
  after 150 ms of silence and ignores jumps over 0.2 (the alt-reset click).
- **Engine:**
  - Stereo 2-min `table`s.
  - The writer is an `rpole~` counter + `tabread~` old sample + degrade/overdub + `tabwrite~`, both restarted on each
    wrap by a metro (the loop is a whole number of 64-sample blocks).
  - Each head is a `phasor~` with `samphold~` latching position/size/jitter at the wrap, then `tabread4~` → edge
    fade → vol² → pan → `throw~`.
  - A new loop or Reset sends a phase reset (no frequency glide, or the phase drifts).

### 04_glitch (full detail: `docs/GLITCH.md`)
- **Buttons and gates:** Reset = clock; Source = mode (Glitch/Stutter); Record = Force; Start > 0.5 = gate;
  Freeze = freeze.
- **Knobs:** size = division; density = probability (glitch+reverse / drift); window = X (degrade amount / shuffle
  prob); overlap = Y (degrade prob / repeat prob); blend = dry/wet.
- **Pitch/Speed:**
  - Pitch = transpose the glitched slices, live (V/oct).
  - Speed = per-repeat ramp of k·step semitones. step: left click −3 (end −12); centre to the right click 0; past it,
    up to +12.
  - Pass-through with Pitch < 0 is slice-locked pitch-down (reads from the write head, zero latency at each slice
    start). Pass-through with Pitch > 0 stays live.
- **Engine:**
  - 2^21-sample circular stereo buffer, written with freeze-as-write-back.
  - Clock edge → beat L (hysteresis) → `snapshot~` write position → freeze-aware `v` → slice geometry → `[delay]`
    slice chain.
  - Each boundary sends B/D/dec/dmul/q, then `gt_slice`. `pass_rate` routes the slice (glitched / slice-locked /
    live) and sets the rate.
  - Reader: time counter + integrated rate counter → decimate → wrapped index → `tabread4~` → bitcrush → fades →
    wet gate.

### 05_spectral (full detail: `docs/SPECTRAL.md`)
- **Knobs:** density = probability; size = bands 4..128; window = smoothing; overlap = texture; start = re-roll rate
  (CCW = Reset only); speed = drift (barber pole, 0.5 = still); pitch = spectral pitch V/oct; blend = dry/wet.
- **Buttons:** Reset = re-roll; Freeze = freeze; Source = sealed; Record = gather; File = re-capture.
- **Alt layer:** start = spread; size = gather decay; window/overlap/density/blend = tape time/feedback/wow/mix.
  Alt values apply only after the knob moves (`pickup()`).
- **Engine:**
  - `block~ 2048 4` (latency N − 64 samples, measured; the dry is delayed to match).
  - ana: `rfft~`, magnitude, phase via an atan cubic with `clip~` steps (no `atan2~`/`>~`), true frequency, then the
    write-back store M/F/P. P is stored frame-centred (−k/2).
  - pool1..4: max-pooled argmax copies, `switch~`ed on only when pitched.
  - syn: unpitched = the store. Pitched = peak-locked: loudest bin near k/r, window-kernel magnitude, shared centred
    phase, accumulator at r·F, reseeded 40 ms after Pitch settles.
  - Band gains: control-rate `[pd bands]`, one 128-band `until` pass per hop, threshold one tick late.
    Mask = `sp_eff[n·wrap(sp_L + drift)]`.
- **New Pd lessons:**
  - a reblocked subpatch's latency is N − 64;
  - argless `switch~` inside a reblocked subpatch inherits its block (period 1), so it can turn parts off cheaply;
  - `tabread~` accepts `set <table>` to switch tables at run time.

### 06_topo (full detail: `docs/TOPO.md`)
- **Buttons:** Reset = clock (one 16th per pulse); Source gate jack (`sourcegate`) = back to step 1; Freeze = lock;
  Record (any latch change) = mutate burst; File short = recall home, held 1 s = store home.
- **Knobs:** start/size = map X/Y; density = fill; overlap = chaos; window = auto-mutate; blend = Sound (kit morph);
  speed = drift (still between the clicks); pitch = tune. Alt: fill offsets K/S/H/P, window = length 4/8/16/32 (odd meters only via Source-gate resets), blend = decay;
  alt Speed (`speed_alt`) = swing, 23 = straight, ±8 = 12/8 (only after it moves). pitch_alt is unused. Sound past
  noon also fades in a crunch bus (drive/clip, bit-crush, sample-rate reduction).
- **Engine:**
  - The map is `tp_map` (25 nodes × 4 lanes × 32). `[pd mapq]` is a synchronous bilinear query (`s tp_q` → `v tp_qr`).
  - Mutations live in `tp_off`; a move that wouldn't be heard becomes a flip.
  - The voices are analog models (sine kick with sweep + click + drive, two-mode snare + noise, burst clap, 808
    six-square metal hats, tom). They have exponential envelopes from the `tp_exp` table and two round-robin halves
    each (click-free phase reset). Params come from `tp_snd`, interpolated between 3 kits at each hit.
- **Test lesson:** an action in pattern cycle k is only fully visible in cycle k+1; space test actions two cycles apart.

## 8. Starting a new instrument (checklist)
1. **Name:** `patches/07_<name>.pd`, with the numeric prefix for the selector.
2. **Builder:** a new `tools/<name>.py` with `<name>_patch(Canvas, controls_canvas, test=None)`. `tools/topo.py` is
   the most recent example (`trig()` action lists, `setv()`/`vadd()`/`vmul()` for `[v]` arithmetic); `tools/spectral.py` has
   the `op()`/`fl()`/`lerp()`/`step()` signal helpers and `pickup()` for alt knobs.
   - Embed `controls_canvas()` as `[pd nebulae_controls]` (it also turns DSP on).
   - Use a unique send prefix per instrument (gloop `gl_`, glitch `gt_`).
   - Reuse `gloop.press()` for primed button edges, and the `chain()`/`rnd()` helpers in `glitch.py`.
3. **Register in `tools/gen.py`'s `__main__`:**
   - write `patches/07_<name>.pd`;
   - write `sim/test_07_*.pd` from `<name>_*_test()` scenario functions (`(ms, msg)` steps);
   - extend `--wav`.
4. **Test harness:** copy `glitch.glitch_patch`'s `if test:` block (tabwrite~ + soundfiler recording) and a scripted
   source like `beat_source`.
5. **Verify:**
   - Load check (no output).
   - Batch runs + `tools/wavcheck.py`.
   - Make sure the other patches are unchanged by builder edits (`git status`).
6. **Docs:**
   - `patches/07_<name>_README.md` (user guide: panel map, knobs, buttons, quick start, differences);
   - `docs/<NAME>.md` (design);
   - this file's §2 status row, §3 layout and §7 summary;
   - update `CLAUDE.md` if the builder list changes.
7. **Commit** with the attribution trailer. **Push** when the owner asks.
