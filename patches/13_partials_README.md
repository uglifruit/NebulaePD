# partials: an additive drone organ

A Pure Data drone made of 16 sine waves, the partials of one note. You sculpt which partials sound and how bright
they are, stretch them from an organ into bells and metal, and let each one's level drift on its own, so the tone
keeps slowly changing colour. Reset deals a new random mix of partial levels and glides to it.

It's in the **Pd bank** as `O_partials` (yellow page, Freeze button), file `13_partials.pd` in the repo.

## Panel map
```
            [ speed ]            speed   = DRIFT SPEED  none between
 start                  size               the clicks, faster beyond
                                 start   = WHICH PARTIALS
 density    [ pitch ]  overlap             all -> odd -> even -> primes
                                 size    = STRETCH  organ -> bell -> metal
       blend     window          density = HOW MANY  1 .. 16
                                 overlap = DRIFT DEPTH
                                 window  = TILT  dark <-> bright
                                 blend   = dry <-> organ
                                 pitch   = NOTE, 1V/oct (click = C2)

 [record]  [file]    [source]  [reset]   [freeze]
  SUB       EVEN      TWINS     DEAL      HOLD
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The note: the click = C2 |
| **Start** | Which partials sound, morphing through four sets: all → odd only (hollow, clarinet-like) → even only, with half the fundamental (an octave up, airy) → primes only (1, 2, 3, 5, 7, 11, 13: sparse and strange) |
| **Size** | Stretch: anticlockwise = harmonic (an organ); turning up spreads the partials apart, into bells and then metal (partial *n* at *n*^1.4 at the end) |
| **Density** | How many partials: 1 (a pure sine) to 16, the top ones fading in one by one |
| **Window** | Tilt: anticlockwise = dark (high partials far down); noon = like a saw; clockwise = all equally loud (bright, buzzy) |
| **Overlap** | Drift depth: how far each partial's level wanders (none → all the way down and back) |
| **Speed** | Drift speed. Between the two clicks: none (the tone holds). Past either click: the levels wander, faster towards the ends |
| **Blend** | Dry input ↔ organ (equal power). It loads fully clockwise |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Deal: every partial gets a new random level, gliding there over 2 s (alt Density). A clock on Reset deals on the beat | — |
| **File** | Even: all the dealt levels back to equal (gliding) | — |
| **Freeze** (button or gate) | Hold: the drift stops where it is | on = held |
| **Source** (button or gate) | Twins: every partial gets a twin a few cents up, so each one beats slowly (a celeste) | on = twins |
| **Record** (button or gate) | Sub: a sine an octave below the note | on = sub |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Stereo width: odd partials to the left, even to the right | half |
| alt **Size** | Twin detune: 0 to 20 cents (how fast the twins beat) | 6 cents |
| alt **Density** | Deal glide: 0.1 to 10 s | 2 s |
| **Source + Record** | All of the above back to their defaults | — |

Alt values only count once you move the knob.

## Quick start
1. Load `O_partials`: an even, organ-like drone on C2. Turn **Window** anticlockwise to darken it.
2. Sweep **Start**: odd only (hollow), even only (airy), primes (strange). Turn **Size** for bells.
3. Turn **Overlap** up, then **Speed** past a click: the partials start to drift and the colour keeps moving.
4. Press **Reset** for a new mix; **Freeze** to hold one you like; **File** to go back to even.
5. Press **Source** for slow beating, **Record** for a sub.

## Notes
- The level stays the same whatever the shape (one partial or sixteen, dark or bright): it's normalised.
- Partials that would go above 18 kHz (high notes, a lot of stretch) are left out.
- CPU, measured offline: about a third of shimmer's, with the drift and the twins on.
