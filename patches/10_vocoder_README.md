# vocoder — 20-band channel vocoder

A Pure Data instrument that puts the spectrum of one sound onto another, the classic robot-voice and
talking-synth effect. The **left input** is the modulator: a voice, drums, anything with a shape. The carrier is
either an internal synth chord (a supersaw on V/oct) or whatever you patch into the **right input**.
Freeze holds a vowel so you can play it as a chord, Speed shifts the formants up or down, and Track makes the
internal chord follow the pitch of the voice.

It's in the **Pd bank** as `L_vocoder` (yellow page, File button), file `10_vocoder.pd` in the repo.

## Panel map
```
            [ speed ]            speed   = FORMANT SHIFT  none between
 start                  size               the clicks, R up, L down
                                 start   = CHORD   8 shapes
 density    [ pitch ]  overlap   size    = BANDS   smooth -> sharp
                                 density = DETUNE  supersaw width
       blend     window          overlap = SIBILANCE  noise for s/t
                                 window  = ENVELOPE   snappy -> slow
                                 blend   = voice <-> vocoder
                                 pitch   = CHORD ROOT, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  TRACK     HOLD      EXT CAR   NEXT CHD  FREEZE
```

## Controls
| Control | Does |
|---|---|
| **Start** | Chord shape of the internal carrier, in 8 zones: unison, octaves, fifth, major, minor, sus4, maj7, min7 |
| **Size** | Band sharpness: anticlockwise = smooth, wide bands; clockwise = narrow, ringing, more "robot" |
| **Density** | Detune: three saws per chord note, spread from none (clean) to a wide supersaw |
| **Overlap** | Sibilance: adds noise wherever the voice has "s" and "t" sounds (above 5 kHz), so consonants stay clear |
| **Window** | Envelope speed: anticlockwise = snappy (follows every syllable); clockwise = slow, smeared |
| **Blend** | Dry modulator (left input) ↔ vocoder (equal power) |
| **Pitch** + 1 V/oct | Root of the internal chord. The click = C3. With Track on, it transposes the tracked pitch in semitones instead |
| **Speed** | Formant shift. Between the two clicks: none (a load on a click is safe). Clockwise: formants up, to 6 bands (two octaves) at the end, the chipmunk side. Anticlockwise: down, the giant side |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Hold the spectral envelope: the vowel or sound at that moment stays, and the carrier keeps playing through it, so you can change chords and notes on a frozen vowel | on = frozen |
| **File** (held) | Momentary freeze, for as long as you hold it | — |
| **Reset** (button or gate) | Next chord shape (one step past what Start says; eight steps go round). A sequencer gate steps through the chords | — |
| **Record** (button or gate) | Track: the internal chord's root follows the pitch of the voice on the left input, rounded to the nearest semitone (a robot choir). Pitch then transposes it | on = tracking |
| **Source** (button or gate) | Carrier: off = the internal chord; on = the right input (any synth, pad or noise you patch in) | on = external |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Stereo width: even bands to the left, odd bands to the right | half |
| alt **Size** | Presence: lifts the voice's top end before the bands, for clearer words | a little |
| alt **Density** | Whisper: blends the internal saws into noise | off |
| alt **Overlap** | Carrier leak: some of the unvocoded carrier underneath | off |
| alt **Window** | Track glide: how smoothly the tracked chord moves (0–500 ms) | 30 ms |
| alt **Blend** | Noise gate threshold (−80 … −20 dB): below it the bands close, so hiss doesn't play the carrier | −60 dB |
| alt **Pitch**, alt **Speed** | Not used (alt Speed is the Nebulae's input gain) | — |
| **Source + Record** | All of the above back to their defaults | — |

Alt values only count once you move the knob (holding Source shows the old values first).

## Quick start
1. Patch a voice (or a drum loop) into the **left** input. Load `L_vocoder`. Blend fully clockwise.
2. Talk or sing: you hear the internal chord speaking. Turn **Start** for other chords, **Pitch** (or V/oct) to
   play them, **Density** for a wider supersaw.
3. Press **Freeze** on a vowel and play chords on it. Press it again to let go.
4. Turn **Speed** past a click to shift the formants. **Size** fully clockwise for a sharper robot.
5. Press **Record** (Track) and sing: the chord follows your pitch. Or press **Source** and patch a synth into
   the right input as the carrier.

## Notes
- The bands run from 100 Hz to 8 kHz, a third of an octave apart, each a 4-pole band-pass.
- The output level follows the modulator's level and the carrier's brightness: a higher chord root sounds a
  little louder, and an external carrier works like a VCA input (its level matters).
- The voice on the left input isn't delayed: Blend mixes it back exactly.
- CPU, measured offline: about the same as shimmer. The pitch tracker only runs while Track is on.
