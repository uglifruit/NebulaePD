# Handoff — NebulaePD (for a new Claude instance)

Last updated 2026-10-22. Read this first, then `docs/PROTOCOL.md`, then the doc for whatever you're touching.
For a **new instrument**, see §8. **The current status and the build queue (2026-11-14) are in
`docs/NEXT_BUILDS.md`**; it replaces the §2 table below where they differ.

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
    across 5 buttons. **The next instrument is `09_…`**;
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
| `patches/07_shimmer.pd` | Strymon-style shimmer reverb (owner's reference: BigSky/blueSky): 8-line FDN + 2-voice pitch shifter in the loop (or before it: Source = Pre), tank mod → ensemble chorus, freeze, swell, duck, clear. Offline-tested (RT60, cascade, freeze hold, 60 s runaway, clicks), **awaiting hardware**. Guide `patches/07_shimmer_README.md`; design `docs/SHIMMER.md`; builder `tools/shimmer.py` |
| `patches/08_resonator.pd` | ECHON-style **4-voice** exciter → pitched delay-line resonator per voice (oldest-note stealing; each note latches its pitch at the strike + 10 ms catch; mono voices panned; block~ 16, damping/DC-blocker phase-compensated tuning, T60-calibrated decay, invert, freeze) → BBD-style stereo delay (glide, wobble, ping-pong, File-held hold). V/oct routing modes Coupled / Res only / Exc only on a short File press. Audio input as exciter (Source). v1 (one voice) was played on hardware 2026-11-07: good except V/oct jumps glided. The 4-voice version (2026-11-10, after the owner's firmware Pitch change) is offline-tested (0.00 c tuning, T60, chord + clean steal, pitch latch, 60 s runaway), **awaiting hardware**. Guide `patches/08_resonator_README.md`; design `docs/RESONATOR.md`; builder `tools/resonator.py` |
| `patches/09_chop.pd` | Slice sequencer (designed with the owner 2026-11-14): Record grabs 1/2/4 clocked bars, File loads stick WAVs; own onset detector (sample-refined) slices at the hits, grid fallback; Reset = beat clock (free-runs, phase-locks, step 1 after a gap), Source = step 1; per-hit dice for shuffle, hits, ratchet, reverse, pitch jumps, stutter; Freeze holds the dice. Offline-tested (`tools/chop_tests.py`, 13 scenarios incl. the unit's own WAVs), **awaiting hardware**. Guide `patches/09_chop_README.md`; design `docs/CHOP.md`; builder `tools/chop.py` |
| `patches/10_vocoder.pd` | 20-band channel vocoder (built 2026-11-14 while the owner was away: decisions to review in `docs/VOCODER.md`): left = modulator, carrier = internal 3-note supersaw chord (Start shapes, Pitch V/oct, Reset next chord, Record = Track via `sigmund~`) or the right input (Source); RBJ biquad bands (Pd's `bp~` has no zeros: unusable here); Freeze holds the envelope (File held = momentary), Speed = formant shift, Overlap = sibilance, alt gate/width/presence/whisper/leak/glide. Offline-tested (`tools/vocoder_tests.py`, 10 scenarios; CPU ≈ 07_shimmer), **awaiting hardware**. Guide `patches/10_vocoder_README.md`; design `docs/VOCODER.md`; builder `tools/vocoder.py` |
| `patches/11_topokits.pd` | 06_topo + sample kits (built 2026-11-14 while the owner was away: decisions in `docs/TOPOKITS.md`): stick files `kit<N>_<voice>.wav` (N 1-8) replace the synth voice they name; kit = alt Pitch (kit 0 = synth); tune/decay/velocity reach the samples. `06_topo.pd` is unchanged (`topo_patch(kits=True)` builds the sibling). Offline-tested (`tools/topokits_tests.py`), **awaiting hardware**. Guide `patches/11_topokits_README.md` |
| `instr/morph.instr` | Csound spectral morph / cross-synthesis (built 2026-11-14 while the owner was away: decisions in `docs/MORPH.md`): A = left input, B = stick file via `mincer` (stretch's pointer) / right input / grab of A; Blend = `pvsmorph`, Overlap = towards `pvsvoc` cross-synthesis, Window = blur, Density = mix, Pitch = transpose, Freeze holds A. Offline-tested (`tools/morph_sim.py`: 13/13 in 6.18, 6.09.1 compile + 44.1 kHz pitch), **awaiting hardware**. Stick `007_morph.instr` |
| `instr/scan.instr` | Csound scanned synthesis (built 2026-11-14 while the owner was away: decisions in `docs/SCAN.md`): `scanu`/`scans` are **not in the module's Csound 6.11** (SD image), so a 64-mass ring is updated in orchestra code at k-rate; Reset strikes, Record bows, Source = input drives it, Freeze holds the waveform, File = strike shape. Offline-tested (`tools/scan_sim.py`: 11/11 in 6.18, identical in 6.09.1), **awaiting hardware**. Stick `008_scan.instr` |
| `sc/05_sc_pattern.scd` | SC generative sequencer (designed with the owner 2026-11-14, details auto: docs/SC_PATTERN.md): 4 voices on Euclidean patterns in a scale, mutation/lock/home; Reset = 16th clock followed by a PLL and **scheduled ahead** of SC's 32 ms latency. Tested (`tools/sc_pattern_tests.py`: logic, NRT, live OSC clock), **awaiting hardware** |
| `sc/06_sc_follow.scd` | SC harmoniser (auto-designed 2026-11-14: docs/SC_FOLLOW.md): Tartini pitch + KeyTrack key + BeatTrack beat; a diatonic harmony (Pitch = interval in scale steps), held or arpeggiated (Density; Reset clocks it), 1-3 voices, Freeze hold, Record below, Source chromatic. Tested (`tools/sc_follow_tests.py` NRT, `sc_osc_tests.py`), **awaiting hardware** |
| `patches/02_echo.pd` | Stereo tape echo + freeze. Offline-tested, no hardware report |
| `patches/00_template.pd`, `01_drone.pd` | Template / demo. No hardware report |
| `instr/` | Csound template + 6 factory demos (V1 ports). `docs/INSTR.md` |
| Custom firmware | `docs/FIRMWARE.md` (its **To do** list comes first). Plan: Stage 0 → uf1 → uf2 (SuperCollider + failure fallback) → uf1b (Pd back-channel, later).
  - **Stage 0 done** (2026-11-09/10).
    - The SD card is imaged (`SDImage/`) and cloned; the original is kept as STOCK.
    - The unit's tree, which includes Qu-Bit's Pi 4 changes, is the base.
    - Poll pass measured at 5.3 ms; Pitch slew ~37 ms on stock.
  - **uf1 installed on hardware** (2026-11-10).
    - The calibration restore worked.
    - The paged selector is the owner's design: Speed = bank, Pitch = page of five, a button loads.
    - The rest: Pitch coeff 0.95, Pd retry and batching, flat loop, Pd externals, hidden `_` files, stock fixes.
  - **SC probe passed on hardware** (run 2): SC 3.10.4 + sc3-plugins (Technobear's build) play live via jackd
    (`JACK_NO_AUDIO_RESERVATION=1`).
  - **uf2 built** (47 + 15 tests, PC SC tests), **not installed yet**:
    - an SC bank one Speed step past Pd, with a blue light;
    - Technobear-compatible OSC;
    - jackd at 256 × 2;
    - the runtime installed once from the stick's `sc_runtime.tgz`;
    - for every engine, a failure falls back to factory/a_granularlooper, plus a boot guard;
    - **Pearls (Beads port, `docs/PEARLS.md`)**: a verified, reproducibly rebuilt plugin in a private Csound plugin
      folder, plus Pearls' firmware hooks.

    Files are staged in `firmware/dist/stage_uf2/`. |
| GENDYN (`gendyn.instr`) | Boot-loops the module, and so does our rewrite `instr/demos/gendyn_fixed.instr`. New try `instr/gendyn_orc.instr` (2026-10-22) drops `gendy`/`butterlp` (algorithm ported to a `setksmps 1` UDO) and fixes the negative-Pitch runaway: offline-tested, **awaiting hardware**. If it loops too, `instr/diag_log.instr` captures the journal to the USB stick without SSH. See `docs/INSTR.md` |

**Roadmap** (not started):
- 05_spectral: hardware feedback. If it crackles, rebuild with `N = 1024` in `tools/spectral.py` (verified offline).
- 04_glitch: hardware feedback on Pitch/Speed/pass-through pitch-down.
- 07_shimmer: hardware feedback (CPU on the Pi, shimmer smoothness, swell threshold vs. Eurorack levels).
- 08_resonator: hardware feedback (CPU of the block~ 16 resonator; fall back to block~ 32 if it crackles; tuning by ear, levels, auto-level feel).
  - **Hardware, 2026-11-07:** good, except big V/oct jumps glide (the firmware's Pitch slew, §4).
  - **Fix attempt `41ec4be`, reverted in `daebe62`:** two alternating voices, a settle-wait and a 40 ms pitch lag. The
    owner found it worse. The likely reason: its "stale after 4 ms" rule fired between slow poll updates, so it never
    waited, and the lag made the new note scoop 40 ms after the attack. The voice code is in that commit if needed.
  - **Custom firmware uf1 sets Pitch `filtCoeff` 0.33 → 0.95** (as Technobear did), tunable from the stick. See
    `docs/FIRMWARE.md`. Measure before/after with `99_pitchlog`.
  - **2026-11-10: rebuilt as 4 voices** at the owner's request (oldest-note stealing, a ringing note keeps its
    pitch). Hardware questions: CPU (about 2× v1, ≈ 07_shimmer offline), whether the 10 ms catch gets every sequenced
    note right, chord levels.
- 06_topo: hardware feedback (sound balance, clock feel). Later idea from the owner: Source cycles through named sample
  kits. But the Source latch also toggles on the Source gate jack (06's step-1 reset), so reset would have to move.
- Gloop effects pass: delay, reverb, bit crush, wavefold, tape saturation/hiss/age, tilt EQ. The user picked "core first".
- Optional soft limiter on the gloop output.
- Csound work.
- Custom firmware (`docs/FIRMWARE.md`): Stage 0 steps 2–5 on hardware next, then the uf1 install. uf1b adds opt-in Pd LEDs/EOL via port 3001.

## 3. Repo layout
```
sc/probe/       SuperCollider probe: run.sh + test .scd scripts (Stage 2, docs/FIRMWARE.md)
patches/        deliverable .pd files (one self-contained file each, copied to USB root) + *_README.md user guides
lib/            nebulae_controls.pd (netreceive 3000 -> route -> [s name]) - also embedded in every patch
sim/            sim_controls.pd (GUI sliders), send_fudi.py (TCP sender), test_*.pd (offline batch tests)
tools/gen.py    GENERATES every .pd (Canvas builder, echo/drone/template, test scenarios)  <- source of truth
tools/gloop.py  03_gloop builder (heads, writer, recorder, takeover, ui; press() helper)
tools/glitch.py 04_glitch builder (ui, clock, glitch, stutter, shuffle, pass_rate, writer, reader, beat_source)
tools/spectral.py 05_spectral builder (ui, tables, bands, stft: ana/pool/syn per side, tape, test_source; pickup())
tools/topo.py   06_topo builder (NODES map, KITS (3 kits); ui, pos, mapq, thr, steps, mutate, voices, test_clock)
tools/shimmer.py 07_shimmer builder (ui, reverb (FDN + shifter taps + diffuser), chorus, duck, swell, test_source)
tools/resonator.py 08_resonator builder (E/program/watched control-math compiler; ui, exciter, res, bbd, test_source)
tools/chop.py   09_chop builder (E + tables/random/loops: prog/val/when/loop; clock, seq, hit, ev, slices, ana, grab, loader)
tools/chop_tests.py  offline scenarios for 09_chop (Pd batch + log/WAV checks; renders in firmware/dist/chop_sim/)
tools/vocoder.py 10_vocoder builder (ui, ctl, carrier, bank, unvoiced, tracker);  tools/vocoder_tests.py its tests
tools/topokits.py 11_topokits kit layer (router, sample voices, loader) for topo.topo_patch(kits=True); tests tools/topokits_tests.py
tools/pitchlog.py    99_pitchlog builder + analyzer (poll rate, Pitch jump response) for logs from the module
tools/fwbuild.py     custom firmware: guards + reproducible neb_update.zip from firmware/src; --import-device
sc/01_sctest.scd     uf2 hardware-test SC patch (and a minimal Nebulae SC patch example)
sc/02..04_*.scd      SC instruments: drift (pad), strike (plucked string), cloud (granular input); guide sc/README.md
tools/sc_nrt_tests.py  offline renders + audio checks of the SC instruments in SC 3.10.4
tools/sc_osc_tests.py  live control test of the SC patches: scsender.py -> sclang -> synth values read back
docs/PEARLS_GUIDE.md   Pearls (Beads) panel + hardware test checklist
pearls/              Pearls stick files (pearls.instr + csound_plugins/libpearls.so), byte-exact, MIT
bt/                  Bluetooth keyboard: btkbd (BTstack, Pi 4 port), run.sh, tests; guide docs/BLUETOOTH.md
instr/bt_test.instr  Bluetooth stage 1-2 test (probe + hello keyboard); tools/btbuild.sh builds btkbd in WSL
instr/bt_storyteller.instr  granular looper + storyteller ears (GENERATED by tools/storyteller.py)
bt/narrator.py, bt/phrases.py  the storyteller: events -> data + poetry; tools/story_sim.py = PC test bench
bt/settings.txt      storyteller settings on the stick (data full/short/off, pace, coda); owner guide docs/STORYTELLER.md
Nebulae PD instruments.odt   THE OWNER'S instrument manual (LibreOffice; theirs to edit - don't regenerate it)
docs/manual/         00_*.md (front: selector + stick map) and NN_*.md sections appended to the owner's ODT by
                     tools/manual_odt.py -> docs/manual/Nebulae instruments.odt (+ .pdf). Update the stick map when
                     the stick changes; new instrument guides go here as NN_name.md (or "@include ../X.md")
docs/SC_IDEAS.md     Technobear's SC patches reviewed + SC instrument ideas (none built)
docs/INSTRUMENT_IDEAS.md  Pd/Csound/SC/platform proposals + the owner's shortlist (first build: stretch)
docs/NEXT_BUILDS.md  handoff for building the rest of the shortlist: status, queue, engine rules, definition of done
instr/stretch.instr  Csound time-stretch/freeze (mincer) of stick files or grabbed input; guide docs/manual/15_stretch.md
instr/morph.instr    Csound morph / cross-synthesis; guide docs/manual/16_morph.md; tests tools/morph_sim.py
instr/scan.instr     Csound scanned synthesis (own mass-spring ring); guide docs/manual/17_scan.md; tests tools/scan_sim.py
tools/stretch_sim.py offline tests of stretch (WSL Csound 6.18; rate609 = Csound 6.09 from Windows, see docs/INSTR.md)
docs/HDMI_KEYBOARD.md  feasibility: HDMI visualiser, USB/BT keyboard, tracker, live coding (none built)
tools/sctest.py      run sclang on the PC: syntax check / NRT renders of .scd files
tools/scbundle.py    SuperCollider runtime bundle (Technobear's SC 3.10.4 + Debian avahi) + the probe's stick folder
tools/wavpeaks.py    per-50 ms peaks of a (float) WAV
tools/wavcheck.py    beats / clicks / freq / holds / spec: sample-level checks of test renders (see its docstring)
tools/instr2csd.py   wrap .instr into the .csd the module builds;  tools/run_csound609.js  run it in Csound 6.09.1
docs/           ARCHITECTURE, PROTOCOL, DEPLOY, INSTR, FIRMWARE, GLOOP, GLITCH, SPECTRAL, TOPO, SHIMMER, RESONATOR
reference/      Qu-Bit dev reference PDF;  upstream/  a few MIT files copied from Qu-Bit's repo
firmware/       base/ (the unit's tree + SOURCE.txt), src/ (base + uf1 edits), tests/ (py2shim, test_firmware,
                test_fwbuild), device_image/neb_update.zip (the unit's tree packed from the SD image = base + runtime
                files; a revert package), device/ (fw_backup output, once it exists), dist/ (gitignored build output)
SDImage/        (gitignored) nebulae_stock_pi4.img, the whole SD card (docs/FIRMWARE.md has its hash)
external/       (gitignored) clones of Qu-Bit-Electronix/QB_Nebulae_V2 and TheTechnobear/NebulaePatches - re-clone if missing
tools/csound609/ (gitignored) unzipped csound-emscripten-6.09.1 from the Csound 6.09.1 GitHub release
```
**Never hand-edit generated .pd files.** Edit the builders, run `python tools/gen.py` from the repo root, and commit
both. `.gitattributes` keeps `.pd/.instr/.csd` LF (the CRLF warnings on .py/.md at commit are harmless).

## 4. Nebulae facts that matter (verified from upstream source)
- **Button names:** the panel labels are Record, **File**, Source, Reset and Freeze. In owner-facing text, always
  call the second button **File**, never "Next", even though stock firmware uses it to step to the next file.
  `PIN_NEXT`/`ADDR_NEXT`/`NEXT_GATE_PIN` in the stock code and the upstream Pearls notes say "Next"; they mean File.
- **How a Pd patch is launched:**
  - The Python app (`Code/nebulae/*.py`, Python 2) runs `pd -rt -callback -nogui -audiobuf 5 /home/alarm/pd/<name>.pd`.
  - USB-root `*.pd` files are copied to `/home/alarm/pd` at boot. Audio files go to `/home/alarm/audio`.
  - The patch must turn on DSP itself: `loadbang -> delay 300 -> ; pd dsp 1`.
  - Sample rate is 48 kHz (both looper patches assume it, and both work on hardware).
- **Control protocol:**
  - TCP to `[netreceive 3000]`, FUDI `name value;`.
  - **Every primary value is resent once per poll loop, changed or not.** Use `[change]` for button edges, and ignore
    edges for about 1 s after load (stored latch states arrive straight away). `gloop.press(..., primed=...)` does both.
  - **Poll pass: 5.3 ms mean** (median 5.5, range 4–8 ms; stock firmware, measured on the module 2026-11-10 with
    `99_pitchlog`). Every value arrives once per pass. Don't build timing logic on a 1 ms assumption (08_resonator's
    settle-wait attempt did, and was reverted).
  - **The firmware slews Pitch CV.** `control.py` HybridData applies a one-pole (`filtCoeff` 0.33), hysteresis
    0.001, octave snapping and a stability gate. The filter steps **twice per pass**, because `ui.py` re-sets Pitch
    every pass. Measured: a big V/oct jump reaches 90 % in ~4 passes (~21 ms) and settles in ~7 (~37 ms). Pitch is
    clipped to −0.30…1.30. Technobear's fork and uf1 use 0.95 ("we dont want it gliding").
  - **Alt values (`*_alt`) are sent only while Source is held.** They are stored once for all Pd patches (stock
    resets them only on a Csound instrument change), so a Pd patch sees the previous patch's alt values.
    Pd mode never saves them either. **uf1 resets the alt layer to defaults on every Pd patch load.**
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
- **More firmware facts (read while writing uf1):**
  - Selector buttons are "triggered": a press reads 1 for a pulse period over several polls. Count rising edges.
  - `FileHandler(dir, ".pd")` iterates the string's characters. Stock therefore globbed `*.`, `*p` and `*d`.
  - Its `getIndex` matched any substring of the path.
  - `check_calibration.py` crashes with a NameError after calibrating, so hold-Pitch never reset the settings.
  - The forced calibration in `update.sh` imports `control.py`/`controlhandler.py`, but the install (`tar` + `mv`)
    happens before any Python.
- **This unit (read from its SD image, 2026-11-09):**
  - 32-bit Arch Linux ARM (kernel 5.15, glibc 2.35), **Pd 0.52.2**, Csound 6.11.0, Python 2.7.18, jack2. No
    SuperCollider.
  - `/boot/config.txt` = the firmware's Pi 3-era `localfiles/config.txt`: the Pi 4 runs at 1200 MHz, not 1500.
  - Its firmware tree is **not** GitHub's v2.1.2. Qu-Bit's Pi 4 port changed `shiftregister.py` (a 10 µs sleep per
    bit), `digitaldata.py` (an incremental value updated in one step), `nebulae.py`/`controlhandler.py` (an unused
    `initial_startup` flag) and `nebulae.service`. **Never build or revert from GitHub's tree.** `firmware/base` is the
    unit's.
  - `/home/alarm/checkfirmware.sh` (outside the tree) reverts to a **v1.0.0 (2018)** factory tree if a file in
    `/home/alarm/mandatory_files.txt` is missing/empty or the stick holds `revert_to_factory_firmware`. `fwbuild`
    guards the mandatory files.
- **LEDs:** Pd **cannot** set any LED.
  - `ui.py` draws them all: button LEDs show each button's latch/flash state; the Speed and Pitch RGB LEDs show those
    encoders.
  - The only usable "display" is latch state. That's why 03_gloop selects the head from the Source and Freeze toggles,
    and 04_glitch shows mode/force/freeze on Source/Record/Freeze.
- **Csound:**
  - `Code/nebulae/ctcsound.py` is byte-identical to the Csound **6.09.1** release. The library on this unit is
    **6.11.0** (package list in the SD image). `tools/run_csound609.js` tests in 6.09.1, which is older, so it is the
    safe side.
  - The orchestra wrapper is `conductor.py`; `instr2csd.py` mirrors it.
- **Boot loop mechanism:** `bootinstr.txt` remembers the last instrument. `nebulae.py` never checks `compileOrc`, and a
  crash makes systemd restart the app, so it loads the same instrument again.
  - Recovery: overwrite the bad file with a working one under the same name (owner-verified).
  - In `neb_log.txt`, a loop shows as blocks every ~15 s with buff/cache ~185 MiB: the app is restarting, not the Pi.
- **Pd on the owner's unit is 0.52.2** (SD image, 2026-11-09). Other units may differ. The old-Pd rules below are
  proven on hardware, so keep them. Relax one only after checking that 0.52 has the feature:
  - no `expr`, and no signal into `lop~`'s cutoff inlet (send floats);
  - `[*~ <arg>]` when the right inlet takes floats (argless `*~` wants a signal);
  - `[table]` rather than `[array define]`;
  - escape `,` and `;` in comments (`gen.py`'s `text()` does this);
  - write `$1` as `\$1` in generated text (Python `"seed \\$1"`); an unescaped `$1` expands at load time
    ("argument number out of range");
  - `wrap~` only on **positive** input (old Pd's `wrap~` was wrong for negatives); `floor(z) = z − wrap~(z)`.

## 5. How to test (do this before handing anything over)
SuperCollider (`.scd`): the PC has **SC 3.10.4 + sc3-plugins 3.10.0**, the module's versions, at
`C:\Program Files\SuperCollider-3.10.4` (plugins in `%LOCALAPPDATA%\SuperCollider\Extensions`). PC and module NRT
renders are identical (SC probe, 2026-11-10).
```bash
python tools/sctest.py check sc/x.scd                 # syntax check (sclang compiles, nothing runs)
python tools/sctest.py run   sc/x_nrt.scd             # run e.g. an NRT render, then check it with wavcheck/wavpeaks
```
Pd:
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
  Record (any latch change) = mutate burst; File short = recall home, held 1 s = store home, double-tap = vanilla.
- **Window** auto-mutates every beat (`8·w³` per beat), and flip-on is gated by `0.7·fill` so hard mutation keeps
  the density.
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

### 07_shimmer (full detail: `docs/SHIMMER.md`)
- **Knobs:** blend = mix (equal-power); size = decay 0.4–60 s; window = damping; start = pre-delay; density = shimmer amount;
  overlap = mod (tank mod, then ensemble chorus past noon); pitch = Voice A interval (click = +12, V/oct);
  speed = Voice B interval (off between the clicks; stepped −5/−12/−24 left, +5/+7/+12/+19/+24 right).
- **Buttons:** Freeze = hold (loop shimmer paused); File held = momentary freeze; Source = Pre/Loop shimmer;
  Record = swell; Reset = clear (360 ms flush).
- **Alt:** start = low cut; size = room 0.5–2×; density = shimmer tone LP; overlap = mod rate; window = A/B balance;
  blend = duck; pitch_alt = detune ±25 cents. Pickup, as 05. **Source + Record = alt layer back to defaults**
  (re-arms the pickups first via `pickup(..., rebase=)`, else the ~1 ms alt stream overwrites the reset).
- **Engine:** tank + shifter in one canvas (a subpatch is sorted as a unit). Lines 0/1 crossfade cos θ/sin θ into the
  shifter, whose output re-enters through the diffuser (energy-balanced). Shifter has **no makeup gain**: with
  1/√0.75, steady tones on the 2000/W Hz comb gain 1.33 per pass and cascades grow.
- **New Pd lessons:** no `!-`/`!/` in vanilla; a frozen loop shimmer drains through its own LP (so Freeze pauses it).

### 08_resonator (full detail: `docs/RESONATOR.md`)
- **Knobs:** pitch = V/oct (continuous, click = C4); start = exciter material (sine→tri→saw→square→noise→S&H);
  size = T60 0.05–30 s; density = envelope pluck → bow; window = key-tracked loop damping; overlap = delay
  feedback (to 1.1); blend = delay mix; speed = delay time 20 ms–2 s.
- **Voices:** 4, taken in turn (= oldest-note stealing). A note latches Pitch at its strike + CATCH_MS (10 ms) and
  keeps it. The stolen voice's read and feedback are muted for one period of the new note (a clean flush); the
  strike waits 0.75 ms so its excitation isn't muted. An exciter per voice; its phase is `wrap~(t·f)` from a
  strike-started `vline~`, because a `phasor~` reset is block-quantised and made pluck levels random.
- **Buttons:** Reset = strike (3 ms after the gate + 0.75 ms; next voice); Freeze = hold all; Source = audio input
  into all 4 voices;
  Record = invert (period halved, stays on pitch); File short = V/oct mode Coupled / Res only / Exc only (no LED,
  Coupled at load); File held ≥ 300 ms = delay hold.
- **Alt:** start = exciter LP; size = stereo width (voices panned L, R, near L, near R); density = auto-repeat 0.25–16 Hz; overlap = delay tone
  (BBD murk/wobble → clean); window = offset ±36 st stepped (the interval in Coupled, the fixed side's note
  otherwise); blend = exciter dry ↔ resonator; pitch_alt = ping-pong. Source + Record = alt reset (+ mode Coupled).
- **Engine:**
  - `[pd res]` runs at `block~ 16`, so the loop can be ≥ 17 samples (top 2.6 kHz, 1.3 kHz inverted).
  - `vd~` gives exactly the requested delay: the measured residual is 0.
  - D = period − τ_lop(f) + τ_hip(f), so Window doesn't detune. g = 10^(−3T/T60)/|H(f)|, capped at 1.
  - Levels: exciter × (1 + periods per strike)^−0.75; audio input × √(1 − G); a control-rate auto-level per
    voice (env~ of its output → its excitation gain, reset at its strike) above −15 dB RMS. A shared one silenced
    new notes under a loud chord.
- **New tool:** `resonator.py`'s `E`/`program()`/`watched()` compile Python expressions to vanilla control objects
  (no `expr`). Use them for control math in new builders.

## 8. Starting a new instrument (checklist)
1. **Name:** `patches/09_<name>.pd`, with the numeric prefix for the selector.
2. **Builder:** a new `tools/<name>.py` with `<name>_patch(Canvas, controls_canvas, test=None)`. `tools/topo.py` is
   the most recent example (`trig()` action lists, `setv()`/`vadd()`/`vmul()` for `[v]` arithmetic); `tools/spectral.py` has
   the `op()`/`fl()`/`lerp()`/`step()` signal helpers and `pickup()` for alt knobs; `tools/resonator.py` has
   `program()`/`watched()` for control-rate math written as Python expressions.
   - Embed `controls_canvas()` as `[pd nebulae_controls]` (it also turns DSP on).
   - Use a unique send prefix per instrument (gloop `gl_`, glitch `gt_`).
   - Reuse `gloop.press()` for primed button edges, and the `chain()`/`rnd()` helpers in `glitch.py`.
3. **Register in `tools/gen.py`'s `__main__`:**
   - write `patches/09_<name>.pd`;
   - write `sim/test_09_*.pd` from `<name>_*_test()` scenario functions (`(ms, msg)` steps);
   - extend `--wav`.
4. **Test harness:** copy `glitch.glitch_patch`'s `if test:` block (tabwrite~ + soundfiler recording) and a scripted
   source like `beat_source`.
5. **Verify:**
   - Load check (no output).
   - Batch runs + `tools/wavcheck.py`.
   - Make sure the other patches are unchanged by builder edits (`git status`).
6. **Docs:**
   - `patches/09_<name>_README.md` (user guide: panel map, knobs, buttons, quick start, differences);
   - `docs/<NAME>.md` (design);
   - this file's §2 status row, §3 layout and §7 summary;
   - update `CLAUDE.md` if the builder list changes.
7. **Commit** with the attribution trailer. **Push** when the owner asks.
