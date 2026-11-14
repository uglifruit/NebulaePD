# pulsar.instr: design notes

Built 2026-11-14 **without a design walk-through**: the owner was away ("auto choose sensible options"). Every
choice below was mine, and each lists alternatives. Instrument `instr/pulsar.instr`, tests `tools/pulsar_sim.py`,
guide `docs/manual/17b_pulsar.md`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **A voice (oscillator) first, input second.** It drones at load; Source makes grains of the live input | An input processor first (pulsar grains of the input as the main mode) |
| 2 | **Pitch = pulse rate, 1 V/oct, click = C3** | Click = C4 |
| 3 | **Start = formant 1, fixed Hz (100 Hz – 8 kHz)**; Freeze = Track (a multiple of the pitch, 0.5× – 16×) | Track as the default, or on alt Start; fixed-Hz only (classic pulsar) |
| 4 | **Size = duty cycle 3 % – 100 %**, with level make-up for short grains | Size = grain length in ms (independent of pitch) |
| 5 | **Density = random masking** (CW = every pulse) | A repeating 8-step mask pattern (rhythmic), random on alt |
| 6 | **Window = grain shape**: square-ish → bell → percussive (partikkel's sustain share and attack/decay ratio) | Separate attack and decay knobs |
| 7 | **Overlap = FM inside the grains, by a sine at the pitch** | FM at the formant; trainlets (partikkel's harmonic pulse trains) |
| 8 | **Speed = chirp per grain**, ±2 octaves, none between the clicks | Speed = pulse-rate glide / vibrato; Speed = formant drift |
| 9 | **Reset = sync** (the train restarts); with **Record = Pluck** each Reset plays a decaying note | Pluck as the default (silent until gated); Reset = new random seed |
| 10 | **File = waveform**: sine, saw, square, vowel, noise | More waveforms; stick WAVs as waveforms |
| 11 | **Source = the live input as the pulsaret** (grains from just behind the write head; Start = ±2 octaves) | Source = the input FM-ing the grains |
| 12 | **Alt: formant 2 ratio + level, stereo scatter, pluck decay, reverb size + amount, sub-octaves (alt Pitch, 0–8 octaves)** | Sub-octaves on Speed; a formant 3 |
| 13 | **Stick name `009_pulsar.instr`** (Csound user orange page, Reset; `999_fw_backup` moves to Freeze, `bt_storyteller`, `bt_test`, `pearls` one along) | — |

## Engine
- `partikkel` (in the module's 6.11 core library and in 6.09; checked in `libcsound64.so` read from the SD
  image). It runs two instances: the waveform one, and the live input one, read from a 65536-sample circular
  table. Source crossfades between them.
- **Grain rate:** `interp` of the pitch (0.25 Hz – 4 kHz). **Grain length:** duty × period, capped at 2 s.
- **Chirp:** the per-grain start/end frequency tables (`giSweepA`/`B`), rewritten with `tablew` every k-cycle.
  Formant 2 is wave 2, on `kwavekey2` with its level in the wave-amplitude table. The stereo scatter is
  alternating channel masks.
- **Sync:** a one-sample pulse into partikkel's sync input. It's built as `upsamp` → `diff` → `limit`, because
  partikkel adds the sync input to its clock phase, so a block of 1s would fire many grains.
- **`dcblock`, not `dcblock2`:** `dcblock2`'s high-order filter delays the output by about 3 ms, and the test
  put the pulses 5 ms late. With `dcblock` a pulse lands 0.1 ms after Reset (one k-cycle after the gate).
- partikkel's sample-position inputs must be a-rate variables in 6.18 (a constant 0 is refused): `azero`.
- Reverb (`reverbsc`) and soft clip (`tanh`), as scan.

## Tests (2026-11-14)
`wsl … tools/pulsar_sim.py`: 20/20 pass on Csound 6.18. `python tools/pulsar_sim.py m609`: 1/1 on 6.09.1.

| Scenario | Result |
|---|---|
| pitch | 130.7 Hz at the click, 261.5 Hz at Pitch 0.8; rms 0.14, peak 0.82 |
| formant | strongest partial 1047 Hz (1 kHz formant), 2485 Hz (2.5 kHz); Pitch up a fifth: 2489 Hz (the formant stays) |
| track | Freeze on: the strongest partial is harmonic 2.00 on both notes |
| duty | spectral spread 1307 Hz at 3 %, 92 Hz at 95 % |
| mask | at 2 Hz: Density 1 = 21 pulses in 10 s, 0.5 = 7, 0 = none |
| pluck | silent, a note on Reset, gone by 3 s |
| sync | a pulse 0.1 ms after each Reset |
| chirp | a long grain sweeps ×2.66 up (CW), ×0.34 down (CCW), measured inside the grain |
| file | sine → saw: spread 424 → 1773 Hz; Source: 49 % of the energy at the input's 660 Hz |
| fm | Overlap 1: spread 632 → 964 Hz |
| stereo | alt Density 1: L/R correlation 0.00 |
| sweep | 60 s of extremes: peak 1.000 (the soft clip), no NaN; CPU 0.30× the factory looper (0.29× at the defaults) |
| m609 | 6.09.1 compiles it; the drone at 130.7 Hz |

## Hardware questions
- Level against the other instruments (rms 0.14 at the defaults).
- Does the sub-octave rhythm (alt Pitch) want its own front-panel place?
