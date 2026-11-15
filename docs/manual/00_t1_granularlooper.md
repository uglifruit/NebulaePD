# a_granularlooper: Qu-Bit's granular looper

Qu-Bit's own instrument, built into the firmware. It plays audio files from the stick, or loops what you record
from the inputs, either cleanly or cut into grains (short overlapping fragments) that you can scatter, stretch,
pitch and freeze.

**Bank:** factory (always the first button). Qu-Bit's Nebulae manual covers it in depth; this page is a summary
from its code.

## Panel map
```
            [ speed ]            speed   = PLAYBACK SPEED  noon = stopped,
 start                  size               clicks = 1x fwd / back, ends 4x
                                 start   = LOOP START
 density    [ pitch ]  overlap   size    = LOOP SIZE
                                 density = GRAIN RATE
       blend     window          overlap = GRAIN SIZE
                                 window  = GRAIN SHAPE
                                 blend   = CLEAN <-> GRAINS
                                 pitch   = PITCH, 1V/oct (click = original)

 [record]  [file]    [source]  [reset]   [freeze]
  RECORD    NEXT FILE  LIVE IN   RESTART   FREEZE
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Pitch of the playback and grains: the click = the original pitch, ±2 octaves and more |
| **Speed** | Playback speed and direction. Noon = stopped; the right click = normal speed forwards, the left click = backwards; up to 4× at the ends |
| **Start** | Where the loop starts in the file or recording |
| **Size** | How long the loop is (fully clockwise = to the end) |
| **Density** | Grain rate: from a grain every few seconds to thousands a second |
| **Overlap** | Grain size: short clicks → long, overlapping grains |
| **Window** | Grain shape: soft (Gaussian) → … → square-edged, morphing through seven shapes |
| **Blend** | Files: clean playback ↔ grains. Live input (Source on): clean loop → dry input (noon) → grains |

| Button / jack | Does | LED |
|---|---|---|
| **Source** (button or gate) | Live input instead of the stick files | on = live |
| **Record** (button or gate) | Live: record the input into the loop. Record again to overdub | on = recording |
| **File** (button or gate) | Next file on the stick (files mode). On live input it's ignored | flashes |
| **Reset** (button or gate) | Restart the loop from Start. The light flashes at the end of every loop (with the EOL gate) | end of loop |
| **Freeze** (button or gate) | Freeze: playback stops where it is and the grains keep playing that moment | on = frozen |

## Alt layer (hold Source)
| Control | Does |
|---|---|
| alt **Start** | Random grain position (scatter) |
| alt **Size** | Stereo spread of the grains |
| alt **Density** | Grain timing: regular → random |
| alt **Overlap** | Random grain size |
| alt **Window** | Random grain drop-outs |
| alt **Pitch** | Random grain pitch |
| alt **Blend** | The input frequency-modulates the grains |
| alt **Speed** | The Nebulae's input gain |
| alt **Record** | Overdub keeps the loop's length (layers into it rather than extending it) |
| alt **Freeze** | Grain sync: with Density fully anticlockwise, every gate into the Source jack fires a grain |
| alt **File** | File order: forwards → backwards → random (the File light fades up, down, or flickers) |

## Hold File and press…
| Combination | Does |
|---|---|
| File + **Reset** | Clear the recorded loop |
| File + **Freeze** | Save the loop to the stick as `neb_buffer_N.wav` (the Freeze and Record lights blink while it writes) |
| File + **Source** | Reload the instrument (rescans the stick's files) |

## Quick start
1. Load it with some `.wav` or `.flac` files on the stick: the first file plays.
2. Turn **Blend** clockwise for grains; **Density** and **Overlap** shape them; **Window** softens or sharpens.
3. Turn **Speed** to noon to stop, past a click to play backwards; **Freeze** holds a moment.
4. Press **Source** for live input, then **Record** to catch a loop.

## Notes
- The firmware gives the extras above (the alt File order, grain sync, the Reset light, red Speed lights while
  recording, the hold-File save) only to an instrument named exactly `a_granularlooper`. Copies with other names,
  such as `bt_storyteller`, lack some of them.
- The record buffer holds 300 seconds.
