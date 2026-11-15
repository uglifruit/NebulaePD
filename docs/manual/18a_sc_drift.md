# sc_drift: a drone / pad

A SuperCollider drone. Five detuned voices on a morphing oscillator (saw → pulse → sine), through a resonant
filter that drifts on its own. It sounds as soon as it loads.

**Bank:** SuperCollider. Expect 5–10 s of silence while SuperCollider starts.

## Panel map
```
            [ speed ]            speed   = DRIFT RATE  slow <-> fast
 start                  size     start   = OSCILLATOR  saw > pulse > sine
                                 size    = DETUNE SPREAD
 density    [ pitch ]  overlap   density = FILTER CUTOFF
                                 overlap = DRIFT DEPTH
       blend     window          window  = RESONANCE
                                 blend   = LEVEL
                                 pitch   = PITCH, 1V/oct (click = C4)

 [record]  [file]  [source]  [reset]  [freeze]
                    CHORD     SWELL    SUB OCTAVE
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Pitch (click = C4) |
| **Start** | Oscillator: saw → pulse → sine |
| **Size** | Detune spread: unison → wide |
| **Density** | Filter cutoff (80 Hz – 12 kHz) |
| **Window** | Filter resonance |
| **Overlap** | Drift depth: the filter and pulse width move |
| **Speed** | Drift rate (slow ↔ fast) |
| **Blend** | Level |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Sub-octave on/off | on = sub |
| **Source** (button or gate) | Chord: adds a fifth and an octave | on = chord |
| **Reset** (button or gate) | Swell: the sound dips and blooms back | — |

## Quick start
1. Load it: a pad at once.
2. Start fully clockwise (sine), Density low, Freeze on: a deep sine drone.
3. Start at noon (pulse), Window up, Overlap up, Speed slow: a moving resonant pad.
