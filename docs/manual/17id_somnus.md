# somnus: oscillators and a looper, dreaming through filter, resonator, echo and ambience

A stereo Csound ambient machine. Four sources (a sine, a supersaw, a wavetable read from the loop, and a
5-second looper) run through four effects in a row: filter, resonator, echo and ambience. A randomiser throws the
settings somewhere new, and you can undo it.

**Inspired by:** Befaco **Oneiroi**. Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = LOOP VARISPEED  stopped at noon,
 start                  size               clicks = 1x back/fwd, ends 2x
                                 start   = LOOP START
 density    [ pitch ]  overlap   size    = LOOP LENGTH  7.6 ms .. 5 s
                                 density = FILTER (File = mode)
       blend     window          overlap = ECHO
                                 window  = RESONATOR
                                 blend   = SOURCE  sine > saw > table > loop
                                 pitch   = OSCILLATORS, 1V/oct (click = C3)

 [record]  [file]       [source]   [reset]     [freeze]
  RECORD    FILTER MODE  INPUT IN   RANDOMISE   UNDO
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The oscillators (the click = C3) |
| **Blend** | Source: sine → supersaw → wavetable read from the loop → the loop itself |
| **Speed** | The loop's varispeed: stopped at noon; the clicks = normal speed backwards / forwards; the ends = 2× |
| **Start** | Where the loop starts in the 5 s buffer |
| **Size** | The loop's length: from 7.6 ms (a tiny loop is an oscillator, C3 at 1×) to the whole 5 s |
| **Density** | Filter cutoff (File = mode; alt Density = resonance) |
| **Window** | Resonator: three tuned resonances (root, fifth, octave; alt Pitch = tune); more = wetter and longer |
| **Overlap** | Echo: two taps (left at T, right at 1.5 T); more = wetter with more repeats (alt Overlap = time) |

| Button / jack | Does | LED |
|---|---|---|
| **Record** (button or gate) | Record into the loop: your input, layered over what's there (alt Size = how much of the old stays). With alt Record on, it records the output instead | on = recording |
| **Reset** (button or gate) | Randomise: the source, loop start and length, filter, resonator, echo and detune jump somewhere new, gliding there | — |
| **Freeze** (button or gate) | Undo the last randomise (it glides back exactly) | — |
| **Source** (button or gate) | Your input straight into the effects too | on = input |
| **File** | Filter mode: low-pass → band-pass → high-pass → comb | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Supersaw detune / the wavetable's place in the loop | some |
| alt **Size** | Sound on sound: how much of the old loop stays when you record | most |
| alt **Density** | Filter resonance | a little |
| alt **Overlap** | Echo time (50 ms to 1.5 s) | ~0.28 s |
| alt **Pitch** | Resonator tune (40 to 700 Hz) | ~125 Hz |
| alt **Window** | Ambience spacetime: small and dark → vast and bright | large-ish |
| alt **Blend** | Ambience amount | some |
| alt **Record** | Record the output instead of the input | off |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `somnus`: a sine on C3 into a little ambience. The loop starts full of white noise, as on the original.
2. Turn **Blend** through the sources; at the loop end, turn **Speed** and **Size**.
3. Press **Record** to catch your input into the loop; turn **Window** and **Overlap** for resonance and echoes.
4. Press **Reset** for somewhere new, **Freeze** to go back.

## Notes
- It's stereo throughout, with its own ambience, so it has no extra reverb.
- CPU, measured offline: under half the factory granular looper.
