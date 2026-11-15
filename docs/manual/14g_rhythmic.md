# Rhythmic Chords: Qu-Bit's chord example

Qu-Bit's Pd example (by Stephen Hensley, also in the firmware): chords on V/oct, played as a rhythm, a pad, or a
mix of both, with a clock you can divide or multiply.

**Bank:** Pd. There's no manual; this page is a summary traced from the patch.

## Panel map
```
            [ speed ]            speed   = CLOCK DIVIDE / MULTIPLY
 start                  size     start   = ATTACK
                                 size    = RELEASE
 density    [ pitch ]  overlap   density = WAVE TYPE (and random rate)
                                 overlap = CHORD TYPE
       blend     window          blend   = RHYTHM <-> PAD
                                 window  = GLIDE
                                 pitch   = ROOT, 1V/oct

 [record]       [file]  [source]  [reset]    [freeze]
  RANDOM CLOCK                     CLOCK IN
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The chord's root |
| **Overlap** | Chord type |
| **Density** | Wave type; it also sets the random trigger rate |
| **Start** | Attack |
| **Size** | Release |
| **Window** | Glide between chords |
| **Blend** | Rhythmic ↔ pad mix |
| **Speed** | Clock division / multiplication (nine steps) |

| Button / jack | Does |
|---|---|
| **Reset** (gate) | Clock input: the chords follow your clock |
| **Record** | A pseudo-random internal clock on/off (starts at 250 ms) |
| File, Source, Freeze | Nothing found in the patch (Freeze toggles a value nothing reads) |

## Quick start
1. Load it and patch a clock into Reset.
2. Pitch for the root, Overlap for the chord type, Blend between rhythm and pad.
3. Speed divides or multiplies the clock; Start and Size shape each chord.
