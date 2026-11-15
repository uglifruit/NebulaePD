# Bowed Drone: an evolving bowed string

Collin Russell's Csound drone (v1.1, ported from the Nebulae V1 by Chris Erin). A bowed-string model through a
Moog-style ladder filter, with vibrato and glide.

**Bank:** Csound user. Summarised from its diagram (`Bowed_Drone_Diagram.pdf`) and its code.

## Panel map
```
            [ speed ]            speed   = FILTER RESONANCE
 start                  size     start   = VIBRATO RATE
                                 size    = VIBRATO DEPTH
 density    [ pitch ]  overlap   density = BOW PRESSURE
                                 overlap = BOW POSITION
       blend     window          blend   = FILTER CUTOFF
                                 window  = GLIDE
                                 pitch   = PITCH, 1V/oct

 [record]
  BOW ON
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Pitch: 64 Hz to 2 kHz across the knob (the click is about 512 Hz) |
| **Start** | Vibrato rate (0 – 10 Hz) |
| **Size** | Vibrato depth |
| **Density** | Bow pressure (smooth → scratchy) |
| **Overlap** | Bow position on the string |
| **Blend** | Filter cutoff (20 Hz – 6 kHz) |
| **Speed** | Filter resonance |
| **Window** | Glide between pitches |

| Button / jack | Does | LED |
|---|---|---|
| **Record** (button or gate) | The bow: on = sounding, off = silent | on = bowing |

The other buttons and the alt layer do nothing.

## Quick start
1. Load it and press **Record**: the string sounds.
2. Turn Blend up to open the filter; Density and Overlap change the bowing.
3. Add vibrato with Start and Size; patch a sequencer into Pitch, with Window for glide.

## Notes
- Mono: the sound comes out of the left output only.
