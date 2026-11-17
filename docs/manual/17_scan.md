# scan — scanned synthesis

A Csound instrument built on a vibrating string you can't hear directly: 64 masses on a ring, tied together by
springs. An oscillator reads the string's shape as its waveform. Strike the string and the wave runs round the
ring and dies away: the **timbre** moves, not just the level, like a struck object whose tone keeps changing.
Bow it to keep it moving, or feed it audio from the inputs.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = 2ND VOICE  none between
 start                  size               the clicks, R detune,
                                           L octave below
 density    [ pitch ]  overlap   start   = STRIKE POSITION
                                 size    = MASS  light -> heavy
       blend     window          density = STIFFNESS loose -> tight
                                 overlap = CENTRING  springy wobble
                                 window  = DAMPING  long -> short
                                 blend   = dry <-> string
                                 pitch   = PITCH, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  BOW       SHAPE     AUDIO IN  STRIKE    HOLD WAVE
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The note: the click = C3 |
| **Start** | Where a strike hits the ring (it changes which harmonics ring out) |
| **Size** | Mass: light = the tone changes faster; heavy = slower |
| **Density** | Stiffness: loose = the wave crawls round the ring (a tone that evolves over many seconds); tight = it moves faster (a livelier tone with a slight chorus) |
| **Window** | Damping: anticlockwise rings for up to a minute, clockwise is a short pluck |
| **Overlap** | Centring: how hard the masses are pulled back to rest; turned up, the tone swells and fades in a springy wobble (slow to a few times a second) |
| **Blend** | Dry input ↔ string (equal power). It loads fully clockwise |
| **Speed** | A second voice. Between the two clicks: none. Clockwise: a slightly detuned copy (chorus, spread in stereo by alt Size). Anticlockwise: the same shape an octave below |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Strike the string at Start. Clock it for rhythmic strikes | — |
| **Record** (button or gate) | Bow: a gentle, wandering push travels round the string and keeps it sounding (latching) | on = bowing |
| **Source** (button or gate) | The audio input pushes the string at Start: play into it and the string sounds at Pitch, following your playing (accents push harder). Blend brings in your dry input | on = input |
| **Freeze** (button or gate) | Hold the waveform as it is at the press; the string carries on underneath, and you hear it again when you release | on = frozen |
| **File** | Next strike shape: narrow bump (bright), wide bump (soft), square (hollow), noise (rough) | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Strike strength | half |
| alt **Size** | Stereo width of the second voice | half |
| alt **Density** | Bow pressure | a little |
| alt **Window** | Tone: dark (−18 dB treble) ↔ bright (+6 dB); noon = flat | flat |
| alt **Overlap** | Reverb size | medium |
| alt **Blend** | Reverb amount | a little |
| alt **Pitch**, alt **Speed** | Not used (alt Speed is the Nebulae's input gain) | — |

## Quick start
1. Load `008_scan`. Press **Reset**: a note at C3 that changes colour as it dies away.
2. Turn **Window** anticlockwise for a long ring and strike again. Try **Density** and **Size** for different
   materials, and **Start** for where you hit.
3. Patch a clock into Reset and a sequence into V/oct. Press **File** for another strike shape.
4. Press **Record** to bow: a sustained, slowly shifting drone. Hold Source and raise alt Density for more
   pressure.
5. Press **Freeze** on a moment you like: that waveform stays as a steady tone.

## Notes
- A strike sends a wave round the ring both ways. The motion is kept slow next to the note (from once in 50 s
  to twice a second round the ring), so the note stays in tune and the tone evolves over seconds; tight and
  light give a slight chorus.
- The string is computed 750 times a second and glides smoothly between updates.
- At the extremes (bowing hard with no damping) the string's energy is limited automatically, so it never runs
  away.
- CPU, measured offline: about half the factory granular looper.
