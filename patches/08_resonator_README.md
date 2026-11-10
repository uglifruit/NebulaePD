# 08_resonator — exciter → resonator → delay

A **4-voice resonator synth/effect** after the Morphor ECHON. Each note has its own **exciter** (a VCO shape, noise
or crackle, shaped by an envelope, or your audio input) feeding its own **pitched delay-line resonator**, which
rings like a string, a tube or a metal bar. Notes keep the pitch they were struck at, and a fifth note takes over
the oldest one. The result then goes through a dark, wobbly **BBD-style stereo delay**. Strike it with
Reset, play it with V/oct, or run any audio through it as a tuned resonator.

Copy `08_resonator.pd` to the USB root. The output is stereo. The audio inputs are only used when Source is on.

## Panel
| Control | Function |
|---|---|
| **Pitch** (+ V/oct) | Note of the **next strike**, continuous 1V/oct. **The click = C4** (261.6 Hz). The knob spans C1 … C6, and CV goes further, up to 2.6 kHz (1.3 kHz inverted). A ringing note keeps its pitch: only new strikes hear Pitch. What it sets depends on the **V/oct mode** (File, below) |
| **Start** | Exciter material. CCW → CW: sine → triangle → saw → square → noise → sample-and-hold crackle, crossfading between neighbours |
| **Size** | Decay: 0.05 s → 30 s (noon ≈ 1.2 s), the same at every pitch |
| **Density** | Exciter envelope. CCW = a short pluck/strike. Noon = a softer hit (≈ 30 ms attack). CW = a slow bowed swell (1.5 s in, 3 s out) |
| **Window** | Damping inside the resonator, which follows the note. CCW = muted, woody, short; noon = a natural string; CW = bright and metallic, ringing for the full Size |
| **Overlap** | Delay feedback. Past about 3 o'clock it runs away into BBD-style self-oscillation, which soft clipping keeps in check |
| **Blend** | Delay mix (equal-power). CCW = no delay; CW = delay only |
| **Speed** | Delay time, 20 ms → 2 s. Turning it while echoes play bends their pitch, like a BBD. Speed carries over from the last instrument, so check it after loading |

| Button / jack | Function |
|---|---|
| **Reset** (button or gate jack) | **Strike** a new note on the next of 4 voices, which is always the one holding the oldest note. That note stops cleanly; the other three ring on. The note sounds about 4 ms after the gate and takes Pitch from the gate and the next 10 ms, so a CV that lands just after the gate still counts |
| **Freeze** (LED) | **Hold**: every ringing note rings forever at its current tone, and new strikes are shut out |
| **Source** (LED) | **Audio in**: your input becomes the exciter of all 4 voices instead of the internal one. Drums, voice and synths ring through a 4-note chord. Reset + V/oct retunes the oldest note, so you build the chord with strikes |
| **Record** (LED) | **Invert** the feedback. The tone becomes hollow and clarinet-like (odd harmonics only), and it stays on the same note |
| **File** short press | **V/oct mode**: Coupled → Res only → Exc only → Coupled. See below. It starts on Coupled at load. There's no LED for it, so count your presses |
| **File** held (≥ 0.3 s) | **Delay hold** while held: the echoes repeat forever and the delay input is shut |

### V/oct mode (File short press)
| Mode | Resonator | Exciter | Feels like |
|---|---|---|---|
| **Coupled** (default) | Pitch | Pitch + the offset | the ECHON: both play the note |
| **Res only** | Pitch | fixed at C4 + offset | a fixed drone, noise or crackle whose overtones each new string picks out |
| **Exc only** | fixed at C4 + offset | Pitch | a fixed tuned body that you play notes through: they bloom near its pitch and its harmonics |

"Pitch" means Pitch at the strike: each note keeps what it took. Changing mode or the offset only affects new
strikes.

The **offset** is alt Window: semitones, ±36, noon = 0. In Coupled it's the exciter-to-resonator interval
(e.g. +12 or +7 for brighter, bell-like strikes). In the other modes it's the fixed side's note.

### Alt layer (hold Source)
An alt knob takes effect only once you move it.

**Lost? Hold Source and press Record:** every alt setting below goes back to its default, and the V/oct mode goes
back to Coupled. The knobs then do nothing until you move them again.

| Control | Function | Default |
|---|---|---|
| alt **Start** | Exciter lowpass (12 dB), 150 Hz → open. Softens the strike: felt hammer instead of pick | open |
| alt **Size** | Stereo width: CCW = every note in the centre; CW = notes alternate hard left, hard right, near left, near right | about 2 o'clock |
| alt **Density** | Auto-repeat: CCW = off, then 0.25 → 16 Hz self-strikes (the ECHON's looping envelope). Fast rates with a long Density bow continuously | off |
| alt **Overlap** | Delay tone: CCW = murky BBD (1.5 kHz, more wobble), CW = clean (16 kHz, no wobble) | ≈ 10 o'clock |
| alt **Window** | **Offset**, ±36 semitones in steps, with a wide 0 around noon (see V/oct mode) | 0 |
| alt **Blend** | Exciter dry ↔ resonator. CW = resonator only. Turn it back to hear the raw strike or input as well | CW |
| alt **Pitch** | Delay ping-pong: 0 = straight stereo, up = echoes bounce L ↔ R. The Nebulae's alt-reset click sets it to 0 | 0 |
| alt **Speed** | Not used (it's the Nebulae's input gain, which matters with Source on) | — |

## Quick start
1. Pitch on its click, Start at 10 o'clock (triangle), Size noon, Density CCW, Window noon, Blend CCW.
2. Press **Reset**: a plucked string. Sweep **Window** (muted → bright) and **Start** (hammered → noisy breath).
3. Density CW and press Reset again: a bowed swell. Turn on auto-repeat (alt Density) for an endless bow.
4. Patch a sequencer: CV → Pitch (V/oct), gate → Reset. Bring in **Blend** and **Overlap** for the delay, and set
   **Speed** to taste.
   Up to 4 notes ring together; play an arpeggio slowly with Size up and it becomes a chord.
5. Try **Record** (invert) for hollow, clarinet-ish tones, and **Freeze** to hold a chord.
6. **Source** on and feed it drums: every hit rings through the 4 notes you struck last. Strike new notes (Reset +
   V/oct) to change the chord while the drums play on.

## Notes
- **4 voices, oldest note stolen.** Strikes take the voices in turn, so the next one always holds the oldest note.
  A stolen note is muted for one period of the new note, exactly as long as it takes to leave the resonator, so it
  stops without a click or a pitch blip.
- **Pitch stays put.** A note takes Pitch at its strike (plus a 10 ms catch for a CV that arrives a moment after the
  gate) and keeps it. Pitch moves, the offset and the V/oct mode only affect new notes. With your firmware's faster
  Pitch tracking (uf1), a sequencer's note is settled within that window.
- Pitch is accurate: it measured within 0.01 cents offline from 92 Hz to 2.5 kHz, and within about 1 cent with
  Window fully CCW. The damping is compensated, so turning Window doesn't detune.
- With Window CCW, high notes are short whatever Size says. Each trip round the loop loses energy in the damping
  filter, and high notes make more trips per second, like a muted string. Size is exact with Window CW. At noon
  it's exact except for long Sizes on high notes, which come out a little shorter.
- Volume: a loud, sustained note (bowed, auto-repeat, audio input) is held near −15 dB RMS by an automatic level
  on its own excitation, which resets at every strike. Single strikes aren't affected. Four notes at once are louder
  (up to about −3 dB with the audio input exactly on the pitch of 4 identical notes); soft clipping bounds it.
- CPU offline is about the same as 07_shimmer's, twice the one-voice version's. The resonator runs in 16-sample
  blocks so it can reach high notes. If it crackles on the module, tell me: the top can drop to about 1.3 kHz to
  save CPU.

## Differences from the ECHON
- 4 voices, not 6, all on one shared panel (no per-voice settings or voice groups).
- There's no 12 dB resonator input filter as a fixed knob. alt Start does that job, and Window is the 6 dB loop
  filter.
- No LFO/mod matrix. Every knob has its own CV jack instead.
- There's an echo after the resonator (the ECHON has none), plus the V/oct routing modes.
