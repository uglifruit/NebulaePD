# cauldron: your sound poured into a time/filter experiment

A Csound effect. Your input drips into the same time/filter experiment as hex: a clocked delay that grows grainy
and noisy as it slows, with a filter and an absorber in its loop. Its own activity can be patched back into it,
on the buttons, for wow and flutter, noise, and wind.

**Inspired by:** Make Noise **Bruxa** (with Alessandro Cortini). Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = TIME MODULATION  none between
 start                  size               the clicks
                                 start   = INPUT LEVEL (it saturates)
 density    [ pitch ]  overlap   size    = SELF-PATCH DEPTH
                                 density = DECAY  a handful .. infinity
       blend     window          overlap = ABSORB
                                 window  = FILTER
                                 blend   = DRY <-> EXPERIMENT
                                 pitch   = TIME, 1V/oct

 [record]      [file]      [source]  [reset]       [freeze]
  WOW&FLUTTER   TIME RANGE  NOISE     WIND & WAVE   HOLD
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Time. 20 ms at the click; with Decay up the experiment rings at 1 / Time, so you can play it from a sequencer (50 Hz at the click, tested to 0.4 %). Slower = longer, grainier, noisier |
| **Start** | Input level into the experiment (×0.25 to ×4, unity at noon; it saturates) |
| **Size** | How deep the self-patches on Record, Source and Reset go |
| **Density** | Decay: a handful of repeats to infinity |
| **Window** | Filter: a low-pass on every pass |
| **Overlap** | Absorb: a high-pass on every pass |
| **Speed** | Time modulation. Between the clicks: none. Clockwise a smooth wow; anticlockwise a random flutter |
| **Blend** | Dry ↔ the experiment |

| Button / jack | Does | LED |
|---|---|---|
| **Record** (button or gate) | Wow & Flutter: the experiment's activity stretches Time | on = on |
| **Source** (button or gate) | Noise: its interference shakes Absorb | on = on |
| **Reset** (button or gate) | Wind & Wave: its interference pours back into the input, and its activity opens the Filter | on = on |
| **Freeze** (button or gate) | Hold: it rings for ever and takes nothing new | on = held |
| **File** | Time range: short (0.9 ms to 0.45 s) ↔ long (×8, to 3.6 s) | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount (a stereo reverb after) | a little |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Patch a sound in and load `cauldron`; Blend at noon.
2. Turn **Pitch** for the time, **Density** for repeats, **Window** and **Overlap** to shape them.
3. Press **File** for long times, then turn Pitch down for the grainy, noisy end.
4. Try **Record** (wow), **Source** (noise) and **Reset** (wind) with **Size** up; **Freeze** holds it all.

## Notes
- Absorb set close to a low note pulls that note's pitch: it's cutting the note's own fundamental.
- CPU, measured offline: under 40 % of the factory granular looper, reverb included.
