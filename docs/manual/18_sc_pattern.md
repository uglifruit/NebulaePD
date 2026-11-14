# sc_pattern — generative sequencer

A SuperCollider instrument that writes and plays its own music: four voices (a plucked lead, an FM bell, a bass and
a noise hat), each with its own rhythm, the pitched ones walking a scale. Clock it from Reset and it plays in time;
leave it alone and it runs at its own tempo. Patterns slowly mutate, can be locked, and come back home.

It's in the **SuperCollider bank** as `05_sc_pattern` (white page, Freeze button). Expect 5–10 s of silence while
SuperCollider starts.

## Panel map
```
            [ speed ]            speed   = TEMPO (free) / SWING (clocked)
 start                  size     start   = SCALE  8 zones
                                 size    = LENGTH  4-32 steps
 density    [ pitch ]  overlap   density = HITS  per voice
                                 overlap = MUTATION  per cycle
       blend     window          window  = TONE  bright -> dark
                                 blend   = SPACE  reverb
                                 pitch   = ROOT, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  MUTATE    HOME      SET B     CLOCK     LOCK
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Root of the scale; the click = C3. Every voice follows |
| **Start** | Scale: major, minor, dorian, phrygian, lydian, mixolydian, major pentatonic, minor pentatonic |
| **Size** | Pattern length: 4 to 32 steps (16 at about a third) |
| **Density** | How many hits each voice spreads over the pattern (evenly: Euclidean rhythms); the hat plays most, the bell least |
| **Overlap** | Mutation: at the end of every cycle some notes change (a step from their neighbour) and some rhythms shift. Anticlockwise = it repeats |
| **Window** | Tone: bright ↔ dark (filters, FM depth, hat colour) |
| **Blend** | Space: dry ↔ a big reverb |
| **Speed** | Free running: tempo, 60–240 BPM (120 between the clicks). With a clock: swing, right of the right click |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Clock: **one pulse = one 16th** (as topo). SuperCollider measures the clock and sends each step ahead of time, so the notes land on the pulses despite its 32 ms of latency. If the clock stops it carries on at the same tempo; after a gap of 2 s the next pulse is step 1 | — |
| **Freeze** (button or gate) | Lock: nothing changes, not even which hits sound | on = locked |
| **Record** (button or gate) | Mutate now: a burst of changes | toggles (no meaning) |
| **File** | Short press: back to home. Held 1 s: this pattern becomes home (at load, home is the first pattern) | — |
| **Source** | Voice set B: square lead, glassy bell, sub bass, shaker | on = set B |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Lead (pluck) level | 0.7 |
| alt **Size** | Bell level | 0.6 |
| alt **Density** | Bass level | 0.75 |
| alt **Overlap** | Hat level | 0.6 |
| alt **Window** | Octave spread: lifts the lead and the bell an octave or two | none |
| alt **Blend** | Decay of every voice: short ↔ long | noon |

Alt values only count once you move the knob.

## Quick start
1. Load `05_sc_pattern`: after the start-up it plays at 120 BPM.
2. Turn **Start** for another scale, **Pitch** for another key, **Density** for more notes.
3. Turn **Overlap** up a little: the tune develops cycle by cycle. Like it? Hold **File** 1 s to make it home,
   or press **Freeze** to lock it.
4. Patch a clock (16ths) into **Reset**: it follows. Turn Speed past the right click for swing.
5. **Record** shakes it up; **File** brings it back.

## Notes
- Each hit plays with a chance of 85 %, rolled every cycle, so a pattern breathes a little unless Freeze is on.
- The first pulse after a stop is played straight away (32 ms late), then everything lands on time.
- Tested on the PC with the module's SuperCollider: with a module-like clock (±5 ms), steps sound within 4–10 ms
  of the pulses.
