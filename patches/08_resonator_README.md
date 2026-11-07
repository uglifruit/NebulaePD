# 08_resonator — exciter → resonator → delay

A one-voice **resonator synth/effect** after the Morphor ECHON. An **exciter** (a VCO shape, noise or crackle,
shaped by an envelope, or your audio input) is fed into a **pitched delay-line resonator** that rings like a string,
a tube or a metal bar. The result then goes through a dark, wobbly **BBD-style stereo delay**. Strike it with
Reset, play it with V/oct, or run any audio through it as a tuned resonator.

Copy `08_resonator.pd` to the USB root. The output is stereo. The audio inputs are only used when Source is on.

## Panel
| Control | Function |
|---|---|
| **Pitch** (+ V/oct) | Note, continuous 1V/oct. **The click = C4** (261.6 Hz). The knob spans C1 … C6, and CV goes further, up to 2.6 kHz (1.3 kHz inverted). What it moves depends on the **V/oct mode** (File, below) |
| **Start** | Exciter material. CCW → CW: sine → triangle → saw → square → noise → sample-and-hold crackle, crossfading between neighbours |
| **Size** | Decay: 0.05 s → 30 s (noon ≈ 1.2 s), the same at every pitch |
| **Density** | Exciter envelope. CCW = a short pluck/strike. Noon = a softer hit (≈ 30 ms attack). CW = a slow bowed swell (1.5 s in, 3 s out) |
| **Window** | Damping inside the resonator, which follows the note. CCW = muted, woody, short; noon = a natural string; CW = bright and metallic, ringing for the full Size |
| **Overlap** | Delay feedback. Past about 3 o'clock it runs away into BBD-style self-oscillation, which soft clipping keeps in check |
| **Blend** | Delay mix (equal-power). CCW = no delay; CW = delay only |
| **Speed** | Delay time, 20 ms → 2 s. Turning it while echoes play bends their pitch, like a BBD. Speed carries over from the last instrument, so check it after loading |

| Button / jack | Function |
|---|---|
| **Reset** (button or gate jack) | **Strike**: fires the exciter envelope on the other of two resonators, so the previous note rings on at its own pitch under the new one. Patch a trigger or clock here. The strike waits until Pitch has settled (3 ms normally, ~15 ms after a big V/oct jump, 30 ms at most) |
| **Freeze** (LED) | **Hold**: the resonator rings forever at its current tone, and new strikes are shut out. Pitch still bends the held note |
| **Source** (LED) | **Audio in**: your input becomes the exciter instead of the internal one. Drums, voice and synths ring at the resonator's pitch |
| **Record** (LED) | **Invert** the feedback. The tone becomes hollow and clarinet-like (odd harmonics only), and it stays on the same note |
| **File** short press | **V/oct mode**: Coupled → Res only → Exc only → Coupled. See below. It starts on Coupled at load. There's no LED for it, so count your presses |
| **File** held (≥ 0.3 s) | **Delay hold** while held: the echoes repeat forever and the delay input is shut |

### V/oct mode (File short press)
| Mode | Resonator | Exciter | Feels like |
|---|---|---|---|
| **Coupled** (default) | follows Pitch | follows Pitch + the offset | the ECHON: both play the note |
| **Res only** | follows Pitch | fixed at C4 + offset | a fixed drone, noise or crackle whose overtones a moving string picks out |
| **Exc only** | fixed at C4 + offset | follows Pitch | a fixed tuned body that you play notes through: they bloom near its pitch and its harmonics |

The **offset** is alt Window: semitones, ±36, noon = 0. In Coupled it's the exciter-to-resonator interval
(e.g. +12 or +7 for brighter, bell-like strikes). In the other modes it's the fixed side's note.

### Alt layer (hold Source)
An alt knob takes effect only once you move it.

**Lost? Hold Source and press Record:** every alt setting below goes back to its default, and the V/oct mode goes
back to Coupled. The knobs then do nothing until you move them again.

| Control | Function | Default |
|---|---|---|
| alt **Start** | Exciter lowpass (12 dB), 150 Hz → open. Softens the strike: felt hammer instead of pick | open |
| alt **Size** | Stereo spread: detunes L/R by up to 30 cents (chorus-like beating) | 6 cents |
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
5. Try **Record** (invert) for hollow, clarinet-ish tones, and **Freeze** to hold a note while you bend Pitch.
6. **Source** on and feed it drums: every hit rings at the Pitch note. Press File once (Res only) and sequence the
   ringing pitch while the drums play on.

## Notes
- **Two voices.** Each strike alternates between two resonators. The ringing note keeps its pitch, and a third
  note takes over the older voice. A Pitch change that comes within 40 ms before a strike belongs to the new
  note. Slower moves (bends, a frozen note, the audio-input drone) still bend the ringing voice, 40 ms late.
- **Why the strike waits:** the Nebulae smooths the Pitch CV before Pd sees it (a big jump arrives as a ramp over
  10–30 ms). Striking during that ramp swoops the attack, so the strike waits for Pitch to stop moving.
- Pitch is accurate: it measured within 0.01 cents offline from 92 Hz to 2.5 kHz, and within about 1 cent with
  Window fully CCW. The damping is compensated, so turning Window doesn't detune.
- With Window CCW, high notes are short whatever Size says. Each trip round the loop loses energy in the damping
  filter, and high notes make more trips per second, like a muted string. Size is exact with Window CW. At noon
  it's exact except for long Sizes on high notes, which come out a little shorter.
- Volume: loud, sustained resonances (bowed, auto-repeat, matched audio input) are held near −9 dB RMS by an
  automatic level on the excitation. Single strikes aren't affected. The worst cases are bounded by soft clipping.
- CPU offline is a little below 07_shimmer's. The resonator runs in 16-sample blocks so it can reach high notes.
  If it crackles on the module, tell me: the top can drop to about 1.3 kHz to save CPU.

## Differences from the ECHON
- Two alternating voices, not six (monophonic playing; the previous note rings on).
- There's no 12 dB resonator input filter as a fixed knob. alt Start does that job, and Window is the 6 dB loop
  filter.
- No LFO/mod matrix. Every knob has its own CV jack instead.
- There's an echo after the resonator (the ECHON has none), plus the V/oct routing modes.
