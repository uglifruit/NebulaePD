# Handoff: building the rest of the instrument shortlist

Written 2026-11-14 for the next Claude instance. **Read `CLAUDE.md` and `HANDOFF.md` first.** HANDOFF.md holds the
platform facts, the test recipes and the Pd checklist (§8), but its §2 status table dates from 2026-10-22. This
file brings the status up to date and gives you the build queue.

## 1. Where things stand (2026-11-14)
- **Git:** `main` has two commits that are **not pushed**: `ca285a7` (INSTRUMENT_IDEAS) and `3b9d630` (stretch),
  plus whatever commit adds this file. Push only when the owner says so; an unrequested push was blocked once.
  `.~lock.Nebulae PD instruments.odt#` is untracked because the owner has their ODT open. Never commit it.
- **Firmware:** uf2_1 is on the module: a paged selector with Csound user / factory / Pd / SC banks, failure fallback
  for every engine, and Pearls' plugin folder. Its history and to-do list are in `docs/FIRMWARE.md`. No firmware work
  is planned for this queue.
- **stretch** (Csound, `instr/stretch.instr`) was built on 2026-11-13. It passed its offline tests (13/13 on 6.18,
  2/2 on 6.09) and is **waiting for the owner's hardware test**.
  - It isn't on the stick yet, because the stick (D:) wasn't plugged in. The file to copy is
    `firmware/dist/stage_stretch/006_stretch.instr`.
  - When the stick is back, copy that file, regenerate `manifest.txt` and `D:\nebulae_banks.txt` with
    `tools/stick_manifest.py`, and put `docs/manual/Nebulae instruments.pdf` on the stick.
- **chop** (Pd, `patches/09_chop.pd`) was built on 2026-11-14 after a full design walk-through. It passed its
  offline tests (`python tools/chop_tests.py`, 13 scenarios) and is **waiting for the owner's hardware test**.
  Stick file: `firmware/dist/stage_chop/K_chop.pd` (Pd yellow page, Record; `ZZ_pitchlog` moves to File).
- **2026-11-14, the owner (away from the keyboard): "Make auto decisions and carry on to next instruments for me to
  check."** So the builds after chop were designed without a walk-through: each design doc lists its decisions
  and the alternatives, for the owner to review before (or after) a hardware test.
- **vocoder** (Pd, `patches/10_vocoder.pd`) built 2026-11-14 that way (`docs/VOCODER.md`: 15 decisions to
  review). Offline tests pass (`python tools/vocoder_tests.py`, 10 scenarios). Stick file:
  `firmware/dist/stage_vocoder/L_vocoder.pd` (Pd yellow page, File; `ZZ_pitchlog` moves to Source).
- **topo kits** (Pd, `patches/11_topokits.pd`, a sibling: `06_topo.pd` unchanged) built 2026-11-14 the same way
  (`docs/TOPOKITS.md`). Tests pass (`python tools/topokits_tests.py`). Stick file:
  `firmware/dist/stage_topokits/M_topokits.pd` (Pd yellow page, Source; `ZZ_pitchlog` moves to Reset).
- **morph** (Csound, `instr/morph.instr`) built 2026-11-14 the same way (`docs/MORPH.md`). Tests: WSL
  `tools/morph_sim.py` 13/13 (6.18) + `python tools/morph_sim.py m609` (6.09.1). Stick file:
  `firmware/dist/stage_morph/007_morph.instr` (Csound user orange page, File; Pearls moves to the yellow page).
- **The shortlist** is in `docs/INSTRUMENT_IDEAS.md`. The owner picked it on 2026-11-13, and its catalogue
  explains why each idea fits its engine. **Platform work (BLE-MIDI, the time machine, gate out) is off the
  table for now.**

## 2. How the owner works (don't skip)
- **Design comes before building, one step at a time.** For each instrument, walk the owner through it with
  AskUserQuestion: the engine and source first, then the panel, then the buttons, then the alt layer. Finish
  with a "build it like this" summary panel.
  - Offer options with a recommendation, the recommended one listed first. The owner often answers with a variant
    of their own.
  - They get confused by selector-style control flows, so walk them through modes and states step by step.
  - The stretch walk-through took about eight questions and is a good model.
- They test on real hardware. Hand them only what passed offline, with a short checklist of what to listen for.
- **Owner-facing text:**
  - the second button is **File**, never "Next";
  - the stick's `E_echo` is our gloop, renamed Echo on purpose. Don't call it a mix-up.
- **When a build is done:** commit (with the attribution trailer from the system prompt), update the docs, the
  manual and the stick map, and say what to copy to the stick. Then stop and wait for the hardware report.
- The owner wants a cheat sheet per instrument eventually. Each new manual section should work as one: a panel map,
  then control tables, then a quick start.

## 3. The build queue
In the suggested order. Each idea's one-line pitch is in `docs/INSTRUMENT_IDEAS.md`. Below, for each: where to
start, the questions to put to the owner, and the risks. **Nothing here is decided until the owner picks it.**

### 3.1 chop (Pd): slice sequencer — **built 2026-11-14** (`docs/CHOP.md`)
`bonk~` and `sigmund~` do ship on the unit, and so does `[file glob]` (Pd 0.52.2, checked in the SD image). chop
still uses its own detector (see `docs/CHOP.md`). The notes below are what the build started from.
- **Pitch:** record a loop or load a stick WAV, slice it at its onsets, and let a step sequencer clocked by Reset
  replay the slices in a new order, with probability, ratchets, reverse and pitch.
- **Where to start:**
  - Reuse `tools/glitch.py`: `clock()` (beat-length measurement from Reset, hysteresis), `chain()`, `rnd()`, the
    `beat_source()` test source, and the `tabwrite~` + `soundfiler` recording in `glitch_patch`'s `if test:` block.
  - Recording and the buffer: `tools/gloop.py` (the writer, `press()` for primed button edges).
  - Control math: `program()`/`watched()` in `tools/resonator.py`.
- **Check first:** whether `bonk~` (and `sigmund~`) ship on the unit. **This isn't verified**: the plan assumed it.
  - Read `/usr/lib/pd/extra` (or wherever Pd 0.52.2 lives) in `SDImage/nebulae_stock_pi4.img` with WSL debugfs, as
    HANDOFF.md §4 was done.
  - If they're missing, detect onsets yourself (an `env~` rise ratio over a short window, done offline once at
    capture time), or use equal slices.
- **Loading stick WAVs is new ground for our Pd patches.** Audio files land in `/home/alarm/audio`. Vanilla 0.52 has
  `[file glob]` for listing a folder, but check that it exists in 0.52.2 before relying on it. The fallback is fixed
  file names, the way C_ReconetC on the stick does it.
- **Questions for the owner:**
  - Is the source a live grab (Record), a stick file, or both?
  - How many steps, and is the slice count fixed (8/16) or set by the onsets?
  - What sits on the knobs: per-step probability, ratchet, reverse and pitch amounts?
  - Freeze locks the pattern and Record re-rolls it, or does Record capture? There's a clash: the draft has Record
    doing both.
  - What does File do?
  - Swing on `speed_alt`, as topo does?
- **Risk:** the owner glitches drums and wants everything in time with zero added latency (see `docs/GLITCH.md`).
  Clock jitter is 1–3 ms, so keep glitch's 5 ms and 30 ms grace rules.
- **Output:** `patches/09_chop.pd` in the repo. On the stick the owner renames Pd patches to letters (`A_durm` …
  `J_resonator`), so suggest `K_chop.pd`: it's the first slot on the yellow page, ahead of `ZZ_pitchlog`.

### 3.2 vocoder (Pd) — **built 2026-11-14** (`docs/VOCODER.md`)
- **Pitch:** a 20-band channel vocoder. The left input is the modulator. The carrier is the right input, or an
  internal supersaw/noise chord on V/oct. Formant shift, envelope freeze, an unvoiced-noise band.
- **Where to start:** for bandpass banks, `bp~`/`vcf~` pairs in a `block~ 64` subpatch. Envelopes are `env~` at
  control rate, or a rectifier (`abs~` + `lop~`, with float cutoffs only, per HANDOFF.md §4).
  - Formant shift = the carrier band *k* is driven by modulator band *k + s*.
  - Freeze = sample-and-hold the band levels.
  - The CPU budget is roughly that of 07_shimmer.
- **Questions:**
  - Internal carrier types and chord shapes.
  - Band count: fixed at 20, or variable?
  - Is the formant shift on a knob or the alt layer?
  - Does Freeze hold the envelope, the carrier, or both?
  - What does Source pick: external or internal carrier?
- **Output:** `patches/10_vocoder.pd` (or the next free number). On the stick: `L_vocoder.pd`.

### 3.3 topo kits (Pd) — **built 2026-11-14** as the sibling `11_topokits.pd` (`docs/TOPOKITS.md`)
- **Pitch:** topo's patterns triggering sample kits from the stick instead of (or as well as) the synth voices.
- **The known clash:** the **Source gate jack is topo's step-1 reset, and it also toggles the Source latch**. That's
  why kit choice goes on the alt layer and not on Source. Read `docs/TOPO.md` and `tools/topo.py`: `KITS`, `voices`,
  and the `tp_snd` interpolation.
- **Questions:**
  - Should samples replace the synth voices or sit beside them (the Sound knob morphs synth → samples)?
  - The kit layout on the stick: one folder or file-name prefix per kit, with how many voices?
  - Kit select: an alt knob, or File?
  - Per-voice tune and decay for the samples?
- **Pd limits:** vanilla can't read folders unless `[file]` works on 0.52.2 (see 3.1). The fallback is fixed names
  (`kit1_kick.wav` …).
- **Output:** a new version of `patches/06_topo.pd`, or a sibling `06_topo_kits.pd` if the owner wants the original
  kept. Ask.

### 3.4 morph and scan (Csound) — morph **built 2026-11-14** (`docs/MORPH.md`)
The owner wrote "morph / scan". **Ask whether they want one (which?) or both.**
- **morph:** cross-synthesis with `pvscross` / `pvsmorph` / `pvsvoc`: one source's spectral envelope on the other
  (L↔R, or input ↔ stick file). Blend morphs between them. Freeze per side with `pvsbufread` or a frozen `pvsfreeze`,
  and `pvsarp` on V/oct.
  - Stick files arrive as tables `400+n`; copy stretch's file handling: the right channel is built at `599+n`, plus
    `giRate[]` and the source selection in instr 1.
- **scan:** scanned synthesis (`scanu` + `scans`): a mass-spring string whose shape is the waveform. The knobs are
  mass, stiffness, damping and centring; Reset strikes; audio input can excite it; V/oct sets the scan rate.
  - **`scanu` needs several function tables** (initial shape, masses, the spring matrix, centring, damping,
    initial velocity). Build them with `ftgen` in the header, and check the 6.11 argument list in the source,
    because the manual's examples vary between versions.
- **Where to start:** `instr/stretch.instr` (the structure, the nebconfig block, the gk-state globals, the instr
  1 → layers → instr 90 mix) and `tools/stretch_sim.py` (render, CPU measurement and checks). Read the gotchas list in
  `docs/INSTR.md` before writing a line. Section 4 summarises it.
- **Output:** `instr/<name>.instr`, with stick name `007_<name>.instr` (Csound user bank, orange page; it pushes
  `999_fw_backup` and the rest one place to the right). The guide goes in `docs/manual/16_<name>.md`.

### 3.5 sc_pattern, sc_follow, sc_mosaic (SuperCollider)
Details and panel sketches are in `docs/SC_IDEAS.md` §4. The recommended order is sc_pattern, then sc_follow, then
sc_mosaic.
- **Where to start:** `sc/02_sc_drift.scd` … `04_sc_cloud.scd` (the patch structure, OSC handlers and the `~nrtTest`
  switch), `sc/README.md`, `tools/sctest.py`, `tools/sc_nrt_tests.py` and `tools/sc_osc_tests.py`.
  - **Store the synth as `~nebSynth`, never `~neb.synth`.** `synth` is a built-in method on Event, so `.set` fails
    silently ("Non Boolean in test"). That cost a hardware round on 2026-11-11.
- **The runtime has:** sc3-plugins (`Tartini`, `Qitch`, `AutoTrack`, `KeyMode`, `Concat`, `JPverb`, `Greyhole`,
  `FM7`, the STK models). It has **neither the BBCut2 classes nor the mi-UGens**. The list is in `docs/SC_IDEAS.md`
  §3.
- **Latency is 32 ms and start-up takes 5–10 s.** sc_pattern doesn't care, because it schedules everything.
  sc_follow's harmonies will lag the input by 32 ms plus the tracker's delay: say so in the design walk-through.
- **Don't copy Technobear's code** (GPL-3; this repo is MIT). Take ideas only.
- **Output:** `sc/05_sc_pattern.scd`, `06_sc_follow.scd`, `07_sc_mosaic.scd`. On the stick, `05_sc_pattern` takes
  Freeze on the SC white page and pushes `31-simple` to the orange page.

## 4. Engine recipes: the condensed hard-won rules
### Pd (full detail: HANDOFF.md §4–§8)
- **The target is Pd 0.52.2:**
  - no `expr`;
  - `[table]`, not `[array define]`;
  - `wrap~` only on positive input;
  - `\$1` in generated text;
  - floats into `lop~`'s cutoff, never a signal.
- **Controls:** values arrive once per 5.3 ms poll pass whether or not they changed. Use `[change]`, and ignore
  edges for about 1 s after load. The alt values arrive only while Source is held, and uf1+ resets them on every Pd
  load. Pd can't set LEDs or the EOL output.
- **Never hand-edit a `.pd`.** Write a builder in `tools/`, register it in `gen.py`, and run `python tools/gen.py`.
  Then check `git status` to make sure the other patches didn't change.
- **Test:** record with `tabwrite~` + `soundfiler`, never `writesf~`. Use `pd.com -nogui -batch -r 48000`, one run
  at a time, then `tools/wavcheck.py`.

### Csound (full detail: `docs/INSTR.md`, gotchas)
- **The module runs 6.11.0.** The PC's WSL Csound is 6.18, and `tools/run_csound609.js` runs 6.09.1, which behaves
  like 6.11. **Test both.** They differ in ways that make an instrument silent on the module:
  - **an array element inside an expression evaluates to 0 in 6.09/6.11.** Read it into a variable first
    (`kr = gisr[kidx]`, then `kr / sr`). This bug would have silenced stretch;
  - `mincer` (and probably other table readers) doesn't correct for the file's sample rate in 6.11. Scale by file sr
    / sr yourself, and test pitch in 6.09 with a 44.1 kHz file;
  - **held notes (`p3 < 0`) with the same p1 tie into one instance.** Use fractional instrument numbers;
  - `pvsblur`'s cost grows with its time; `pvsmooth` costs the same at any setting;
  - `run_csound609.js` options: `CS609_MEM=512` for big tables, `CS609_FILES=a.wav,…` for audio files. The wasm
    build has no live input, and it prints `printks` only once.
- **Check every opcode and its arguments against the 6.11 source.** The 6.11 source tree was in a previous
  session's scratchpad
  (`C:\Users\andyu\AppData\Local\Temp\claude\1db1c8d20b9ee60c\8b530b01-9280-4082-856d-77cf178c0c4e\scratchpad\cs611`)
  and may have been cleaned up. If it's gone, download the 6.11.0 tag from GitHub into your own scratchpad.
- **A bad `.instr` can boot-loop a stock module.** uf2 now falls back to the factory looper, but still keep
  init-time work small and bounded.
- **CPU:** measure with getrusage against the factory looper (`stretch_sim.py` does this). Stretch came in at
  1.2–1.5×; aim for under 2×.
- **Running the tests:**
  - WSL: `wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/<name>_sim.py`;
  - 6.09: from Windows Python. That needs a lazy import of `resource`, which Windows lacks.

### SuperCollider (full detail: `sc/README.md`, `docs/FIRMWARE.md` Stage 2)
- The PC has SC 3.10.4 + sc3-plugins 3.10.0, the module's versions, and PC renders match the module's.
- **Test:**
  - `python tools/sctest.py check sc/x.scd` (syntax);
  - extend `tools/sc_nrt_tests.py` with offline renders and audio checks for the new patch;
  - extend `tools/sc_osc_tests.py` (live: every control read back from the synth).

### Environment
- **Bash tool:** it mangles heredocs and backslashes. Write scripts with the Write tool, then run them;
  `git commit -F - <<'EOF'` is fine.
- **PowerShell quoting is fragile:** use script files.
- **Paths and Python:** use `C:/Users/...` absolute paths for Pd. `python -I` hides pymupdf/pypdf, so drop the
  flag for your own scripts.
- **GitHub:** the GitHub MCP server fails to connect; use the `gh` CLI or `git push origin main`.

## 5. Definition of done, for each instrument
1. Design agreed with the owner, ending on a summary panel they approve.
2. Built and offline-tested in the right engine(s), with a scenario test script and a CPU figure. Csound runs in
   both 6.18 and 6.09.
3. **Docs:**
   - **Pd:** `patches/NN_<name>_README.md` + `docs/<NAME>.md`.
   - **SC:** a section in `sc/README.md`.
   - **Csound:** a design note in `docs/INSTR.md` if it taught you something.
4. **Manual:** add the section `docs/manual/NN_<name>.md`. Section numbers: 10 Pearls, 15 stretch, 20 storyteller,
   30 utilities, so slot new ones in between. Then:
   - add the instrument to the intro list and the stick table in `docs/manual/00_stick.md`;
   - rebuild with `python tools/manual_odt.py`, check the PDF pages render (pymupdf), and keep panel-map lines
     short, because long ones wrap in the PDF;
   - **never edit the owner's own `Nebulae PD instruments.odt`.**
5. **Bookkeeping:** mark the instrument built in `docs/INSTRUMENT_IDEAS.md`, then update the layout lines in
   HANDOFF.md §3, its status in §2, and this file.
6. **Stick:** stage the stick file in `firmware/dist/stage_<name>/`, or copy it to D: if the stick is plugged in.
   Then regenerate `manifest.txt` and tell the owner which button and page it lands on.
7. **Commit.** Hand over with a short hardware checklist, then wait for the report.

## 6. Don't
- Push, edit `Code/scripts/`, `Code/localfiles/` or the boot-path Python, or start firmware or platform work unasked.
- Build an instrument before its design walk-through.
- Copy GPL code (Technobear's) or another product's name or branding. Pearls and Echo are renamed on purpose.
- Trust the 6.18 render alone for a Csound instrument.
