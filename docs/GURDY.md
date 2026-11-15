# gurdy.instr: design notes

Built 2026-11-15: a hurdy-gurdy, the drone synth's mechanical ancestor. The owner chose:
- Speed = the crank;
- Start plays the melody in a scale (and its CV jack), Source = melody on;
- Reset strokes + crank surges buzz the trompette;
- bowed-string models;
- File = modes (scale + drones together);
- Pitch click = C2 (the drones' rule from round 3).

The rest was mine. Instrument `instr/gurdy.instr`, tests `tools/gurdy_sim.py`, guide `docs/manual/17f_gurdy.md`.
Stick `013_gurdy.instr`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Strings:** five bowed waveguides (`wgbow`): bourdon (the key), mouche (a fifth up, an octave in minor), trompette (an octave up), two melody strings 3 cents apart | More drone strings; a sixth melody string an octave up |
| 2 | **The crank:** stopped fully anticlockwise, a steady turn at noon, faster clockwise. 0.25 s of wheel inertia; louder, harder bow and nearer the bridge as it speeds up, plus a high shelf that opens past noon | A noon dead zone (as our other Speed knobs) |
| 3 | **Wheel irregularity:** the bow pressure wobbles once per revolution (alt Size = how much, default 0.3) | A perfectly even wheel |
| 4 | **The melody:** Start (and its CV) picks one of 15 notes (two octaves of the mode's scale) from an octave above the key; a tangent tick on each change; alt Density = glide | A continuous (fretless) Start |
| 5 | **Freeze = hold the melody note** (Start and its CV are ignored until released) | Freeze = hold the crank speed |
| 6 | **Record = the trompette buzzes all the time** | Record = melody an octave up |
| 7 | **The trompette's "dog":** the string's square-ish shadow, differentiated into a click each half-cycle, band-passed to 1–3 kHz, louder than the string's own top. A stroke lasts ~0.1 s. A crank surge (Speed up by more than 0.08 + 0.2 × alt Overlap in 80 ms) buzzes it | A sampled buzz |
| 8 | **Density = drones' level** (melody alone → full drones) | Density = how many drone strings |
| 9 | **Overlap = sympathetic strings:** four delay-line resonators on the mode's root, third, fifth and octave, rung by everything | `streson`: it went NaN on C3 in Csound 6.09.1, so it's out |
| 10 | **Window = the body:** three wooden resonances (290, 560, 1350 Hz) scaled by ±0.6 octave | — |
| 11 | **Modes (File):** major / mixolydian / dorian with fifth drones, minor with octave drones | Other modes; drone tuning separately |
| 12 | **alt:** Start = width, Size = wheel irregularity, Density = glide, Overlap = buzz sensitivity, Window/Blend = reverb | — |

## Engine notes
- `wgbow` runs sharp by about 0.84 samples of loop (0.1 % at C2, 0.5 % at C4). Each string's frequency is corrected
  by `1/(1/f + 0.0000175)`. Measured: within 0.2 % from C2 to C4.
- Per-string audio code uses multipliers (`itk`, `itr`), not `if ir == n` blocks: the trompette's rattle inside an
  i-rate `if` stayed silent.
- `wgbow` alone is stable on 6.09.1. The 6.09 NaN was `streson`, now replaced.

## Tests (2026-11-15)
`wsl … tools/gurdy_sim.py`: 15/15 on Csound 6.18. `python tools/gurdy_sim.py m609`: 1/1 on 6.09.1.

| Scenario | Result |
|---|---|
| drones | C2 65.41, G2 98.02, C3 130.84 Hz |
| melody | Start → C3 130.96, E3 164.99, G3 196.24, C4 261.98 Hz |
| mode | minor: no G2 (40 dB under), third on E♭3 155.73 Hz |
| crank | stopped silent; noon rms 0.12; fast louder and brighter (centroid +25 %) |
| trompette | strokes +8.5 dB at 1.5–4 kHz; Record +6.9 dB |
| surge | a quick turn +7.7 dB |
| freeze | holds G3 while Start goes to C3 |
| pressure | Size: +13 dB of top |
| body | Window: centroid 885 → 646 Hz |
| sympathy | the halo rings on after the wheel stops |
| sweep | 60 s of extremes: bounded, no NaN; CPU 0.78× the factory looper |

## Hardware questions
- Is the crank's feel right (inertia, the speed range)? Does the dog bark at the right effort?
- Is wgbow's squeak at high pressure musical, or should Size stop short of it?
