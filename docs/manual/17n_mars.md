# Mars Affects: filter, VCA, delay and shimmer reverb

Ian Hoogeboom's effect chain (v1.5.1): a DJ-style filter (Korg 35), a VCA, a stereo delay (free-running or
clocked, with skew between left and right) and a reverb with an "alien shimmer" (an LFO or random chorus/flanger
in the tail), plus ducking.

**Bank:** Csound user. Summarised from its author's manual (`mars_affects.pdf`, `mars_affects.txt`).

## Panel map
```
            [ speed ]            speed   = DJ FILTER  LP <- noon -> HP
 start                  size     start   = DELAY TIME / CLOCK DIVISION
                                 size    = REVERB SIZE
 density    [ pitch ]  overlap   density = DELAY AMOUNT
                                 overlap = REVERB AMOUNT (past noon: wetter)
       blend     window          blend   = INPUT PANNING / BALANCE
                                 window  = VCA / OUTPUT GAIN (CW = open)
                                 pitch   = SHIMMER  CCW random, CW LFO

 [record]    [file]  [source]   [reset]          [freeze]
  MUTE INPUT  DUCK    PRE-DELAY  CLOCK IN / TAP   MAX WET
 pulse out = the delay's clock
```

## Controls
| Control | Does |
|---|---|
| **Start** | Clocked: a division of the clock. Free-running: the delay time (very short, Karplus-like, to 3 s) |
| **Density** | Delay level |
| **Size** | Reverb size (it also sets the pre-delay's length) |
| **Overlap** | Reverb level; past noon the dry is taken out of the reverb, fully clockwise = 100 % wet |
| **Pitch** | Shimmer amount: noon = plain reverb, anticlockwise = random, clockwise = LFO |
| **Speed** | DJ filter: low-pass anticlockwise, high-pass clockwise |
| **Blend** | Input panning (2× mono mode: the left/right input balance) |
| **Window** | VCA / output gain. With nothing in its CV jack, set it fully clockwise |

| Button / jack | Does |
|---|---|
| **Record** | Mute the input: the effects ring out |
| **File** | Duck the effects (and partly the dry) |
| **Source** | Reverb pre-delay on/off (0 – 200 ms, with Size) |
| **Reset** | Clock in, or tap the tempo (clocked mode) |
| **Freeze** | Maximum wet: the most delay into reverb, the most reverb, 100 % wet |
| **Pulse** out | The delay's clock (divided, when clocked) |

## Alt layer (hold Source)
| Control | Does |
|---|---|
| alt **Start** | Delay skew between left and right (anticlockwise = none) |
| alt **Density** | Delay feedback |
| alt **Size** | Dry into the reverb |
| alt **Overlap** | Delay into the reverb |
| alt **Pitch** | Shimmer depth |
| alt **Blend** | Shimmer LFO / random speed |
| alt **Window** | Ducking release time (0 – 2 s) |
| alt **Speed** | Input gain |
| alt **Record** | Stereo / 2× mono input (2× mono: the filter and VCA act on the left only) |
| alt **File** | Ducking VCA |
| alt **Reset** | Clocked / free-running delay |
| alt **Freeze** | 100 % wet (no dry at the output) |

## Quick start
1. Patch a sound in, set **Window fully clockwise** (or it's silent), Start, Density, Size and Blend at noon,
   Overlap at 10 o'clock.
2. Turn Density for the delay, Overlap for the reverb, Pitch for shimmer, Speed for the filter.
3. For clocked echoes: alt Reset on, then a clock (or taps) into Reset; Start picks the division.
