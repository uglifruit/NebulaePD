# prism: six resonant filters on a scale, rotating

A Csound stereo resonator. Your input rings six resonant filters, each tuned to a note of a scale. The odd bands
go left, the even ones right. Rotate them and the notes move round the filters, crossing from side to side. Each
filter morphs to its new note by crossfading to a twin already tuned there, quickly or slowly. There are 11 scales,
from chromatic to slendro and a drum's inharmonic modes.

**Inspired by:** 4ms **Spectral Multiband Resonator**. Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = AUTO-ROTATE  none between the
 start                  size               clicks; CW up, CCW down
                                 start   = SPREAD  1 .. 4 scale steps
 density    [ pitch ]  overlap   size    = Q  breathy -> ringing
                                 density = MORPH  5 ms .. 4 s
       blend     window          overlap = TILT  lows <-> highs
                                 window  = FREQ NUDGE  odds up, evens down
                                 blend   = MIX  dry <-> filters
                                 pitch   = TRANSPOSE (click = C3)

 [record]  [file]    [source]  [reset]   [freeze]
  SCALE     SCALE     LOCK      ROTATE    ROTATE
  ROTATION  (11)      (odds)    UP        DOWN
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Transpose: the scale's root (C3 at the click) |
| **Start** | Spread: how many scale steps apart the bands are, 1 to 4 |
| **Size** | Q: wide and breathy → narrow, ringing, singing |
| **Density** | Morph: how long a filter takes to move to its new note, 5 ms to 4 s |
| **Window** | Freq nudge: the odd bands go up and the even bands down, to 5 semitones (none at noon) |
| **Overlap** | Tilt: louder lows (anticlockwise) ↔ louder highs (clockwise), flat at noon |
| **Blend** | Mix: dry ↔ the filters |
| **Speed** | Auto-rotate: none between the clicks; clockwise rotates up, anticlockwise down, faster further out |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Rotate up one step | flashes |
| **Freeze** (button or gate) | Rotate down one step | flashes |
| **File** | Scale, eleven in turn: chromatic, major, minor, pentatonic, whole tone, harmonic series, raga Bhairav, 17-TET, slendro, Bohlen-Pierce, membrane (a drum's modes), then round again | — |
| **Source** | Lock (latching): the odd bands (left) hold their notes while the even ones rotate on | on = locked |
| **Record** | Scale rotation (latching). Off: the six notes rotate round the bands, so the chord stays and its notes swap sides. On: every band steps along the scale, so the chord climbs, wrapping at the top | on = scale rotation |
| **Pulse** out | A short gate on every rotation step | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Speed** | The Nebulae's input gain | — |

Your left and right inputs are mixed into all six filters; one cable is enough.

## Quick start
1. Load `prism` and play something rich into it (noise, drums, a pad).
2. **Size** up for ringing notes; **Pitch** sets the root; **Start** spreads the bands apart.
3. Press **Reset** or **Freeze** to rotate, or turn **Speed** past a click to rotate by itself. **Density** sets how
   slowly each filter glides to its new note.
4. Press **File** for another scale; latch **Record** to make the chord climb instead of swap sides.
5. **Window** detunes the two sides against each other; **Overlap** tilts towards the lows or highs.

## Notes
- Rotation steps that come faster than the morph wait for it, then jump to the latest note.
- Patch **Pulse** to an envelope or a drum: it fires on every rotation.
- CPU, measured offline: about two fifths of the factory granular looper.
