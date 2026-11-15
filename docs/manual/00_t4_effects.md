# d_effects: Qu-Bit's delay and reverb

Qu-Bit's built-in effect: a stereo delay into a reverb. Qu-Bit marks it as a work in progress, so some controls do
nothing (and its own comments name a few controls wrongly; this page follows the code).

**Bank:** factory. This page is a summary from its code.

## Panel map
```
            [ speed ]            speed   = (not used)
 start                  size     start   = DELAY TIME  10 ms .. 2 s
                                 size    = DELAY FEEDBACK
 density    [ pitch ]  overlap   density = REVERB TIME
                                 overlap = REVERB BRIGHTNESS
       blend     window          window  = REVERB SEND
                                 blend   = DRY <-> DELAY
                                 pitch   = (not used)

 [record]  [file]    [source]  [reset]   [freeze]
                      MUTE IN
```

## Controls
| Control | Does |
|---|---|
| **Start** | Delay time: 10 ms – 2 s (it glides when you turn it) |
| **Size** | Delay feedback |
| **Blend** | Dry ↔ delay |
| **Window** | How much goes into the reverb |
| **Density** | Reverb time |
| **Overlap** | Reverb brightness (damping 800 Hz – 15 kHz) |
| **Pitch, Speed** | Not used |

| Button / jack | Does | LED |
|---|---|---|
| **Source** (button or gate) | Mute the input (the delay and reverb ring out) | on = muted |
| Other buttons | Not used | — |

## Quick start
1. Patch a sound into the inputs and load it.
2. **Start** for the delay time, **Size** for repeats, **Blend** to bring them in.
3. Turn **Window** up for reverb, then **Density** and **Overlap** to shape it.

## Notes
- The output is clipped gently above about −1 dB.
