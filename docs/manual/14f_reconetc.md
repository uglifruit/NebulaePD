# ReconetC!: a generative dual sample slicer

Radek Rudnicki's Pd instrument. Two slicers cut up samples according to four small algorithms (chosen in zones),
with a probability for each step and repeats, through two stereo reverbs. It reads six specific samples from the
stick: `Atmos`, `Kick`, `Piano1`, `Piano2`, `SnareCrickets` and `Stabs` (.wav). Keep those names to use your own
material.

**Bank:** Pd. Summarised from its author's notes (`Reconetc redme.txt` and the panel guide).

## Panel map
```
            [ speed ]            speed   = SLICER 1 SPEED / PITCH
 start                  size     start   = ALGORITHM (zones 1-4; 5 = free loops)
                                 size    = SLICER 1 VOLUME
 density    [ pitch ]  overlap   density = TEMPO (internal clock)
                                 overlap = SLICER 2 VOLUME
       blend     window          blend   = PROBABILITY (% of slicing)
                                 window  = REPEATS (% of repetition)
                                 pitch   = SLICER 2 SPEED / PITCH

 [record]  [file]    [source]  [reset]   [freeze]
            SAMPLE 1                RESTART  (ext clock in, see alt Record)
```

## Controls
| Control | Does |
|---|---|
| **Start** | Algorithm: four zones, each a different slicing algorithm; the fifth (fully clockwise) is free-running loops |
| **Density** | Tempo: the internal clock's rate |
| **Speed** | Slicer 1's speed / pitch |
| **Pitch** | Slicer 2's speed / pitch |
| **Size** | Slicer 1's volume |
| **Overlap** | Slicer 2's volume |
| **Blend** | Probability that each clock step slices |
| **Window** | How often steps repeat |

| Button / jack | Does |
|---|---|
| **File** | Next sample for slicer 1 (if a sample doesn't load, press again) |
| **Reset** | Restart the sequence from the first slice |

## Alt layer (hold Source)
| Control | Does |
|---|---|
| alt **Blend** | Reverb on slicer 1 |
| alt **Window** | Reverb on slicer 2 |
| alt **Size** | Level of the left input, sent through the reverb |
| alt **File** | Next sample for slicer 2 |
| alt **Record** | External clock on: then gates into **Freeze** clock it |

## Quick start
1. Make sure the six samples are on the stick, then load it: slices start playing.
2. Turn Start through the zones for different algorithms; Density for the tempo.
3. Blend and Window for probability and repeats; Speed and Pitch to re-pitch the two slicers.
