# veil: a drone voice with six algorithms, formants, overtones and motion

A Csound drone voice and effect. Six algorithms (on **File**) share the same four timbre knobs:
- **Start** = overtones;
- **Size** = formant;
- **Density** = spread;
- **Window** = cross-mod.

**Speed** sets them drifting on their own, **Reset** throws them somewhere new and glides there, and **Freeze**
holds everything still. **Overlap** blurs it into a diffuse space, **Record** adds shimmer, and **Source** runs
your input through the same chain instead.

**Inspired by:** Forge TME **Vhikk X**, the drone voice and FX module. Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = MOTION  none between the
 start                  size               clicks, drift past them
                                 start   = OVERTONES  the timbre scan
 density    [ pitch ]  overlap   size    = FORMANT  dark .. bright
                                 density = SPREAD  one line .. a swarm
       blend     window          overlap = SPACE
                                 window  = CROSS-MOD
                                 blend   = dry <-> veil
                                 pitch   = NOTE, 1V/oct (click = C2)

 [record]  [file]    [source]  [reset]   [freeze]
  SHIMMER   ALGORITHM INPUT     RANDOMISE HOLD
```

## The algorithms (File)
| # | Algorithm | Start (overtones) | Window (cross-mod) |
|---|---|---|---|
| 1 | **Swarm**: six voices on a morphing wavetable | sine → triangle → saw → square → bell | the voices FM each other |
| 2 | **Choir**: buzzing voices through vowel formants | the vowel: a → e → i → o → u | roughness |
| 3 | **Overtone stack**: exact harmonics | which harmonics, from the 1st to the 10th | ring modulation |
| 4 | **FM pair** | the ratio (through bell-like inharmonic places) | the FM index |
| 5 | **Ring**: two groups and their product | the second group's interval | how much ring |
| 6 | **Resonant noise**: tuned resonators rung by noise | harmonic → stretched (bell-like) | noise → crackle |

On every one, **Size** moves the formant (where the resonant peak sits) and **Density** spreads the voices.

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The note (click = C2) |
| **Start** | Overtones: the timbre scan (see the table) |
| **Size** | Formant: dark/large → bright/small |
| **Density** | Spread: a single line → a wide, beating swarm |
| **Window** | Cross-mod (see the table) |
| **Overlap** | Space: a diffuse stereo reverb that blurs into the drone |
| **Speed** | Motion. Between the two clicks: none. Past either click the four timbre knobs drift on their own, faster towards the ends |
| **Blend** | Dry input ↔ veil (it loads fully clockwise) |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Randomise: the four timbre settings jump to somewhere nearby, gliding there over a second or two | — |
| **Freeze** (button or gate) | Hold: the motion and the glide stop exactly where they are | on = held |
| **Source** (button or gate) | Process the input instead of the oscillators: waveshaping, formant, chorus and ring modulation on the same four knobs, then the space | on = input |
| **Record** (button or gate) | Shimmer: the space feeds back an octave up | on = shimmer |
| **File** | Next algorithm (six go round); the old one fades out | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Stereo width | medium |
| alt **Size** | Motion depth | medium |
| alt **Density** | Randomise range (small nudges → big jumps) | medium |
| alt **Window** | Space size | large-ish |
| alt **Overlap** | Shimmer amount | medium |
| alt **Blend** | Output level (±12 dB) | 0 dB |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `015_veil`: the swarm on C2.
2. Turn **Start**, **Size**, **Density** and **Window** slowly; press **File** for the next algorithm.
3. Turn **Speed** past a click and let it drift; press **Reset** for something new; **Freeze** to keep it.
4. Turn **Overlap** up for space, press **Record** for shimmer.
5. Press **Source** to run your input through the same chain.

## Notes
- CPU, measured offline: under half of the factory granular looper (only the current algorithm runs).
