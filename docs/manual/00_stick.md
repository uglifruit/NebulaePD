# Nebulae instruments: how to choose, and what's in this manual

This manual covers every instrument on the stick:
- Qu-Bit's five built in (the factory bank);
- the Pure Data, Csound and SuperCollider instruments we made;
- the community instruments you added.

Each has a guide in the same shape: what it is, a panel map, the controls, the buttons, the alt layer and a quick
start.

## Choosing an instrument (custom firmware uf2)
1. **Hold Speed for 1.5 s**: the selector opens.
2. **Turn Speed** to pick the bank: anticlockwise = **Csound user** (left light), middle = **factory** (both
   lights), clockwise = **Pd** (right light green), clockwise again = **SuperCollider** (right light **blue**).
3. **Turn Pitch** to pick the page of five. The Pitch light shows the page: white = 1–5, orange = 6–10, yellow =
   11–15, blue = 16–20, green = 21–25.
4. **Lit buttons** have an instrument; the bright one is running. **Press one** and it loads straight away.
5. Pitch or Speed **click** leaves without loading.

The five buttons, left to right, are **Record, File, Source, Reset, Freeze**: positions 1–5 of each page.

**Which button is which instrument:** the instruments sit in name order (digits before letters), so adding one
moves the others along. The current map is **`nebulae_banks.txt`** on the stick, regenerated whenever the stick
changes. This manual doesn't list positions, so it stays right however the stick is arranged.

Instruments made after another instrument say so in the index below and in an **Inspired by** line at the
top of their guide.

**The alt layer:** on every instrument, hold **Source** and turn a knob (or press a button) to reach its second
function. On our instruments, a knob's alt value only changes once you move it past where it was.

## In this manual
| Instrument | Bank | What it is |
|---|---|---|
| **a_granularlooper** | factory | Qu-Bit's granular looper: files from the stick or live recording, cut into grains |
| **b_oneshot** | factory | Qu-Bit's four-voice sample player: four buttons trigger four stick files |
| **c_synth** | factory | Qu-Bit's simple synth voice: two oscillators, a sub and a ladder filter |
| **d_effects** | factory | Qu-Bit's delay into reverb |
| **e_testio** | factory | Qu-Bit's input-to-output test |
| **gloop** (on the stick as Echo) | Pd | A 4-head looper (after the Cutlasses Gloop) |
| **glitch** | Pd | A clocked beat-repeater and breakbeat slicer (after your Workshop Computer Glitch) |
| **spectral** | Pd | Spectral Clouds+: a frozen, gathered, playable spectrum (after Spectral Clouds / your WorkshopSpectral) |
| **topo** | Pd | A drum-pattern map and drum synth (after Mutable Instruments Grids) |
| **shimmer** | Pd | A shimmer reverb |
| **resonator** | Pd | Exciter → resonator → delay (after the Morphor ECHON) |
| **chop** | Pd | A slice sequencer |
| **vocoder** | Pd | A 20-band vocoder |
| **topo kits** | Pd | Topo playing your sample kits (after Grids, through topo) |
| **shift** | Pd | A frequency shifter in a feedback delay |
| **partials** | Pd | An additive drone organ |
| **Durm** | Pd | Eli Pechman's four-voice drum machine |
| **Plasma Membrane** | Pd | Eli Pechman's phase-modulation voice |
| **ReconetC!** | Pd | Radek Rudnicki's generative dual sample slicer |
| **Rhythmic Chords** | Pd | Qu-Bit's example: chords with a rhythm |
| **stretch** | Csound | Extreme time-stretch and freeze |
| **morph** | Csound | Spectral morphing / cross-synthesis |
| **scan** | Csound | Scanned synthesis |
| **pulsar** | Csound | Pulsar synthesis |
| **tanpura** | Csound | A self-playing tanpura drone (after the Indian tanpura) |
| **chorale** | Csound | A choir drone |
| **radiate** | Csound | A stereo filter of four resonant peaks (after the Make Noise QPAS) |
| **gurdy** | Csound | A hurdy-gurdy (after the medieval instrument) |
| **plates** | Csound | An eight-voice drone you touch into life (after the SOMA Lyra-8) |
| **veil** | Csound | A drone voice with six algorithms (after the Forge TME Vhikk X) |
| **register** | Csound | Shift-register noise (after the Hikari Monos) |
| **Pearls** | Csound | Mutable Instruments Beads, ported |
| **bt_storyteller** | Csound | The granular looper, narrating to your PC over Bluetooth |
| **AVALON** | Csound | Ian Hoogeboom's wavetable morph oscillator (after the Synthesis Technology E350 / E352) |
| **Bowed Drone** | Csound | Collin Russell's bowed-string drone |
| **Mars Affects** | Csound | Ian Hoogeboom's filter, VCA, delay and shimmer reverb |
| **Realms** | Csound | Robert Pabst and Ian Hoogeboom's ambient rooms |
| **sc_drift** | SuperCollider | A drone / pad |
| **sc_strike** | SuperCollider | A plucked string |
| **sc_cloud** | SuperCollider | Granular clouds from the input |
| **sc_pattern** | SuperCollider | A generative sequencer |
| **sc_follow** | SuperCollider | Listens and plays a harmony along |
| **sc_mosaic** | SuperCollider | Rebuilds the input from pieces of a stick file |
| **sc_space** | SuperCollider | Diffuse delays into a long reverb |
| **sc_swarm** | SuperCollider | A drone of drifting oscillators |
| **999_fw_backup** | Csound | Utility: firmware backup and inventory (see Utilities) |

## Also on the stick
These are files the firmware or the instruments need:
- `sc_runtime.tgz` (SuperCollider);
- `csound_plugins/` (Pearls);
- `bt_keyboard/` (the storyteller);
- `neb_fwbackup/` (the firmware backup: **keep it**, the revert to stock uses it);
- the `.wav` and `.flac` sounds (the loopers, Realms and ReconetC play them);
- the community instruments' own manuals (`avalon.pdf`, `mars_affects.pdf`, `realms.pdf` and others).
