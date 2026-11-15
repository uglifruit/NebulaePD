# sc_swarm: a drone of drifting oscillators

A SuperCollider drone. 32 oscillators sit around one note, each wandering on its own slow path. Close together
they beat and shimmer; spread out they become a cluster; press Source and they gather onto a chord. Nothing
repeats, so it can run for hours.

**Bank:** SuperCollider (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = BREATHING  gentle between
 start                  size               the clicks, deeper at ends
                                 start   = CHORD  (with Source on)
 density    [ pitch ]  overlap   size    = SPREAD  unison -> cluster
                                 density = VOICES  1 .. 32
       blend     window          overlap = WAVE  triangle -> saw
                                 window  = WANDER  slow -> fast
                                 blend   = dry <-> swarm
                                 pitch   = NOTE, 1V/oct (click = C2)

 [record]  [file]    [source]  [reset]   [freeze]
  HUSH      -         GATHER    SHAKE     HOLD
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The note: the click = C2 |
| **Size** | Spread: anticlockwise = all on the note (a slow chorus); noon = beating; clockwise = a cluster up to an octave either side |
| **Density** | How many oscillators play, 1 to 32 (the level stays even) |
| **Window** | How fast each one wanders: from barely moving to restless |
| **Overlap** | Waveform: triangle (soft, organ-like) → saw (bright, buzzy) |
| **Speed** | Breathing: each oscillator's level swells on its own. Between the two clicks a gentle shimmer; towards either end deeper, slower swells |
| **Start** | The chord the swarm gathers onto when Source is on: fifth, major, minor, sus4, maj7, min7, add9, fourths |
| **Blend** | Dry input ↔ swarm (equal power). It loads fully clockwise |

| Button / jack | Does | LED |
|---|---|---|
| **Source** (button or gate) | Gather: the swarm splits onto the chord's notes, gliding there (alt Density sets how slowly). Off = one cloud round the note again | on = chord |
| **Reset** (button or gate) | Shake: every oscillator jumps to a new place in the spread (a 0.3 s glide) | — |
| **Freeze** (button or gate) | Hold: the wandering and breathing stop where they are | on = held |
| **Record** (button or gate) | Hush: the swarm fades out over a few seconds; press again and it swells back | on = hushed |
| **File** | Not used | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Stereo width: mono → wide | wide |
| alt **Size** | Sub: a sine an octave below the note | off |
| alt **Density** | Gather time: how slowly the swarm moves onto the chord (0.3 to 20 s) | about 2 s |
| alt **Overlap** | Tone: a low-pass from 300 Hz to fully open | open |

Alt values only count once you move the knob.

## Quick start
1. Load `09_sc_swarm` and wait for SuperCollider to start (5 to 10 s): a soft cloud on C2.
2. Turn **Size** up slowly: from a gentle chorus into beating, then a cluster. Turn **Density** for more or fewer
   voices.
3. Press **Source**: the swarm gathers onto a chord. Turn **Start** for another one, alt **Density** for a slower
   gather.
4. **Overlap** clockwise for a brighter, buzzier swarm; **Window** for faster wandering; **Speed** past a click for
   deeper breathing.
5. **Freeze** holds it still; **Reset** shakes it; **Record** fades it away and back.

## Notes
- The output goes through a limiter at −0.5 dB (20 ms delay, as in the other SuperCollider patches).
- CPU, measured offline on the PC: about 11 % of a core, like sc_space. Not measured on the module yet.
