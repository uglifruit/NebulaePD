# horizon: a feedback loop you play into

A Csound feedback effect. Your input is driven into a loop. The loop's own output comes round again through bass
and treble boosts and an overdrive. Below about 2 o'clock on Feedback it colours and lengthens what you play;
above, it rings by itself at the loop's pitch, and your playing pushes it about. Your input's dynamics can open
the loop or duck it. A stereo reverb follows.

**Inspired by:** Bastl Instruments / Casper Electronics **Dark Matter**. Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = WOBBLE  none between the
 start                  size               clicks; wow / random
                                 start   = DRIVE  -6 .. +30 dB
 density    [ pitch ]  overlap   size    = BASS boost (with overdrive)
                                 density = TREBLE boost (with overdrive)
       blend     window          overlap = DYNAMICS  off at noon:
                                           CW opens, CCW ducks
                                 window  = FEEDBACK  rings past ~2 o'clock
                                 blend   = X-FADE  clean <-> loop
                                 pitch   = the loop's PITCH (click = C4)

 [record]  [file]    [source]  [reset]   [freeze]
  CLEAN     VCA       POLARITY  ENVELOPE  HYPER
  pre/post  in/out    (inverted) slow/fast (drive)
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The loop's pitch (its delay): C4 at the click, C1 to C6. Where it rings by itself, this is the note |
| **Start** | Drive: your input's level into the loop, −6 to +30 dB, soft-clipped |
| **Size** | Bass boost in the loop (0 to +18 dB, below 180 Hz), with overdrive: it rumbles |
| **Density** | Treble boost in the loop (0 to +18 dB, above 3.5 kHz), with overdrive: it screams higher |
| **Window** | Feedback: how much goes round again. It rings by itself from about 2 o'clock |
| **Overlap** | Dynamics, bipolar, off at noon. Clockwise, your playing opens the loop (silence shuts it). Anticlockwise, your playing ducks it, so it screams in the gaps |
| **Blend** | X-fade: the clean signal ↔ the loop |
| **Speed** | Wobble: the loop's pitch moves. None between the clicks; clockwise a smooth wow, anticlockwise random, faster further out |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** | Hyper (latching): +12 dB more drive and a second, harder clip | on = hyper |
| **Reset** | The envelope's decay (latching): slow (off) or fast (on) | on = fast |
| **Source** | Polarity (latching): the loop's feedback inverted, so it rings an octave down, hollow (odd harmonics) | on = inverted |
| **Record** | The clean signal (latching): before the drive (off) or after it (on) | on = after |
| **File** | The VCA: in the loop (Dynamics works the feedback), or out (Dynamics works the output level instead) | — |
| **Pulse** out | A gate from your input's envelope: high while you play (above −20 dB), until it decays | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount (a stereo reverb after) | a little |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `horizon`, play into it and turn **Blend** towards the loop.
2. Raise **Window** (Feedback) past 2 o'clock: it rings by itself. **Pitch** sets the note.
3. **Size** and **Density** boost the bass and treble in the loop: it rumbles or screams.
4. Turn **Overlap** clockwise so only your playing opens the loop, or anticlockwise so your playing ducks it.
5. **Freeze** for hyper drive, **Source** for an octave down, **Speed** off the clicks to make it wobble.

## Notes
- A whisper of noise in the loop lets it start by itself, with nothing plugged in.
- Patch **Pulse** into something else's gate: it follows your playing.
- CPU, measured offline: about two fifths of the factory granular looper, reverb included.
