# tanpura: a self-playing drone of plucked strings

A Csound drone after the Indian tanpura. Four strings are plucked in turn, over and over: the first string,
two strings an octave up on the home note (Sa), then the low Sa. Each string buzzes against a curved bridge (the
jawari), the bright, shimmering buzz that makes a tanpura sound alive. It plays by itself, or follows a clock.

**Inspired by:** the Indian **tanpura**, the drone lute with a buzzing (jawari) bridge.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = CYCLE  about 4 s between
 start                  size               the clicks, 1 s CW, 8 s CCW
                                 start   = 1ST STRING  Pa | Ma | Ni | Sa
 density    [ pitch ]  overlap   size    = TONE  dark -> bright
                                 density = JAWARI  clean -> buzzing
       blend     window          overlap = LIFE  sway + beating
                                 window  = RING  2 .. 30 s
                                 blend   = dry <-> tanpura
                                 pitch   = LOW SA, 1V/oct (click = C2)

 [record]  [file]    [source]  [reset]   [freeze]
  PAUSE     -         OCTAVE    PLUCK     SUSTAIN
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The low Sa (the lowest string): the click = C2. The two middle strings are an octave above |
| **Start** | The first string's note, in four zones: Pa (a fifth up), Ma (a fourth), Ni (a major seventh), Sa (all four on Sa). Tuned in just intervals, as a tanpura is |
| **Speed** | Cycle time, four plucks per cycle. Between the two clicks about 4 s (a pluck a second); clockwise faster, to 1 s; anticlockwise slower, to 8 s |
| **Window** | Ring time: 2 s to 30 s |
| **Density** | Jawari: anticlockwise = a clean string; clockwise = the buzzing bridge (notes ring a little shorter, as the buzz takes energy) |
| **Size** | Tone: dark → bright |
| **Overlap** | Life: the plucks sway a little in time, and the two Sa strings drift apart by up to 6 cents, so they beat slowly |
| **Blend** | Dry input ↔ tanpura (equal power). It loads fully clockwise |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Pluck the next string. A clock into Reset takes over the playing; 2 s after the last pulse it plays by itself again | — |
| **Record** (button or gate) | Pause: no new plucks; the strings ring on and fade | on = paused |
| **Freeze** (button or gate) | Sustain: the strings ring on for as long as it's held. The buzz fades out while frozen (it would drain the note) and comes back when you let go | on = sustaining |
| **Source** (button or gate) | Octave: the whole tanpura an octave up (a higher tanpura) | on = up |
| **File** | Not used | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Stereo width: string 1 to the left, low Sa to the right | wide-ish |
| alt **Size** | Pluck hardness: a soft finger → a hard pluck | medium |
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount | a little |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `010_tanpura`. After a moment it starts plucking: Pa, Sa, Sa, low Sa, round and round.
2. Set **Pitch** to the key you play in (V/oct works). **Start** picks the first string: Pa for most ragas, Ma or
   Ni for others.
3. Turn **Density** for more or less buzz, **Window** for longer rings, **Speed** for the pace.
4. **Overlap** brings it to life: a slight sway and slow beating between the Sa strings.
5. Patch a clock into **Reset** to pluck in time. **Record** pauses it; **Freeze** holds the strings ringing.

## Notes
- CPU, measured offline: under half of the factory granular looper.
