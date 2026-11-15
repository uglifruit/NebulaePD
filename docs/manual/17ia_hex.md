# hex: a tonic spilled into a time/filter experiment

A Csound drone instrument. A triangle "tonic" and its subharmonics (the tones) pour into a time/filter experiment:
a clocked delay that grows grainy and noisy as it slows, with a filter and an absorber in its loop. An agitation
wave shakes the filter, and touches route the experiment back into itself.

**Inspired by:** Make Noise **Strega** (designed with Alessandro Cortini). Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = AGITATION  none between
 start                  size               the clicks
                                 start   = TONES  tri > subs > folded
 density    [ pitch ]  overlap   size    = TIME  CCW slow+noisy, CW short
                                 density = DECAY  a handful .. infinity
       blend     window          overlap = ABSORB
                                 window  = FILTER
                                 blend   = TONES <-> EXPERIMENT
                                 pitch   = TONIC, 1V/oct (click = C3)

 [record]      [file]  [source]   [reset]        [freeze]
  INTERFERENCE  HOLD    INPUT IN   RESTART AGIT.  ACTIVATE
  (hold)                                          (hold)
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The tonic: the tones' pitch (the click = C3) |
| **Start** | Tones: triangle → + a subharmonic an octave down → + another (a twelfth down) → folded → sharp |
| **Size** | Time: the rate the tones drip into the filter. Clockwise = short and clean (a pitched comb); anticlockwise = long, slow and grainy, with an avalanche of noise round 9 o'clock |
| **Density** | Decay: the experiment's iterations, from a handful to infinity |
| **Window** | Filter: a low-pass on every pass of the experiment |
| **Overlap** | Absorb: a high-pass on every pass |
| **Speed** | Agitation. Between the clicks: none. Past them a rise-and-fall wave, from one a minute up to audio rate, moving the Filter. Clockwise it rises slowly and falls fast; anticlockwise the opposite |
| **Blend** | The tones as they are ↔ the experiment |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Activate: while held (or while a gate is high) the tones pour into the experiment | on while held |
| **Record** (button or gate) | Interference: while held, the experiment bends the tonic's pitch | on while held |
| **Reset** (button or gate) | Restart the agitation wave | — |
| **Source** (button or gate) | Your input pours into the experiment too | on = input |
| **File** | Hold: the experiment rings for ever and takes nothing new; press again to release | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Activation constant: how much the tones always pour in, untouched | half |
| alt **Size** | Activation interference: the experiment's own level lets more in (it plays itself) | off |
| alt **Density** | Tonic interference: the experiment always bends the tonic | off |
| alt **Pitch** | Time modulation: the subharmonics wobble Time | a little |
| alt **Overlap** | How far the agitation moves the Filter | some |
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount (a stereo reverb after) | a little |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `hex`: the tones pour into the experiment at half strength.
2. Turn **Size** anticlockwise towards 9 o'clock for the avalanche; **Density** for longer decays.
3. Turn **Window** and **Overlap** to shape it; **Speed** past a click to agitate.
4. Hold **Freeze** to pour more in; hold **Record** to let it bend the pitch. Press **File** to hold what you have.

## Notes
- Time is a true echo time (tested): a burst at Size 0.3 echoes 0.19 s later.
- CPU, measured offline: about 40 % of the factory granular looper, reverb included.
