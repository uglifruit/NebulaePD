# 07_shimmer — shimmer reverb

A Strymon BigSky/blueSky-style **shimmer reverb**. A lush 8-line reverb has a pitch shifter in its feedback, so
every pass climbs another interval and the tail blooms into an octave-up halo. Two pitch voices are available, and
there's an option for the SoS-style "pre" shimmer: one layer, no climb. There's also tank modulation into ensemble
chorus, freeze, swell, ducking and clear.

Copy `07_shimmer.pd` to the USB root. Patch audio into the inputs; the output is stereo.

## Panel
| Control | Function |
|---|---|
| **Mix** (Blend) | Dry/wet, equal-power. Fully CW = 100 % wet (use this when it sits on a mixer send) |
| **Size** | Decay time: 0.4 s → 60 s (noon ≈ 5 s) |
| **Window** | Tone: high-frequency damping in the reverb. CCW = dark, fully CW = no damping |
| **Start** | Pre-delay 0 → 1 s (squared curve: noon = 250 ms) |
| **Density** | **Shimmer amount**. 0 = plain reverb. Noon = classic halo. CW = dense, fast-climbing shimmer |
| **Overlap** | **Mod**. CCW → noon: slow modulation inside the reverb (lush, no metallic ring). Noon → CW: also fades in a 3-voice ensemble chorus (Dimension-D / string-machine feel) |
| **Pitch** (+ V/oct) | **Voice A interval** in semitones. **The click = +12 (octave up)**. Turn to change the interval (−24 … +36), and use V/oct to sequence it |
| **Speed** | **Voice B interval**. Between the two clicks = **off**. Past the right click: +5, +7, +12, +19, +24. Past the left click: −5, −12, −24 (sub-octaves). Speed carries over from the last instrument, so check it after loading |

| Button / jack | Function |
|---|---|
| **Freeze** (LED) | Infinite hold. New input is shut out, the tail sustains forever, and the shimmer pauses so the held sound doesn't drift away |
| **File** (hold) | Momentary freeze while held |
| **Source** (LED) | Off = **Loop** shimmer (cascading, the Strymon sound). On = **Pre** shimmer: the input is pitch-shifted once before the reverb, giving one octave-up layer and no climb |
| **Record** (LED) | **Swell**: each new note fades into the reverb over about 1 s, for bowed, volume-pedal entries. A note counts as new after about 150 ms of silence |
| **Reset** (button or gate jack) | **Clear**: the tail is cut and the reverb is empty about 0.4 s later. From a gate it chops the tails rhythmically |

### Alt layer (hold Source)
An alt knob takes effect only once you move it.

| Control | Function | Default |
|---|---|---|
| alt **Start** | Low cut, 20 Hz → 1 kHz, on the reverb input and the shimmer loop | 80 Hz |
| alt **Size** | Room size, 0.5× (small, plate-like) → 2× (cathedral). Changing it bends the pitch briefly, like tape | 1× (noon) |
| alt **Density** | Shimmer tone: a lowpass on the shifted signal, 1 → 16 kHz. Lower = smoother and darker, CW = glassy | 6 kHz |
| alt **Overlap** | Mod / chorus rate, 0.05 → 5 Hz. Depth backs off automatically above 1 Hz | 0.4 Hz |
| alt **Window** | Voice A / B balance: CCW = A only, noon = equal, CW = B only. This only matters when Voice B is on | noon |
| alt **Blend** | Ducking: the wet signal dips under your playing (up to −24 dB) and blooms back when you stop | off |
| alt **Pitch** | Detune: spreads the shimmer voices up to ±25 cents (L/R and A/B), which makes it cloudier and wider. The alt-reset click sets it back to 0 | 0 |
| alt **Speed** | Not used (it's the Nebulae's input gain) | — |

## Quick start
1. Mix about 2 o'clock, Size noon, Window 2 o'clock, Density at 0, Pitch on its click (+12), Speed between the clicks.
2. Play. It's a plain hall. Bring **Density** up towards noon and the octave-up halo blooms in behind each note.
3. Push Size past 3 o'clock and Density higher for the endless rising pad. Pull alt Density (shimmer tone) down if
   it gets glassy.
4. Turn Speed past the left click to the first step past −12 for octave-up plus sub-octave (organ-like). The first
   step past the right click gives +5 (a fourth); the next step gives +7, the fifth.
5. **Freeze** to hold a chord and play over it. Reset clears it.

## Notes
- The shimmer decays with the reverb. At high Density the tail is a little shorter than the Size setting, because
  some energy climbs out of range through the shimmer lowpass.
- The loudest settings (Size and Density fully up, sustained input) are bounded by soft clipping. They're loud but
  safe, with no runaway.
- CPU is about the same as 05_spectral. If it crackles on an older Pi, tell me: the chorus and Voice B can be
  switched off when unused.
