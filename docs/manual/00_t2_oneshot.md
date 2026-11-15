# b_oneshot: Qu-Bit's four-voice sample player

Qu-Bit's built-in one-shot player. Four buttons (or gates) each fire a file from the stick, once, at its own
pitch. Good for drums and hits from a sequencer.

**Bank:** factory. This page is a summary from its code.

## Panel map
```
            [ speed ]            speed   = (not used)
 start                  size     start   = TUNE VOICE 1 (Record)
                                 size    = TUNE VOICE 3 (Reset)
 density    [ pitch ]  overlap   density = TUNE VOICE 2 (File)
                                 overlap = TUNE VOICE 4 (Freeze)
       blend     window          blend   = WHICH FOUR FILES
                                 window  = (not used)
                                 pitch   = PITCH OF ALL, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  VOICE 1   VOICE 2   STOP ALL  VOICE 3   VOICE 4
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Pitch of every voice: the click = the files' own pitch |
| **Start / Density / Size / Overlap** | Each voice's own tuning (voices 1 / 2 / 3 / 4): noon = no change, ±3 octaves |
| **Blend** | Which four files: the voices play four files in a row, and Blend slides that window along the stick's files |
| **Speed, Window** | Not used |

| Button / jack | Does | LED |
|---|---|---|
| **Record** (button or gate) | Fire voice 1 (the first of the four files) | flash |
| **File** (button or gate) | Fire voice 2 | flash |
| **Reset** (button or gate) | Fire voice 3 | flash |
| **Freeze** (button or gate) | Fire voice 4 | flash |
| **Source** (button or gate) | Stop every voice | flash |

A new trigger restarts that voice.

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start / Density / Size / Overlap** | How much of each file plays (voices 1–4): fully clockwise = all of it | all |
| alt **Window** | Sample-rate reduction (lo-fi) | off |
| alt **Record / File / Reset / Freeze** | Stop that voice | — |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Put four short sounds (a kick, snare, hat, clap) first in name order on the stick.
2. Load it and press Record, File, Reset and Freeze: one sound each.
3. Patch four gates from a drum sequencer into those jacks; tune each voice with its knob.

## Notes
- It doesn't use the audio inputs.
