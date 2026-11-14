# Instrument ideas: Pd, Csound, SuperCollider and the platform

Proposed 2026-11-13. Each idea plays to what its engine, or this module, does best. **★ = on the owner's
shortlist.** **First build: stretch.** SC detail is in `docs/SC_IDEAS.md`, and screen/keyboard ideas are in
`docs/HDMI_KEYBOARD.md`.

Already built (so these don't repeat them):
- Pd: gloop (Echo on the stick), glitch, spectral, topo, shimmer, resonator;
- SC: drift, strike, cloud;
- Csound: Pearls, storyteller.

## What each engine is good at here
| Engine | Strengths | Weaknesses |
|---|---|---|
| **Pd 0.52** (vanilla) | ~5 ms control response, sample-accurate logic and tables: the best engine for clocked, in-time things. `sigmund~` (pitch, partials), `bonk~` (onsets), `bob~` (Moog ladder), `hilbert~`. Our Python builders. uf2 loads `.pd_linux` externals from the stick | a thin DSP library; everything is hand-built |
| **Csound 6.11** | The deepest built-in library: `partikkel`, `paulstretch`, `mincer`/`temposcal`, the `pvs` streaming phase vocoder (`pvscross`, `pvsmorph`, `pvsarp`, `pvsbufread`), `tradsyn`/`sinsyn`, scanned synthesis (`scanu`/`scans`), `prepiano`, `barmodel`, `wgbow`, `reverbsc`, `zdf_ladder`, `diode_ladder`, `vosim`. **Native C++ plugins** through uf2's private plugin folder (proven by Pearls) | control logic is clumsier than Pd's |
| **SC 3.10.4** + sc3-plugins | patterns, polyphony, live code, `FM7`, waveguide/STK/piano models, `JPverb`/`Greyhole`, pitch/beat/key tracking, `Concat` | 32 ms latency, 5–10 s start |
| **The platform** | 4 GB RAM (minutes to hours of audio, where Eurorack MCUs have seconds), 4 cores, a proven Bluetooth stack, the stick, our own firmware, one unused EOL gate out | one engine at a time; no CV out |

Effort: S = a few sessions, M = like topo or resonator, L = bigger. CPU is against one audio core.

## Pure Data
| | Idea | What it is | Effort / CPU |
|---|---|---|---|
| ★ | **chop**: slice sequencer: **built 2026-11-14**, awaiting hardware (`patches/09_chop.pd`, guide `patches/09_chop_README.md`, design `docs/CHOP.md`; our own onset detector instead of `bonk~`, Freeze holds the dice, Source = step 1) | Record a loop or load a stick WAV. It is auto-sliced at its onsets (`bonk~`), and a step sequencer clocked by Reset replays the slices in a new order, with per-step probability, ratchets, reverse and pitch. Freeze locks the pattern, Record re-rolls it, File loads the next WAV. In time, with zero added latency | M / low |
| ★ | **vocoder**: **built 2026-11-14** without a walk-through (the owner was away; decisions to review in `docs/VOCODER.md`), awaiting hardware (`patches/10_vocoder.pd`, guide `patches/10_vocoder_README.md`) | A 20-band channel vocoder. Left in = modulator (voice, drums). The carrier is the right input, or an internal supersaw/noise chord on V/oct. Formant shift, freeze of the spectral envelope, unvoiced-noise detection | S–M / low |
| | **shift**: frequency shifter + barber-pole | A single-sideband shifter (`hilbert~`) with V/oct-able shift, inside a feedback delay: endlessly rising or falling echoes. Ring-mod mode; opposite shift per side | S / low |
| ★ | **topo kits**: **built 2026-11-14** as a sibling patch without a walk-through (decisions to review in `docs/TOPOKITS.md`), awaiting hardware (`patches/11_topokits.pd`) | topo's patterns playing sample kits from the stick, with kit choice on the alt layer (the Source gate jack stays step-1 reset) | S–M / low |

## Csound
| | Idea | What it is | Effort / CPU |
|---|---|---|---|
| ★ | **stretch**: **built 2026-11-13**, awaiting hardware (`instr/stretch.instr`, guide `docs/manual/15_stretch.md`) | Extreme time-stretch and freeze of stick files or a captured input (`mincer`, phase-locked vocoder): 10×–1000× slower with the pitch unchanged. Start scrubs, Speed = stretch, Pitch = transpose (V/oct), layers, blur and a reverb tail. Measured at 1.2–1.5× the factory looper's CPU | S / medium |
| ★ | **morph**: cross-synthesis: **built 2026-11-14** without a walk-through (decisions in `docs/MORPH.md`), awaiting hardware (`instr/morph.instr`, guide `docs/manual/16_morph.md`) | `pvscross` / `pvsmorph` / `pvsvoc`: one source's spectral envelope on the other (L↔R, or input ↔ stick file). Blend morphs between them, with freeze per side and a spectral arpeggiator (`pvsarp`) on V/oct | M / medium |
| ★ | **scan**: scanned synthesis | A mass-spring string whose shape is the waveform. Knobs = mass, stiffness, damping, centring; Reset strikes it; audio input can excite it | M / low–medium |
| | **pulsar**: a granular oscillator | `partikkel` as a playable V/oct voice: pulsar/trainlet synthesis, formant grains, per-grain FM, grain masks | M / medium |
| | **plugin ports** | Mutable Instruments' MIT DSP as Csound plugins (the Pearls route), e.g. a Plaits-style macro oscillator or an Elements-style modal voice, renamed | M each |

## SuperCollider (detail in `docs/SC_IDEAS.md`)
| | Idea | What it is | Effort / CPU |
|---|---|---|---|
| ★ | **sc_pattern** | A generative sequencer with its own 4 voices: Euclidean/probability patterns quantised to a scale; mutate, lock, home | M / low |
| ★ | **sc_follow** | Tracks the input's pitch and beat; adds a harmony in the detected key, a sub-octave, or arpeggios in time | M / medium |
| ★ | **sc_mosaic** | Concatenative resynthesis: the input answered with matching fragments of a stick file | M / medium |
| | **sc_space** | `Greyhole` diffuse delays into `JPverb`, with freeze and ducking | S / low–medium |

## The platform (not this round)
| Idea | What it is | Effort |
|---|---|---|
| **BLE-MIDI** | The Nebulae as a Bluetooth MIDI device, on the storyteller's radio stack: knobs/CV/gates out as MIDI, and MIDI in to play any instrument | M–L |
| **time machine** | Always records the last 30–60 min in RAM: scrub back in time, replay what happened 10 minutes ago, save a span to the stick | M |
| **gate out (uf1b)** | Lets Pd/SC drive the EOL jack: gate-out sequencers, drums in / trigger out, clock divide | S–M (firmware) |

## How each one gets built
A design walk-through with the owner comes first (panel, buttons, alt layer), one step at a time. Then:
- **Pd:** a builder in `tools/` called from `tools/gen.py`, with offline batch tests and `wavcheck`;
- **Csound:** an `.instr`, with every opcode checked against the 6.11 source, rendered offline, and CPU measured;
- **SC:** `sc/NN_*.scd` with `tools/sctest.py`, `sc_nrt_tests.py` and `sc_osc_tests.py`.

Each build ends with a manual section in `docs/manual/`, the stick map, and the owner's hardware test.
