# 11_topokits — design notes

Built 2026-11-14 **without a design walk-through** (the owner was away: "make auto decisions and carry on").
Builder `tools/topokits.py` (the kit layer) + `tools/topo.py` (`topo_patch(kits=True)`, `voices(trig=)`), tests
`tools/topokits_tests.py`, guide `patches/11_topokits_README.md` (= manual section 14).

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **A sibling patch** (`11_topokits.pd`, stick `M_topokits`); `06_topo.pd` is byte-identical | Replace topo (one patch) once the kits are liked |
| 2 | **Samples replace the synth voice** where the kit has a file; other voices stay synth | Samples beside the synth, the Sound knob crossfading synth → samples (Sound would lose its synth-kit morph or the crunch) |
| 3 | **Kits = file names `kit<N>_<voice>.wav`**, N 1–8, voices kick snare clap hat open perc | One folder per kit (the firmware copies audio files to one folder; unverified for subfolders); a prefix per kit name |
| 4 | **Kit select = alt Pitch** (the encoder's alt accumulator, ~12 clicks per kit, kit 0 = synth only, applies only after it moves) | File (topo uses all three File gestures); alt Window (topo's pattern length); Source (its gate jack is step-1 reset) |
| 5 | **Tune and decay reach the samples**; decay below noon shortens, never lengthens | Per-voice tune/decay on the alt layer (no free controls left) |
| 6 | Velocity = level; CH chokes OH; topo's panning | Sample panning from the file (stereo samples) |
| 7 | Files read at load, up to 5 s each, left channel | Stereo samples (double the voices) |

## Engine
- `voices(trig="tp_syn_")`: topo's synth voices listen to the router's synth side.
- Router per voice: `tp_trig_<V> vel` → `tk_have[kit·6 + v]` → `tp_smp_<V>` (sample) or `tp_syn_<V>`.
- Sample voice: two halves (round robin, the other fades out in 3 ms); `tabread4~` switched to `tk_<kit>_<V>`
  per hit; `vline~` index 0 → n over n / (tune · sr / 1000) ms × min(1, decay); envelope 0.5 ms up, 5 ms down at
  the end. The kit layer's stereo sum joins the synth before topo's crunch.
- Loader: at load, for each of the 48 (kit, voice) names, `[file glob]` the exact path (no error if missing),
  then `soundfiler read -resize -maxsize 240000` and the length, sample rate and "have" tables.

## Tests (`python tools/topokits_tests.py`, 2026-11-14: all pass)
- alt Pitch: kit 0 → 1 → 2 → back to 0.
- Router: kit 1 (all six files) = every hit a sample; kit 2 (kick only) = only the kick; kit 0 = none.
- The kit tones appear only while their kit is on (+30–40 dB); kit 2's kick +41 dB.
- Decay (alt Blend 0.2): the 1 s kick plays 435 ms; tune (Pitch 0.7): rate ×1.4142 (+6 semitones).
- Bounded, no NaN; CPU 1.17× 06_topo per minute of audio.

## Hardware questions
- Are the kit files found on the module (they must sit with the other audio files on the stick root)?
- Is ~12 clicks per kit on alt Pitch comfortable? Load time with many kit files.
