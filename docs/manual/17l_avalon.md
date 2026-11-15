# AVALON: a morphing wavetable oscillator

Ian Hoogeboom's "Morphing Nebulaeum" (v1.5). It's a wavetable oscillator in the style of the Synthesis Technology
E350 Morphing Terrarium. A bank of 64 waves sits on an 8 × 8 grid: **Start** and **Density** morph across it
(X and Y), while **Speed** and **Size** run through all 64 in a line (Z). Out L plays the XY wave, out R the Z
wave, and **Blend** mixes them in five modes. An octave up and down, plus detune, thicken it.

It reads WaveEdit banks (`ROM A/B/C.wav`, `avalon.wav` on the stick); more at waveeditonline.com.

**Bank:** Csound user. Summarised from its author's manual (`avalon.pdf`, `avalon.txt`).

## Panel map
```
            [ speed ]            speed   = MORPH Z (coarse)
 start                  size     start   = MORPH X
                                 size    = MORPH Z FINE  (alt: range)
 density    [ pitch ]  overlap   density = MORPH Y
                                 overlap = OCTAVE UP/DOWN LEVEL (alt: mode)
       blend     window          window  = DETUNE  (alt: range)
                                 blend   = BLEND XY <-> Z  (alt: mode)
                                 pitch   = PITCH, 1V/oct  (alt: fine)

 [record]   [file]     [source]   [reset]   [freeze]
  NO MORPH Y NEXT BANK  NO MORPH Z            INSTANT DETUNE
  (alt: X)
 out L = XY   out R = Z
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Pitch |
| **Start** | Morph X across the grid |
| **Density** | Morph Y across the grid |
| **Speed** | Morph Z through all 64 waves (coarse: it steps a little) |
| **Size** | Fine Z morph around Speed (noon = none); alt Size sets its range (1 to 8 waves) |
| **Overlap** | Level of the octave-up and octave-down oscillators |
| **Window** | Detune those oscillators, from none to an octave |
| **Blend** | Blend between the XY and Z waves; the five modes are on alt Blend |

| Button / jack | Does |
|---|---|
| **Record** | No morphing on Y: Density picks clean waves (alt Record: the same for X) |
| **File** | Next wavetable bank on the stick |
| **Source** | No morphing on Z: Speed/Size pick clean waves |
| **Freeze** | Instant detune |

## Blend modes (alt Blend)
| Alt Blend | Left as Blend turns | Right as Blend turns |
|---|---|---|
| fully anticlockwise | XY, untouched | Z → XYZ → XY |
| 9 o'clock | XY → XYZ → Z | Z, untouched |
| noon | XY → XYZ | Z → XYZ |
| 3 o'clock | XY → XYZ → Z | Z → XYZ → XY |
| fully clockwise | XY → XYZ → Z | XY → XYZ → Z |

## Alt layer (hold Source)
| Control | Does |
|---|---|
| alt **Pitch** | Fine tune |
| alt **Size** | Range of the fine Z morph |
| alt **Overlap** | Octave levels: more up (anticlockwise), even (noon), more down (clockwise) |
| alt **Window** | Instant-detune range |
| alt **Blend** | Blend mode (above) |
| alt **Record** | No morphing on X |
| alt **Speed** | The Nebulae's input gain |

## Quick start
1. With `avalon.wav` on the stick, set Start, Density, Window and Overlap fully anticlockwise and Size at noon:
   a sine on out L.
2. Turn Start and Density to morph across the grid; Speed and Size for out R.
3. Raise Overlap for the octaves, then Window (or press Freeze) to detune them.
