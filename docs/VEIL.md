# veil.instr: design notes

Built 2026-11-15: a drone voice and FX with six algorithms sharing the same four timbre knobs, in the spirit of
a multi-algorithm drone voice (our own design and name). The owner asked for "knobs to turn that change formants,
overtones, and so forth. Some degree of motion", and chose:
- **6 algorithms**;
- **Speed drifts, Reset randomises**, Freeze holds;
- **Source processes the input**;
- **Overlap = space, Record = shimmer**;
- Pitch click = C2.

The rest was mine. Instrument `instr/veil.instr`, tests `tools/veil_sim.py`, guide `docs/manual/17h_veil.md`.
Stick `015_veil.instr`.

## The four knobs, per algorithm
| Algorithm | Start = overtones | Size = formant | Density = spread | Window = cross-mod |
|---|---|---|---|---|
| 1 swarm | wavetable morph: sine > triangle > saw > square > bell | the common 3-peak formant | 6 voices detuned to ±35 cents (plus an octave below and above) | each voice FMs the next |
| 2 choir | the vowel: a > e > i > o > u | voice size (formants ×0.7–1.4) | 4 voices to ±30 cents | roughness (a shaking fundamental) |
| 3 overtone stack | which harmonics (a bump from the 1st to the 10th, set exactly by `chebyshevpoly`) | a peak at a fixed frequency (200 Hz – 6.4 kHz) the harmonics pass through | 3 stacks to ±25 cents | ring modulation between stacks |
| 4 FM pair | the ratio, 0.5 .. 7 (through inharmonic places) | the common formant | 4 pairs to ±30 cents | the FM index |
| 5 ring | group B's ratio to A, 1 .. 4 | the common formant | detune within each group | how much of A × B |
| 6 resonant noise | resonator spacing: harmonic > stretched (bell-like) | which resonators ring loudest | left/right detune (slow beating) | the noise turned to crackle |

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Only the current algorithm runs:** File starts the next and the old one fades out over ~1 s, then stops (CPU stays at one algorithm's cost) | All six running, crossfaded (6× the CPU) |
| 2 | **The common formant:** three resonances (280 Hz .. 1.7 kHz, × 2.6, × 4.3) moving together, a little dry kept | A vowel bank on every algorithm |
| 3 | **Wavetables band-limited to 48 harmonics** (GEN30 from raw shapes): enough top at C2 for the formant to find, some aliasing above C5 | Per-octave tables (more memory, cleaner high up) |
| 4 | **Motion:** four smooth random drifts (overtones, formant, spread, cross-mod), ±0.1 .. ±0.7 by distance past the click × alt Size; none between the clicks | Regular LFOs |
| 5 | **Randomise (Reset):** new targets within ±(0.15 + 0.5 × alt Density), glided to (time constant 0.5 s) | A jump |
| 6 | **Freeze holds** the drift and the glide where they are (tested on the values themselves) | Freeze also holds the sound (spectral) |
| 7 | **Source:** the input through waveshaping (overtones), the formant, two chorus copies (spread) and ring modulation with a sine on the note (cross-mod), then the space | A vocoder (the oscillators carrying the input's shape) |
| 8 | **Space:** two allpasses per side into `reverbsc` (alt Window = size); Overlap = how much | — |
| 9 | **Shimmer:** the reverb's output an octave up (a Doppler shifter) fed back in, alt Overlap = how much | A fifth up |
| 10 | **alt:** Start = width, Size = motion depth, Density = randomise range, Window = space size, Overlap = shimmer, Blend = level | — |

## Engine notes
- A `turnoff` inside a user opcode crashed Csound 6.18, so each algorithm turns itself off (`$ALGEND`).
- `dust2` is k-rate only in the module's 6.11, so the crackle uses `dust` (a-rate there).
- The module's opcode list registers names with type suffixes (`oscili.a`): scan with them, or names look missing.

## Tests (2026-11-15)
`wsl … tools/veil_sim.py`: 17/17 on Csound 6.18. `python tools/veil_sim.py m609`: 1/1 on 6.09.1.

| Scenario | Result |
|---|---|
| pitch | the overtone stack's fundamental at 65.41 / 130.81 Hz |
| algos | all six sound (rms 0.06–0.18) and differ (the closest pair 1.2 decades apart) |
| overtones | centroid 103 → 638 Hz |
| formant | centroid 287 → 734 Hz |
| spread | the exact line loses 3 dB to its neighbourhood |
| crossmod | FM: energy over 1 kHz up 68 dB |
| vowel | "a" → "i": the 800 Hz / 2.3 kHz balance swings 38 dB |
| motion | still between the clicks (sd 0.02 octave), drifting past them (0.14); Freeze holds all four values exactly |
| reset | moves 2.4 octaves of centroid, 47 % of the way after 0.25 s |
| source | the input in (+57 dB), the oscillators out (−72 dB) |
| space | a tail 0.5–1 s after the input stops (−17 dB against none) |
| shimmer | octave-up energy in the tail +50 dB |
| shimmer at its most (added 2026-11-16) | with the drone, full Overlap, alt Window and alt Overlap, for 30 s: stays alive, peak 0.78 |
| sweep | 60 s of extremes through every algorithm: bounded, no NaN; CPU 0.43× the factory looper |

## Fixed after hardware (2026-11-16)
- **The owner: shimmer on "introduces shimmer, then crackles, and goes silent" until it's switched off.** The
  shimmer loop (reverb → octave up → back in) had a gain above unity and no limit. It ran away in about 4 s to a
  full-scale DC, which is silent. Now the feedback is scaled by the reverb's own gain (√(1 − fb²)), high-passed at
  200 Hz and soft-limited. The new test fails on the old code (pinned at 1.000) and passes now.

## Hardware questions
- Which algorithms earn their place? Any to swap for something else?
- Motion and randomise ranges: too much, too little?
