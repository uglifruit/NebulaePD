# quartet: four wavetable voices, eleven programs, a delay that runs away

A Csound drone of four wavetable voices. Three buttons play voices like touch pads, and the fourth voice drones
on Source. Each voice is reshaped by one of eleven programs on File. Then the mix is saturated, filtered by a
ladder filter, sent through a delay whose feedback goes past 100 %, and bitten by a destructive distortion.

**Inspired by:** Neutral Labs **Elmyra 2**. Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = LFO on CUTOFF  none between
 start                  size               the clicks
                                 start   = TUNING  voices apart (micro)
 density    [ pitch ]  overlap   size    = WAVE  the wavetable position
                                 density = MOD  the program's amount
       blend     window          overlap = FEEDBACK  100% at noon
                                 window  = CUTOFF
                                 blend   = BITE
                                 pitch   = NOTE, 1V/oct (click = C2)

 [record]  [file]    [source]  [reset]   [freeze]
  VOICE 1   PROGRAM   VOICE 4   VOICE 2   VOICE 3
  (hold)              (drone)   (hold)    (hold)
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The lowest voice (the click = C2) |
| **Start** | Tuning: how far apart the four voices sit (voice *n* is *n* × Start × 12 semitones up), unquantised, so microtonal. alt Start past noon rounds to semitones |
| **Size** | Wave: the position in the wavetable (sine → triangle → saw → square → pulse → formant → bell → buzz) |
| **Density** | Mod: the amount of the program on File |
| **Window** | Cutoff of the ladder low-pass (alt Pitch = resonance) |
| **Overlap** | Delay feedback: 100 % at noon, more beyond (it runs away, held by a soft limiter) |
| **Speed** | LFO on the cutoff. Between the clicks: none. Clockwise a sine, anticlockwise sample & hold, faster towards the ends |
| **Blend** | Bite: distortion and waveshaping, with a filter that closes as it bites harder (fully anticlockwise = clean) |

| Button / jack | Does | LED |
|---|---|---|
| **Record** (button or gate) | Touch voice 1: it sounds while held or while a gate is high | on while touched |
| **Reset** (button or gate) | Touch voice 2 | on while touched |
| **Freeze** (button or gate) | Touch voice 3 | on while touched |
| **Source** (button or gate) | Voice 4 drones | on = droning |
| **File** | The program (eleven go round): unison detune, sub-oscillators, chord, waveshaper, saturation, bitmangler, sample-rate reduction, noise, DJ filter, dual wave, hard sync | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Past noon: the tuning rounds to semitones | off (microtonal) |
| alt **Size** | Delay mix | about a third |
| alt **Density** | Envelope: attack and release, short → long | short |
| alt **Overlap** | Delay time (10 ms to 1.6 s) | ~0.25 s |
| alt **Pitch** | Filter resonance | a little |
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount (a stereo reverb after) | a little |
| alt **Speed** | The Nebulae's input gain | — |

Your input joins after the delay, into the bite.

## Quick start
1. Load `quartet` and press **Source**: voice 4 drones.
2. Hold **Record**, **Reset** or **Freeze** to bring in voices 1–3 (or patch gates into them).
3. Turn **Size** through the waves, press **File** for a program and turn **Density** for its amount.
4. **Overlap** past noon for runaway echoes; **Blend** to bite; **Speed** past a click for the LFO.

## Notes
- The mix is saturated before the filter, as on the original, so even sine voices carry a little grit.
- CPU, measured offline: about half the factory granular looper, reverb included (less with all four voices on).
