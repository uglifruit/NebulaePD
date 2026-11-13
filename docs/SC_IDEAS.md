# SuperCollider on the Nebulae: what exists, and what we could build

Written 2026-11-12 for the owner, who is new to SuperCollider (SC). Nothing here is built yet. The current SC bank
(uf2) and our four patches are in `sc/README.md`, and the plumbing is in `docs/FIRMWARE.md` "Stage 2".
The owner's shortlist across all engines is in `docs/INSTRUMENT_IDEAS.md` (SC: sc_pattern, sc_follow,
sc_mosaic).

## 1. SC in one page
SC is two programs:
- **scsynth**, the audio server, runs a graph of unit generators (UGens: oscillators, filters, grains, FFT …)
  efficiently in C++;
- **sclang**, the language, builds those graphs (SynthDefs), starts and stops them, and schedules events.

A Nebulae `.scd` patch is a sclang program. It boots the server, defines its sounds, and listens for the panel as
OSC messages (`/neb/pitch 0.6`, `/neb/reset 1` … on UDP port 3000, Technobear-compatible).

| Compared with Pd / Csound on this module | |
|---|---|
| **Strong** | **Polyphony and events**: every note can be its own synth, started and freed on demand. **The pattern language** (`Pbind`, `Pseq`, `Prand`, Routines): generative sequencing, Markov chains and probability are built in and compact. **The UGen library**: ours ships with sc3-plugins (below). **Live coding**: code can be changed while it plays (`Ndef`, `JITLib`). |
| **Weak** | **Latency 32 ms** (measured, `-p512 -n3`) against about 5 ms for Pd. Fine for drones, effects and sequenced things; not for tight, played-by-gate percussion that must line up with other modules. **5–10 s start-up.** One audio thread (scsynth). |
| **Same** | Every panel control and CV is available, 1 V/oct works, and audio files from the stick are copied to `/home/alarm/audio/` as for the other engines. The engine can't drive the LEDs, EOL or gate out (as in Pd). |

## 2. Technobear's SC patches
Mark Harris (TheTechnobear) added SC to the Nebulae in his 2020 firmware 2.2.x, crediting Stefano Catena for the
first version. uf2's SC bank is compatible with it. His examples live in
`github.com/TheTechnobear/NebulaePatches/sc`, cloned here as `external/NebulaePatches/`. **They are GPL-3**:
fine on your stick, but we don't copy their code into this repo (MIT).

| File | What it is | Worth it? |
|---|---|---|
| `00-default.scd` | A template, not an instrument. It lists every OSC address with its range and edge behaviour (Pitch clicks at 0.6, Speed clicks at 0.375 and 0.625, which buttons latch on rising or falling edges) and has an empty `OSCdef` per control | Reference. Our `sc/` patches already follow it |
| `01-livecoding.scd` | Forwards the panel's OSC to a laptop over the network, and tells it which audio files the module has. You live-code on the laptop; the module's server makes the sound | **Not usable on uf2: there is no network.** The same idea, on the module itself, is part of `docs/HDMI_KEYBOARD.md` |
| `30-grainbuf.scd` | Granular playback of the stick's audio files with `GrainBuf`: File picks the file, Start = position, Speed = rate, Size = grain length, Density = grains per second, Window = interpolation | A plain demo. It loads **every** audio file into memory at start (slow with a full stick). Our `04_sc_cloud` does live-input grains |
| `31-simple.scd` | A saw at 440–880 Hz on Pitch. Loud | Already on the stick, as a test |

His repo also has two Csound instruments (`grain_looper.instr`, `slice_looper.instr`) and a Pd Clouds port
(`pd/clds~`). His bigger system, **Orac**, is released separately on patchstorage. That's all the SC he
published for the Nebulae: it was a platform release with demos, not a set of instruments, so there is room for real
SC instruments.

## 3. What the runtime has (sc3-plugins, from his 2.2.2 build)
Beyond core SC (oscillators, filters, `GrainBuf`/`TGrains`, `PV_` spectral, `Pluck`, `Klank`, `DynKlank`, …):

| Family | UGens | Good for |
|---|---|---|
| Physical models | `DWGBowed`, `DWGPlucked` (waveguide strings), `OteyPiano`, `MdaPiano`, STK instruments (`StkInst`: mandolin, flute, clarinet, bowed, …), `MembraneCircle` / `MembraneHexagon` | playable acoustic-ish voices on V/oct + Reset |
| FM | `FM7` (a 6-operator matrix, DX7-style) | bells, e-piano, metallic basses |
| Space | `JPverb` (lush modulated reverb), `Greyhole` (diffuse delay network), `NHHall` (clean hall) | effect instruments |
| Analysis | `Tartini` / `Qitch` (pitch tracking), `AutoTrack` (beat tracking), `KeyMode`, `Chromagram`, `BeatStatistics`, `Concat` (concatenative resynthesis) | instruments that **listen** to the input |
| Chaos and odd | `ChaosUGens`, `MCLDChaos` (Lorenz, Hénon, logistic …), `Neuromodules`, `NoiseRing`, `Betablocker`, `VOSIM`, `GlitchUGens`, `DiodeRingMod`, `AY` (AY-3-8910 chip) | noise, drones, chip sounds |
| Loops | `LoopBuf`, `JoshGrainUGens`, `BhobGrain` | sample loops and grains |

Not included: the **BBCut2 class library** (only its beat-tracking UGens are there), and the Mutable Instruments
`mi-UGens` (Plaits, Rings, Clouds for SC). Both could be added to the runtime later, but that would mean
rebuilding `sc_runtime.tgz`.

## 4. Instruments we could make
Each idea plays to something SC does better than our Pd and Csound work. Rough CPU on the Pi 4 at 1.2 GHz, against
the module's single audio core:

| # | Idea | What it does | Panel sketch | CPU |
|---|---|---|---|---|
| 1 | **sc_pattern**: a generative sequencer with its own voices | 4 voices (pluck, FM bell, bass, noise hat), each with a Euclidean or probability pattern, quantised to a scale. Clocked by Reset, or free. Patterns mutate, freeze and come home (topo's ideas, melodic) | Pitch = root (V/oct), Start = scale/mode, Size = pattern length, Density = hits, Overlap = mutation, Window = voice mix/tone, Blend = space (JPverb), Speed = swing/rate; Freeze = lock, Record = mutate, File = home, Source = alt layer | low |
| 2 | **sc_follow**: it listens and plays along | Tracks the pitch of a monophonic input (`Tartini`) and the beat (`AutoTrack`), then adds voices: a harmony a 3rd/5th/octave away in the detected key (`KeyMode`), a sub-octave, or arpeggios in time with the beat | Pitch = interval, Start = voice (FM7 / string / pad), Density = arpeggio rate, Blend = dry/wet … | medium |
| 3 | **sc_space**: an effect pair that isn't shimmer | `Greyhole` diffuse delays into `JPverb`, with freeze, ducking and a pitch-drift option; quite different from 07_shimmer | Size = time, Window = damping, Overlap = diffusion, Density = modulation, Start = delay ↔ reverb … | low–medium |
| 4 | **sc_mosaic**: concatenative resynthesis | `Concat` rebuilds the live input out of tiny pieces of a stick audio file (or the input's own past): you play a drum loop, and it answers with matching fragments of a choir recording | File = corpus, Size = grain, Density = match strictness, Speed = scan … | medium |
| 5 | **sc_piano / sc_bow**: playable physical models | 4-voice `MdaPiano` or `DWGBowed` on V/oct + Reset, with sympathetic resonance (`DynKlank`) and space; like 08_resonator but acoustic | Pitch = note, Size = decay/pressure, Window = brightness, Density = hammer/bow … | medium (OteyPiano is high) |
| 6 | **sc_chaos**: strange attractors as drones | Lorenz / Hénon / neural oscillators as audio and as modulation; Pitch scales them, and the knobs move the attractor's parameters. It never repeats | | low |
| 7 | **sc_chip**: an AY-3-8910 tracker voice | the `AY` chip emulation: 3 square voices + noise + envelope; arpeggio chords from a V/oct note; pairs with the tracker idea in `docs/HDMI_KEYBOARD.md` | | low |

**Recommendation:** start with **1 (sc_pattern)**. It is the thing SC is uniquely good at, it doesn't care about the
32 ms latency (everything is scheduled), and it makes the Nebulae a different kind of instrument rather than
another effect. **2 (sc_follow)** is the most surprising, and best second: it is the storyteller's "listening",
made musical. Both need a short design walk-through with you first (as with topo). Port nothing from Technobear
except ideas.

## 5. To try now, with no work
Copy Technobear's `30-grainbuf.scd` (and `00-default.scd` to read) from `external/NebulaePatches/sc/` to the stick:
put a few short audio files on the stick, hold Speed, go past Pd (blue light), and load it. Expect a long start
while it loads every audio file. Its controls are listed in the table above.
