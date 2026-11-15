# chorale: a choir drone that sings vowels

A Csound drone of up to eight singing voices. Each voice has its own slight detune and vibrato; together they
sing through one set of vowel formants, so the whole choir moves from "ah" through "eh", "ee", "oh" to "oo" as
you turn Start. Press Source and the choir splits onto a chord; Reset steps through the chords.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = VOWEL DRIFT  none between
 start                  size               the clicks, wanders beyond
                                 start   = VOWEL  ah eh ee oh oo
 density    [ pitch ]  overlap   size    = VOICE SIZE  big <-> small
                                 density = VOICES  1 .. 8
       blend     window          overlap = BREATH
                                 window  = ENSEMBLE  tight -> loose
                                 blend   = dry <-> choir
                                 pitch   = NOTE, 1V/oct (click = C2)

 [record]  [file]    [source]  [reset]   [freeze]
  BREATHE   REGISTER  CHORDS    NEXT CHD  HOLD VOWEL
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The note: the click = C2 |
| **Start** | The vowel, morphing smoothly: ah → eh → ee → oh → oo |
| **Size** | Voice size (a formant shift): noon = natural; anticlockwise = bigger, darker voices; clockwise = smaller, brighter |
| **Density** | Voices, 1 to 8: the second and fourth on the note, the third, fifth and seventh an octave up, the eighth an octave down (the level stays even) |
| **Window** | Ensemble: how far the voices spread in pitch, from a tight choir to a loose crowd (each voice also wanders a little) |
| **Overlap** | Breath: air in the voices |
| **Speed** | Vowel drift. Between the two clicks: none. Past either click the vowel wanders round Start, faster towards the ends |
| **Blend** | Dry input ↔ choir (equal power). It loads fully clockwise |

| Button / jack | Does | LED |
|---|---|---|
| **Source** (button or gate) | Chords: the voices split onto a chord (voices 1–4 on its four notes, 5–8 an octave up) | on = chords |
| **Reset** (button or gate) | Next chord shape: fifth, major, minor, sus4, maj7, min7, add9, fourths (eight steps go round). A sequencer gate steps through them | — |
| **Freeze** (button or gate) | Hold the vowel where it is: Start and the drift stop moving it | on = held |
| **Record** (button or gate) | Breathe: every few seconds each voice drops out for a breath, at its own moment, so the choir sounds alive | on = breathing |
| **File** | Register: bass → tenor → alto → soprano (each with its own formants; four presses go round) | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Stereo width: the voices spread across left and right | wide |
| alt **Size** | Vibrato depth (0 to 50 cents) | gentle |
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount | a little |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `011_chorale`: four voices singing "ah" on C2 (bass register).
2. Turn **Start** slowly through the vowels. Turn **Density** for more voices, **Window** for a looser ensemble.
3. Press **File** to move up through tenor, alto and soprano; turn **Size** for bigger or smaller voices.
4. Press **Source** for a chord, then **Reset** to step through chords (or patch a gate into Reset).
5. Turn **Speed** past a click and the vowel starts to wander; **Freeze** holds it; **Record** makes the choir breathe.

## Notes
- The formant values are the classic published tables (as in the Csound manual) for each register.
- CPU, measured offline: under half of the factory granular looper.
