# Nebulae instruments: what is on the stick, and how to choose

The guides in this manual cover the instruments we made: Pure Data (gloop, glitch, spectral, topo, shimmer,
resonator, chop, vocoder, topo kits), SuperCollider (drift, strike, cloud, pattern), Csound (Pearls, stretch, morph, scan) and the Bluetooth storyteller. The other
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

## The stick, 2026-11-13
| Bank / page | Button | Instrument | What it is |
|---|---|---|---|
| **Csound user**, white | Record | 001_a_granular_looper_Factory_Default | An older release of Qu-Bit's granular looper (its overdub buffers differ from the built-in one) |
| | File | 002_avalon | AVALON "Morphing Nebulaeum": an 8×8×64 wavetable morph oscillator after the Synthesis Technology Terrariums; reads WaveEdit banks (`ROM A/B/C.wav`, `avalon.wav`). Manual: `avalon.pdf`, `avalon.txt` |
| | Source | 003_bowed_drone | Bowed Drone (Collin Russell; V1 port by Chris Erin): evolving bowed-string drones. Diagram: `Bowed_Drone_Diagram.pdf` |
| | Reset | 004_mars_affects | Mars Affects 1.5.1: filter, VCA, delay, effect, reverb and ducking in a chain (after the factory Effects / World of Echo). Manual: `mars_affects.pdf` |
| | Freeze | 005_realms_v1.0 | Realms (Robert Pabst, Ian Hoogeboom): morph through up to seven "rooms" of paired ambient loops (the `11_…72_` .flac files). Manual: `realms.pdf`, `realms.txt` |
| **Csound user**, orange | Record | 006_stretch | stretch: extreme time-stretch and freeze of stick files or of what you just played (its guide is in this manual) |
| | File | 007_morph | morph: spectral morphing / cross-synthesis of the input with a stick file (its guide is in this manual). *To copy: not on the stick yet* |
| | Source | 008_scan | scan: scanned synthesis, a struck / bowed string whose shape is the waveform (its guide is in this manual). *To copy: not on the stick yet* |
| | Reset | 999_fw_backup | Utility: backs up the firmware and writes an inventory to the stick (see Utilities) |
| | Freeze | bt_storyteller | The granular looper, telling your PC what happens to it over Bluetooth (its guide is in this manual) |
| **Csound user**, yellow | Record | bt_test | Utility: the Bluetooth check (see Utilities) |
| | File | pearls | Pearls: Mutable Instruments Beads (its guide is in this manual) |
| **Factory** (built in) | 1–5 | a_granularlooper, b_oneshot, c_synth, d_effects, e_testio | Qu-Bit's own: see the Nebulae manual |
| **Pd**, white | Record | A_durm | No notes on the stick. From its patch: a drum processor with side-chain compression, trigger glitches, filter and downsampler; holding Source turns the burst off |
| | File | B_Plasma_Membrane | No notes on the stick. Its knobs each control two parameters (split down the middle) |
| | Source | C_ReconetC | Reconetc: a generative dual sample slicer with four micro-algorithms in zones, trigger probability, repeats and two reverbs. Needs its six samples (`Atmos`, `Kick`, `Piano1`, `Piano2`, `SnareCrickets`, `Stabs` .wav). Notes: `Reconetc redme.txt` |
| | Reset | D_rhythmic_chords | Qu-Bit's Pd example (also in the firmware): chords on V/oct with a rhythm |
| | Freeze | E_echo | Echo: the 4-head looper (the "gloop" guide in this manual; named Echo on the stick so it isn't taken for the Cutlasses Gloop) |
| **Pd**, orange | Record | F_glitch | glitch: clocked beat-repeater |
| | File | G_spectral | spectral: Spectral Clouds+ |
| | Source | H_topo | topo: drum patterns + drum synth |
| | Reset | I_shimmer | shimmer: shimmer reverb |
| | Freeze | J_resonator | resonator: exciter → resonator → delay |
| **Pd**, yellow | Record | K_chop | chop: slice sequencer (its guide is in this manual). *To copy: not on the stick yet* |
| | File | L_vocoder | vocoder: 20-band vocoder (its guide is in this manual). *To copy: not on the stick yet* |
| | Source | M_topokits | topo kits: topo playing your sample kits (its guide is in this manual). *To copy: not on the stick yet* |
| | Reset | ZZ_pitchlog | Utility: measures the Pitch control's timing (see Utilities) |
| **SuperCollider**, white | Record | 01_sctest | Test patch: a plucked saw for checking the controls |
| | File | 02_sc_drift | drift: drone / pad |
| | Source | 03_sc_strike | strike: plucked string |
| | Reset | 04_sc_cloud | cloud: granular input |
| | Freeze | 05_sc_pattern | sc_pattern: generative sequencer with four voices (its guide is in this manual). *To copy: not on the stick yet* |
| **SuperCollider**, orange | Record | 31-simple | Technobear's example: a saw on Pitch. **Loud**: turn the output down first |
