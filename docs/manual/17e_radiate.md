# radiate: a stereo filter of four resonant peaks

A Csound stereo filter with four resonant peaks. Pitch sets the lowest peak and **Start (Radiate)** spreads the
others above it. **File** picks how they're spaced: evenly, as harmonics, in octaves or as a chord. **Window**
morphs the output from low-pass through band-pass and high-pass to "smile". Turn **Size** up and the peaks ring,
then sing on their own: a stereo chord you can play from a sequencer. A gate into **Reset** pings them like a
struck bell or drum.

It's in the **Csound user bank** as `012_radiate` (yellow page, Record button).

## Panel map
```
            [ speed ]            speed   = ANIMATION  none between
 start                  size               the clicks: CW circles,
                                           CCW wanders
 density    [ pitch ]  overlap   start   = RADIATE  peaks spread apart
                                 size    = RESONANCE  .. self-oscillate
       blend     window          density = PEAKS  1 .. 4
                                 overlap = DRIVE
                                 window  = OUTPUT  LP > BP > HP > smile
                                 blend   = dry <-> filter
                                 pitch   = CUTOFF, 1V/oct (click = C6)

 [record]  [file]    [source]  [reset]   [freeze]
  DIRTY     SHAPE     R IN = FM  PING      HOLD ANIM
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The cutoff: the lowest peak. The click = C6 (about 1 kHz); the whole range is about 46 Hz to 11.7 kHz. It tracks exactly, so when it self-oscillates you can play it |
| **Start** (Radiate) | Spreads the other peaks above the lowest. **Noon** (a flat zone) = exactly the File shape. Anticlockwise squeezes them together, all on one peak fully anticlockwise. Clockwise stretches them, to twice the shape |
| **Size** | Resonance: gentle → sharp peaks. In the last part of the turn the peaks sing on their own (self-oscillation) |
| **Density** | Peaks: 1 to 4 (one plain resonant filter up to all four) |
| **Overlap** | Drive into the filter (unity at about a third) |
| **Window** | The output, morphing smoothly: low-pass → band-pass → high-pass → smile. Smile passes lows and highs, with a resonant edge at each end and a dip between (it widens as you spread the peaks) |
| **Speed** | Animation. Between the two clicks: none. Clockwise past the click the peaks circle (Radiate and cutoff move together, smoothly); anticlockwise they wander at random. Faster towards the ends |
| **Blend** | Dry input ↔ filter (equal power). It loads fully clockwise |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Ping: every peak rings at its frequency (alt Density sets how long). Patch a sequencer gate in for drums and plucks, even with no input | — |
| **Source** (button or gate) | The right input stops being audio and **modulates the cutoff** at audio rate (FM: growls, metallic and bell tones). The left input then feeds both channels. alt Start = depth | on = FM |
| **Record** (button or gate) | Dirty: saturation before and after the peaks, and the sound pulls the cutoff, so it growls | on = dirty |
| **Freeze** (button or gate) | Hold the animation exactly where it is. Press again and it carries on | on = held |
| **File** | Peak shape: **even** (evenly spaced) → **harmonic** (1 : 2 : 3 : 4) → **octaves** → **chord** (root, fifth, octave, tenth). Four presses go round | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | FM depth (with Source on) | a little |
| alt **Size** | Animation depth | half |
| alt **Window** | Animation target: Radiate only ↔ both ↔ cutoff only | both |
| alt **Density** | Ping ring time (20 ms to 3 s) | about 0.15 s |
| alt **Overlap** | Stereo width: the high peaks go wide left and right | wide-ish |
| alt **Blend** | Output level (±12 dB) | 0 dB |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `012_radiate` with something in the left input: a stereo low-pass at about 1 kHz with four soft peaks.
2. Turn **Size** up for sharper peaks, **Start** to spread them, **Window** for band-pass, high-pass or smile.
3. Press **File** for the harmonic, octave or chord shapes; turn **Density** down for fewer peaks.
4. Turn **Speed** past a click to set it moving; **Freeze** holds the shape you like.
5. Turn **Size** fully up for a singing stereo chord on Pitch, or patch a gate into **Reset** to ping it.
6. Put a second sound (an oscillator, an LFO) into the right input and press **Source** for FM.

## Notes
- With nothing in the right input it copies the left, so a mono source comes out in stereo.
- The self-oscillation and the pings are exactly in tune (sines on the peaks). The filter peaks themselves pull
  slightly towards each other when they're close (up to about 2 %).
- CPU, measured offline: about two-thirds of the factory granular looper.
