# Plasma Membrane: a phase-modulation voice

Eli Pechman's Pd voice. Two banks of four harmonics, each tied to the fundamental by a numerator/denominator ratio,
phase-modulate the fundamental. **Speed** scans through the harmonics. Its left half uses the left-hand (blue)
controls and its right half the right-hand (green) ones, as the two Speed lights show. Out L is the fundamental,
out R the harmonics mix.

**Bank:** Pd. Summarised from its author's manual (`Plasma_Membrane_Manual.pdf`).

## Panel map
```
            [ speed ]            speed   = HARMONIC SELECTION (left half
 start                  size               = bank 1, right half = bank 2)
                                 pitch   = PITCH
 density    [ pitch ]  overlap   start / density  = bank 1 RATIO num / den
                                 size / overlap   = bank 2 RATIO num / den
       blend     window          blend   = bank 1 MODULATION
                                 window  = bank 2 MODULATION

 [record]   [file]    [source]  [reset]   [freeze]
  B1 RANGE   B1 ROTATE WAVE      B2 ROTATE B2 RANGE
 in L = phase mod in   in R = sync   out L = fundamental   out R = harmonics mix
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The fundamental |
| **Speed** | Scans the harmonics: left half through bank 1, right half through bank 2 |
| **Start / Density** | Bank 1's harmonic ratio: numerator / denominator |
| **Size / Overlap** | Bank 2's harmonic ratio: numerator / denominator |
| **Blend** | Bank 1's modulation amount |
| **Window** | Bank 2's modulation amount |

| Button / jack | Does |
|---|---|
| **Record** / **Freeze** | Harmonic ratio range, bank 1 / bank 2 |
| **File** / **Reset** | Rotate the harmonics, bank 1 / bank 2 |
| **Source** | Wave select |
| **in L** | Phase modulation input |
| **in R** | Sync input |

## Alt layer (hold Source)
| Control | Does |
|---|---|
| alt **Speed** | Phase modulation amount from in L (both outputs) |
| alt **Pitch** | Pitch offset (both outputs) |
| alt **Start / Size** | Mix harmonics 1 & 2 (bank 1 / bank 2), harmonics output only |
| alt **Density / Overlap** | Mix harmonics 3 & 4 (bank 1 / bank 2) |
| alt **Blend / Window** | Left of noon: phase-modulate the main out; right: mix with it. Noon = off |

The alt buttons do nothing.

## Quick start
1. Load it: listen to out L (the fundamental) and out R (the harmonics).
2. Turn Speed through its left half and play with Start, Density and Blend; then the right half with Size,
   Overlap and Window.
3. Press File or Reset to rotate the harmonics; set alt Blend / alt Window to noon to switch the alt effect off.
