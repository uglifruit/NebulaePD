# Nebulae instruments: what is on the stick, and how to choose

The guides in this manual cover the instruments we made: Pure Data (gloop, glitch, spectral, topo, shimmer,
resonator, chop, vocoder, topo kits, shift, partials), SuperCollider (drift, strike, cloud, pattern, follow, mosaic, space, swarm), Csound (Pearls, stretch, morph, scan, pulsar, tanpura, chorale, radiate) and the Bluetooth storyteller. The other
instruments on the stick have their own manuals (listed below).

## Choosing an instrument (custom firmware uf2)
1. **Hold Speed for 1.5 s**: the selector opens.
2. **Turn Speed** to pick the bank: anticlockwise = **Csound user** (left light), middle = **factory** (both
   lights), clockwise = **Pd** (right light green), clockwise again = **SuperCollider** (right light **blue**).
3. **Turn Pitch** to pick the page of five. The Pitch light shows the page: white = 1–5, orange = 6–10, yellow =
   11–15, blue = 16–20, green = 21–25.
4. **Lit buttons** have an instrument; the bright one is running. **Press one** and it loads straight away.
5. Pitch or Speed **click** leaves without loading.

The five buttons, left to right, are **Record, File, Source, Reset, Freeze**: positions 1–5 of each page.

The module sorts the files by name (digits before letters), so a numeric prefix sets the position. Pd and SC files
starting with `_` are hidden. `nebulae_banks.txt` on the stick is this map, regenerated from the files
(`tools/stick_manifest.py`).

## The stick, 2026-11-15 (sorted)
| Bank / page | Button | Instrument | What it is |
|---|---|---|---|
| **Csound user**, white | Record | 002_avalon | AVALON "Morphing Nebulaeum": an 8×8×64 wavetable morph oscillator after the Synthesis Technology Terrariums; reads WaveEdit banks (`ROM A/B/C.wav`, `avalon.wav`). Manual: `avalon.pdf`, `avalon.txt` |
|  | File | 003_bowed_drone | Bowed Drone (Collin Russell; V1 port by Chris Erin): evolving bowed-string drones. Diagram: `Bowed_Drone_Diagram.pdf` |
|  | Source | 004_mars_affects | Mars Affects 1.5.1: filter, VCA, delay, effect, reverb and ducking in a chain (after the factory Effects / World of Echo). Manual: `mars_affects.pdf` |
|  | Reset | 005_realms_v1.0 | Realms (Robert Pabst, Ian Hoogeboom): morph through up to seven "rooms" of paired ambient loops (the `11_…72_` .flac files). Manual: `realms.pdf`, `realms.txt` |
|  | Freeze | 006_stretch | stretch: extreme time-stretch and freeze of stick files or of what you just played (its guide is in this manual) |
| **Csound user**, orange | Record | 007_morph | morph: spectral morphing / cross-synthesis of the input with a stick file (its guide is in this manual) |
|  | File | 008_scan | scan: scanned synthesis, a struck / bowed string whose shape is the waveform (its guide is in this manual) |
|  | Source | 009_pulsar | pulsar: a granular oscillator, pulsar synthesis (its guide is in this manual) |
|  | Reset | 010_tanpura | tanpura: a self-playing drone of four plucked, buzzing strings (its guide is in this manual) |
|  | Freeze | 011_chorale | chorale: a choir drone that sings vowels (its guide is in this manual) |
| **Csound user**, yellow | Record | 012_radiate | radiate: a stereo filter of four resonant peaks that radiate apart, self-oscillate and ping (its guide is in this manual) |
|  | File | 999_fw_backup | Utility: backs up the firmware and writes an inventory to the stick (see Utilities) |
|  | Source | bt_storyteller | The granular looper, telling your PC what happens to it over Bluetooth (its guide is in this manual) |
|  | Reset | pearls | Pearls: Mutable Instruments Beads (its guide is in this manual) |
| **Factory** (built in) | 1–5 | a_granularlooper, b_oneshot, c_synth, d_effects, e_testio | Qu-Bit's own: see the Nebulae manual. The granular looper's extra features are in "The two granular loopers" |
| **Pd**, white | Record | A_durm | No notes on the stick. From its patch: a drum processor with side-chain compression, trigger glitches, filter and downsampler; holding Source turns the burst off |
|  | File | B_Plasma_Membrane | No notes on the stick. Its knobs each control two parameters (split down the middle) |
|  | Source | C_ReconetC | Reconetc: a generative dual sample slicer with four micro-algorithms in zones, trigger probability, repeats and two reverbs. Needs its six samples (`Atmos`, `Kick`, `Piano1`, `Piano2`, `SnareCrickets`, `Stabs` .wav). Notes: `Reconetc redme.txt` |
|  | Reset | D_rhythmic_chords | Qu-Bit's Pd example (also in the firmware): chords on V/oct with a rhythm |
|  | Freeze | E_echo | Echo: the 4-head looper (the "gloop" guide in this manual; named Echo on the stick so it isn't taken for the Cutlasses Gloop) |
| **Pd**, orange | Record | F_glitch | glitch: clocked beat-repeater |
|  | File | G_spectral | spectral: Spectral Clouds+ |
|  | Source | H_topo | topo: drum patterns + drum synth |
|  | Reset | I_shimmer | shimmer: shimmer reverb |
|  | Freeze | J_resonator | resonator: exciter → resonator → delay |
| **Pd**, yellow | Record | K_chop | chop: slice sequencer (its guide is in this manual) |
|  | File | L_vocoder | vocoder: 20-band vocoder (its guide is in this manual) |
|  | Source | M_topokits | topo kits: topo playing your sample kits (its guide is in this manual) |
|  | Reset | N_shift | shift: frequency shifter in a feedback delay, barber-pole echoes (its guide is in this manual) |
|  | Freeze | O_partials | partials: an additive drone organ of 16 drifting partials (its guide is in this manual) |
| **SuperCollider**, white | Record | 02_sc_drift | drift: drone / pad |
|  | File | 03_sc_strike | strike: plucked string |
|  | Source | 04_sc_cloud | cloud: granular input |
|  | Reset | 05_sc_pattern | sc_pattern: generative sequencer with four voices (its guide is in this manual) |
|  | Freeze | 06_sc_follow | sc_follow: listens and plays a harmony along (its guide is in this manual) |
| **SuperCollider**, orange | Record | 07_sc_mosaic | sc_mosaic: rebuilds the input from pieces of a stick file (its guide is in this manual) |
|  | File | 08_sc_space | sc_space: diffuse delays into a long reverb, with freeze and ducking (its guide is in this manual) |
|  | Source | 09_sc_swarm | sc_swarm: a drone of 32 drifting oscillators that can gather onto chords (its guide is in this manual) |

Taken off on 2026-11-15 (kept in the repo if you ever want them back): the old user-bank copy of the granular looper (`001_a_granular_looper_Factory_Default`), the test utilities `bt_test`, `01_sctest` and `ZZ_pitchlog`, and Technobear's `31-simple`.

Also on the stick, needed by the firmware: `sc_runtime.tgz` (SuperCollider), `csound_plugins/` (Pearls), `bt_keyboard/` (the storyteller) and `neb_fwbackup/` (the firmware backup: **keep it**, the revert to stock uses it). The `.wav` and `.flac` files are the sounds the looper and Realms play.
