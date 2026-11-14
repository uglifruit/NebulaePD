# morph — spectral morphing and cross-synthesis

A Csound instrument that melts one sound into another. **A** is what you play into the left input. **B** is a file
from the stick (or the right input, or a few seconds of A you just grabbed). Blend morphs between their spectra:
not a crossfade, but the partials of one sliding into the partials of the other. Overlap turns it into
cross-synthesis: the notes of A sung with the colour of B. Freeze holds a moment of A while B moves on.

It's in the **Csound user bank** as `007_morph` (orange page, File button).

## Panel map
```
            [ speed ]            speed   = B SPEED  centre frozen,
 start                  size               clicks 1x, ends 4x
                                 start   = B POSITION (scrubs)
 density    [ pitch ]  overlap   size    = B REGION it loops in
                                 density = MIX  dry <-> morph
       blend     window          overlap = CROSS  morph -> A's notes
                                           in B's colour
                                 window  = BLUR  none -> 2 s
                                 blend   = MORPH  A <-> B
                                 pitch   = TRANSPOSE, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  GRAB A    NEXT      B=RIGHT   B START   HOLD A
```

## Controls
| Control | Does |
|---|---|
| **Blend** | Morph: fully anticlockwise = A, fully clockwise = B, between = their spectra interpolated (partials glide from one to the other) |
| **Overlap** | Cross: anticlockwise = the plain morph. Turning up crossfades to cross-synthesis: A's partials (its notes and rhythm) under B's spectral envelope (its colour). Talk into A with a pad as B for a vocoder-like effect. A makeup gain rises with it (cross-synthesis is quiet) |
| **Window** | Blur: the morphed spectrum smoothed over time, none to 2 s. Changes melt into each other |
| **Density** | Mix: dry input ↔ morph (equal power). It loads fully clockwise |
| **Pitch** + 1 V/oct | Transpose the morph, ±3 octaves; the click = none |
| **Speed** | B's speed through its file: centre = frozen in place, the clicks = 1× (anticlockwise = backwards), the ends = 4×. Between the centre and a click = slower, down to 1000× slower. It loads on the forward click |
| **Start** | Where B plays from (turning it scrubs) |
| **Size** | The region B loops in, from Start; fully clockwise = to the end |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Hold A's spectrum: the moment of the input at the press stays, B keeps moving | on = frozen |
| **Reset** (button or gate) | B back to Start (a short soft dip) | — |
| **Record** (button or gate) | B = the last few seconds of A (alt Size sets how many). It's always listening, so press it after something good. Lasts until File is pressed | — |
| **File** | Next stick file for B (and back to files after a Record) | — |
| **Source** | B = the right input, live (overrides the file or grab while it's on) | on = right input |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Size** | Grab length: 2 – 30 s | ≈ 10 s |
| alt **Window** | Tone: dark (−18 dB treble) ↔ bright (+6 dB); noon = flat | flat |
| alt **Overlap** | Reverb size | medium |
| alt **Blend** | Reverb amount | a little |
| alt **Speed** | Not used (it's the Nebulae's input gain) | — |
| the others | Not used | — |

## Quick start
1. Put a few files on the stick (pads, voices, textures). Load `007_morph`. Play something into the left input.
2. Turn **Blend** slowly from anticlockwise to clockwise: your sound turns into the file.
3. Bring **Overlap** up: your notes now play with the file's colour. Try a voice in A and a chord pad as B.
4. Press **Freeze** on a chord in A and sweep Blend: the frozen chord morphs against a moving file.
5. Press **Record**, play something else: the morph is now between you and your own past.

## Notes
- Both sounds go through a 2048-point phase vocoder, so the morph lags the input by about 40 ms. Density's dry
  side is not delayed.
- Files at any sample rate play at the right speed and pitch. Stereo files: B uses the left channel.
- CPU, measured offline: about 0.8× the factory granular looper.
