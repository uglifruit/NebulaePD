# 09_sc_swarm: design notes

Built 2026-11-14. The owner chose:
- Pitch click = C2 (all four drones);
- Blend only mixes the input in (the drones don't listen);
- Source gathers the swarm onto a chord, with Start picking one of 8 shapes.

The rest was mine (they said "ask me any questions before I let you loose"). Patch `sc/09_sc_swarm.scd`, tests
`tools/sc_swarm_tests.py` (NRT) and `python tools/sc_osc_tests.py sc/09_sc_swarm.scd` (live), guide
`docs/manual/19_sc_swarm.md`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **32 voices** (planned 40: cut for CPU, see Engine) | 40 with a cheaper oscillator; 16 |
| 2 | **One VarSaw per voice: Overlap = triangle → saw.** The plan had sine → triangle → saw, but a sine per voice doubled the cost | A sine on the alt layer; a global low-pass for a near-sine |
| 3 | **Size = spread, cents = 1200 × Size²** (fine control near unison) | Linear |
| 4 | **Window = wander rate 0.02–3 Hz; Speed = breathing** (per-voice level swells; gentle between the clicks) | Speed = wander, Window = breathing |
| 5 | **Reset = shake** (every voice glides 0.3 s to a new random offset) | Reset = next chord |
| 6 | **Freeze = hold the wandering and breathing** (`Gate.kr`: an LFNoise at rate 0 didn't hold still) | Freeze = hold and mute the input |
| 7 | **Record = hush** (fades over about 3 s, LED on = hushed) | Record = sub octave |
| 8 | **Chords: fifth, major, minor, sus4, maj7, min7, add9, fourths**, voice *i* on note *i* mod 4 | Voicings spread over octaves |
| 9 | **Alt: width, sub sine, gather time, tone low-pass**; File unused | Reverb (not included: sc_space exists, and CPU) |
| 10 | **Stick: `09_sc_swarm.scd`** (SC orange page, Reset; `31-simple` moves to Freeze) | — |

## Engine
- Per voice:
  - `LFNoise2` drift (rate × a random 0.6–1.4), held by `Gate.kr`;
  - a `TRand` shake, lagged 0.3 s;
  - offset = (0.6 drift + 0.4 shake) × spread;
  - plus the chord note × the gather lag;
  - `VarSaw` (width 0.5 → 0.01) into `Pan2` (level = count fade × breathing), at a random fixed pan × width.
- The chord's four notes are looked up once, as a flat table (`Select.kr(chord × 4 + k, shapes.flat)`).
  **A per-voice `Select` over `shapes.collect { |s| s[k] }` gave wrong notes:** the gathered chord had C, E and
  octave C, but no G. Not explained, so avoid that form.
- Sum ÷ √count, low-pass (alt Overlap), sub sine, `LeakDC`, hush, blend, `Limiter` 0.95.
- The SynthDef is too big for one OSC message, which matters in NRT renders only. The tests write it to a file
  and `/d_load` it (`sc_space_tests.render(defload=True)`); live, `SynthDef.add` does the same by itself.

## Tests (2026-11-14: all pass)
| Scenario | Result |
|---|---|
| pitch | one voice: 65.37 Hz at the click, 130.74 at Pitch 0.8 |
| spread | about 5 cents of spread at Size 0.05, 97–145 cents at 0.6 (random per run) |
| density | 1 voice −19.8 dB, 32 voices −19.1 dB; 12 spectral peaks round the note against 1 |
| chord | Source + major: E 0.18 and G 0.56 of the energy (none before) |
| freeze | voices moved 14–52 cents in 4 s while wandering, under 4.2 held (the window's resolution is about 9 cents) |
| shake | frozen: 0.00 cents, then 11.7 cents across a Reset |
| wave | triangle: no 2nd harmonic, 3rd at 1.6 % of the fundamental's energy; saw: 2nd at 31 % |
| hush | −23 dB → silence → back to −21 dB |
| level | everything moving: peak 0.95 (the limiter), no NaN |
| OSC (live) | all 15 controls reach the synth |

**CPU (PC, NRT, 4 minutes):** 6.7 s per minute of audio with 32 voices at full Density (about 11 % of a
core), against 1.0 s for 04_sc_cloud. The first build (40 voices, three oscillators each) was 12.8 s.

## Hardware questions
- CPU on the Pi. The fallback is fewer voices (n = 24 or 16 in the patch).
