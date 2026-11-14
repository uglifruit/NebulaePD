# sc_follow — it listens and plays along

A SuperCollider instrument that listens to what you play into it, a voice, a bass line, a lead, and plays along.
It tracks the pitch, works out the key, and adds a harmony in that key: a third above, a sixth below, whatever
you set. Held under your notes, or arpeggiated in time with the beat it hears (or with your clock).

It's in the **SuperCollider bank** as `06_sc_follow` (orange page, Record button). Expect 5–10 s of silence while
SuperCollider starts.

## Panel map
```
            [ speed ]            speed   = EXTRA  sub-octave (R),
 start                  size               octave up (L)
                                 start   = VOICE  bell / square / pad
 density    [ pitch ]  overlap   size    = GLIDE / note length
                                 density = ARPEGGIO  off -> 16ths
       blend     window          overlap = VOICES  1 -> 3
                                 window  = TONE
                                 blend   = dry <-> harmony
                                 pitch   = INTERVAL (click = 3rd)

 [record]  [file]    [source]  [reset]   [freeze]
  BELOW     ARP ORD   CHROMATIC ARP CLK   HOLD
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The harmony interval, in steps of the scale: the click = a third above. Turning it moves a step at a time; one octave of V/oct = seven steps (an octave), so a sequencer into V/oct plays the harmony line |
| **Start** | Voice: FM bell, soft square, supersaw pad (three zones) |
| **Size** | Sustained: how fast the harmony glides to a new note. Arpeggio: how long each note rings |
| **Density** | Arpeggio. The first quarter = off: the harmony is held under your notes, following your level. Then on the beat, 8ths, 16ths of the beat it hears (or of the clock on Reset) |
| **Overlap** | Voices: one harmony; past a third a second one (a further third up); past two thirds also your note an octave up |
| **Window** | Tone: dark ↔ bright |
| **Blend** | Dry ↔ harmony (equal power) |
| **Speed** | Extra: between the clicks none; right of the right click a sub-octave under your note; left of the left click an octave above |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Hold: the last note and key carry on as a drone after you stop | on = held |
| **Record** (button or gate) | Below: the harmony goes under your note instead of over it | on = below |
| **Source** | Chromatic: no key, every note gets the same interval (parallel major thirds at the click) | on = chromatic |
| **Reset** (button or gate) | Clock for the arpeggio: one pulse = one note. When no pulse has come for 2 s it follows the beat it hears | — |
| **File** | Next arpeggio order: up, down, up-down, random | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | How fast the key follows you (slow = steady, fast = changes key quickly) | medium |
| alt **Size** | Stereo width of the voices | half |
| alt **Density** | Input gate: below this level it doesn't follow (keeps noise out) | low |
| alt **Overlap** | Detune of the voices | a little |
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount | a little |

## Quick start
1. Load `06_sc_follow`, patch a melody (one note at a time) into the inputs, Blend fully clockwise.
2. Play for a few seconds: it finds the key and plays a third above each note. Blend back to noon to hear both.
3. Turn **Pitch** for other intervals, **Start** for another voice, **Overlap** for a chord.
4. Turn **Density** up for an arpeggio in time with your playing, or patch a clock into Reset.
5. Press **Freeze** on a note you like and stop playing: the harmony stays.

## Notes
- It follows one note at a time: chords confuse the pitch tracker.
- The key needs a few seconds of playing to settle. A plain scale run can be heard as a neighbouring key (C major
  and F major share six notes); melodies that dwell on the tonic and its third settle fastest.
- Latency: the harmony comes about 70 ms after you play (the tracker plus SuperCollider's 32 ms), so it suits
  held notes and lines better than fast staccato.
