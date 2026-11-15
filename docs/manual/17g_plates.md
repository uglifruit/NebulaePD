# plates: an eight-voice drone you touch into life

A Csound drone of eight voices in four pairs. Three buttons are **touch plates**: hold one (or send it a gate)
and its pair swells in, let go and it fades. **Density (Hold)** keeps every voice droning on its own. The
pairs modulate each other (FM) on **Window**, a "hyper LFO" of two square waves shakes them on **Speed**, and
there's a delay that can run away and a distortion on **Blend**.

**Inspired by:** SOMA Laboratory **Lyra-8**, the organismic synthesizer. Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = HYPER LFO  none between the
 start                  size               clicks
                                 start   = PAIR TUNING  unison > fifths
 density    [ pitch ]  overlap             > octaves
                                 size    = SHARP  sine > square-ish
       blend     window          density = HOLD  drone level untouched
                                 overlap = DELAY  echoes > runaway
                                 window  = FM  pairs modulate each other
                                 blend   = DISTORTION
                                 pitch   = NOTE, 1V/oct (click = C2)

 [record]  [file]    [source]  [reset]   [freeze]
  PAIR 1    LFO LOGIC  PAIR 4    PAIR 2    PAIR 3
  (hold)              (on/off)   (hold)    (hold)
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The lowest pair's note (click = C2) |
| **Start** | The pairs' tuning: all on the note fully anticlockwise, fifths apart a little past noon (0.58), octaves fully clockwise |
| **Size** | Sharp: sine → square-ish (more overtones) |
| **Density** | Hold: the level every voice drones at without being touched. Fully anticlockwise: silent until you touch |
| **Window** | FM: each pair modulates the next (the fourth modulates the first). Growl → splinter → chaos |
| **Overlap** | Delay: echoes, then feedback; near the top it runs away into self-oscillation |
| **Speed** | Hyper LFO. Between the clicks: none. Past them two square LFOs gate the FM and shake the pitch, faster towards the ends. Anticlockwise their edges are rounded |
| **Blend** | Distortion: clean → driven |

| Button / jack | Does | LED |
|---|---|---|
| **Record** (button or gate) | Touch pair 1: it sounds while held, or while a gate is high | on while touched |
| **Reset** (button or gate) | Touch pair 2 | on while touched |
| **Freeze** (button or gate) | Touch pair 3 | on while touched |
| **Source** (button or gate) | Pair 4 on/off: a pair that drones by itself | on = on |
| **File** | The LFO logic: A OR B → A AND B → A + B | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Delay time (30 ms .. 1.2 s; right = 1.5 × left) | ~0.2 s |
| alt **Size** | Detune within each pair (beating, up to 40 cents) | 10 cents |
| alt **Density** | Swell time (30 ms .. 2.5 s in, twice that out) | ~0.3 s |
| alt **Window** | LFO B's speed against A (0.5× .. 4×) | ~1.5× |
| alt **Overlap** | The LFO on the delay time (wobbling echoes) | a little |
| alt **Blend** | The input, into the delay and distortion | off |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `014_plates`: four pairs droning quietly in fifths (Hold at 0.4).
2. Hold **Record**, **Reset** or **Freeze** to swell a pair up; press **Source** for the fourth.
3. Turn **Window** for FM, **Size** for sharper voices, **Blend** for drive, **Overlap** for echoes.
4. Turn **Speed** past a click for the hyper LFO; press **File** to change its logic.
5. Patch gates from a sequencer into Record, Reset and Freeze to play the pairs.

## Notes
- Turn Density fully anticlockwise to play it only by touch.
- CPU, measured offline: under half of the factory granular looper.
