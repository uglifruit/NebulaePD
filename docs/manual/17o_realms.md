# Realms: travel through rooms of sound

Robert Pabst (Cinematic Laboratory) and Ian Hoogeboom's ambient instrument (v1.0). Up to seven "rooms", each a
pair of looping ambient recordings, which you move through with **Speed**, like walking from a forest to a city.
Sounds sit **near** (dry) or **far** (filtered, reverberant), and you can rotate the room around you. Your input
can be placed in the room too.

The rooms are the stick's sound files in name order, two per room (`11_…`, `12_…`, `21_…` … `72_…`). Loading can
take a minute and a half with 75 MB of files.

**Bank:** Csound user. Summarised from its author's manual (`realms.pdf`, `realms.txt`).

## Panel map
```
            [ speed ]            speed   = ROOM
 start                  size     start   = INPUT NEAR <-> FAR
                                 size    = SWAP FIRST / SECOND near-far
 density    [ pitch ]  overlap   density = INPUT PANNING
                                 overlap = ROOM ROTATION
       blend     window          blend   = INPUT <-> ROOMS
                                 window  = FIRST <-> SECOND
                                 pitch   = PITCH OF ALL, 1V/oct

 [record]  [file]  [source]       [reset]       [freeze]
                    CLOCK/RANDOM   REVERB TYPE   NO ROTATION
 pulse out = a clock from the loops, or random pulses
```

## Controls
| Control | Does |
|---|---|
| **Speed** | Room: anticlockwise = the first, clockwise = the last; the rooms crossfade |
| **Pitch** + 1 V/oct | Pitch of all the rooms |
| **Start** | The input: near ↔ far |
| **Size** | Which file is near: anticlockwise = the first near, the second far; clockwise swaps them |
| **Density** | Input panning |
| **Overlap** | Room rotation: turns near/far into left/right (like turning your head) |
| **Blend** | Input ↔ rooms (a crossfade: both full at noon) |
| **Window** | First ↔ second file (a crossfade: both full at noon) |

| Button / jack | Does |
|---|---|
| **Source** | Pulse mode: off = a clock from the shortest loop; on = random pulses at loop restarts |
| **Reset** | Reverb type: Freeverb / a feedback delay network |
| **Freeze** | Rotation off (as Overlap at noon) |
| **Pulse** out | The clock or the random pulses |

## Alt layer (hold Source)
| Control | Does |
|---|---|
| alt **Pitch** | Output gain (×0 – ×4; noon = ×1) |
| alt **Start** | Near ↔ far balance |
| alt **Size** | Reverb tail (none → very long; also the pre-delay) |
| alt **Density** | The far sound's filter cutoff |
| alt **Overlap** | Reverb damping |
| alt **Window** | The far reverb's dry/wet |
| alt **Blend** | Pulses per loop (clock mode) or pulse length (random mode) |
| alt **Speed** | Input gain |
| alt **Record** | Stereo / 2× mono input |
| alt **File** | Gate / two triggers on the pulse out |
| alt **Reset** | Reverb pre-delay on/off |
| alt **Freeze** | Continuous rotation past the ends of Overlap |

## Quick start
1. Put the room files on the stick and load it; wait for the cyan lights to finish.
2. After loading, hold Source and press Pitch to reset the alt settings.
3. Turn Speed slowly to travel; Window and Size to rebalance each room; Overlap to rotate it.
4. Blend brings your input in; Start places it near or far.

## Notes
- If it's silent but Freeze still toggles, it's still loading (or alt Pitch is fully anticlockwise).
- Hold File and press Source to reload the files after swapping the stick.
