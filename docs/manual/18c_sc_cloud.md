# sc_cloud: granular clouds from the input

A SuperCollider granulator. A 4-second buffer records the input all the time, and grains read it back pitched
and scattered.

**Bank:** SuperCollider. Expect 5–10 s of silence while SuperCollider starts.

## Panel map
```
            [ speed ]            speed   = PITCH SCATTER  centre = none
 start                  size     start   = HOW FAR BACK  now .. 4 s ago
                                 size    = GRAIN LENGTH  20 .. 500 ms
 density    [ pitch ]  overlap   density = GRAINS PER SECOND
                                 overlap = STEREO SPREAD
       blend     window          window  = POSITION SCATTER
                                 blend   = DRY <-> WET
                                 pitch   = GRAIN PITCH, 1V/oct

 [record]  [file]  [source]  [reset]  [freeze]
                    REVERSE   BURST    HOLD BUFFER
```

## Controls
| Control | Does |
|---|---|
| **Audio in** | The source (stereo summed to mono) |
| **Start** | How far back the grains read (just recorded → 4 s ago) |
| **Size** | Grain length (20 – 500 ms) |
| **Density** | Grains per second (1 – 80); the last tenth gives random, dense grains instead of regular ones |
| **Window** | Position scatter around Start |
| **Pitch** + 1 V/oct | Grain pitch (click = the original pitch) |
| **Overlap** | Stereo spread of the grains |
| **Speed** | Pitch scatter: centre = none; either way = more random detune |
| **Blend** | Dry ↔ wet |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Stop recording: the buffer holds what it has | on = held |
| **Reset** (button or gate) | A burst of grains | — |
| **Source** (button or gate) | Reverse: grains play backwards | on = reverse |

## Quick start
1. Patch a melody in and load it; Blend fully wet, Density at noon, Size small.
2. Press **Freeze**, then play with Start and Pitch.
