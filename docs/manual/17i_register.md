# register: shift-register noise, from hiss to locked patterns

A Csound noise instrument: a shift register (a row of bits that shifts along at every clock tick, feeding back on
itself) clocked by **Pitch**, through a resonant low-pass filter. Fast, it's hiss or a pitched buzz. Slowed down,
it steps out rhythms and almost-melodies. **Freeze** locks whatever pattern it's playing into a loop. Let the
register move the filter (**Source**) and the noise turns into sequenced sweeps.

**Inspired by:** Hikari Instruments **Monos**, the shift-register noise synth. Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = MOTION  none between the
 start                  size               clicks: CW wanders, CCW steps
                                 start   = LENGTH  2 bits .. 24 bits
 density    [ pitch ]  overlap   size    = CUTOFF
                                 density = DIVIDE  raw > /2 > /4 > /8
       blend     window          overlap = CHANCE  repeat .. random
                                 window  = RESONANCE
                                 blend   = dry <-> register
                                 pitch   = CLOCK, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  STEREO    RANGE     STEP FILTER EXT CLOCK LOCK
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The clock. Its range is on File: **noise** (the click = 4186 Hz), **tone** (÷16, the click = 262 Hz), **pattern** (÷256, the click = 16 Hz) |
| **Start** | Length: 2 to 24 bits. Short registers repeat quickly (a pitched buzz in the noise and tone ranges); long ones are noise |
| **Overlap** | Chance: fully anticlockwise the register plays its own repeating sequence; clockwise, bits flip at random until it's fully random |
| **Density** | Divide: the raw bits → ÷2 → ÷4 → ÷8 (lower, chunkier, more rhythmic) |
| **Size** | Filter cutoff: 40 Hz to 16 kHz |
| **Window** | Resonance, up to a whistle |
| **Speed** | Motion. Between the two clicks: none. Clockwise past the click the clock and cutoff wander smoothly; anticlockwise they jump in steps. Faster towards the ends |
| **Blend** | Dry input ↔ register (it loads fully clockwise) |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Lock: no new bits; the register just turns, so its current pattern loops (Start sets the loop's length) | on = locked |
| **Reset** (button or gate) | External clock: each gate steps the register once. Pitch's clock takes over 2 s after the last gate | — |
| **Source** (button or gate) | The register steps the filter cutoff too: sequenced sweeps. alt Start = how far | on = stepping |
| **Record** (button or gate) | Stereo: the right channel gets its own register | on = stereo |
| **File** | Clock range: noise → tone → pattern (three go round) | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | How far Source steps the cutoff (up to ±2 octaves) | ±1 octave |
| alt **Size** | Drive into the filter | a little |
| alt **Window** | Motion depth | medium |
| alt **Blend** | Output level (±12 dB) | 0 dB |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `016_register`: noise at the noise range, a mid cutoff, some resonance.
2. Turn **Start** anticlockwise for a pitched buzz; play **Pitch** like an oscillator.
3. Press **File** twice for the pattern range: slow, stepped rhythms. Turn **Density** to divide them down.
4. Turn **Overlap** up for randomness, then press **Freeze** when you hear a pattern you like: it loops.
5. Press **Source** and raise **Window**: the register plays the filter as a sequence.
6. Patch a clock into **Reset** to step it in time with everything else.

## Notes
- The register is computed sample by sample. Its CPU rises with the clock speed; the noise range at full Pitch
  with Record on is the heaviest.
- CPU, measured offline: under half of the factory granular looper (0.85× at the very top with Record on).
