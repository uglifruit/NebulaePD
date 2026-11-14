# pulsar: a granular oscillator

A Csound voice built on pulsar synthesis. The sound is a train of tiny grains (pulsarets), one per period of
the pitch, each followed by a gap. The grain's own frequency is a **formant**: it stays where it is while you
play notes, the way a vowel does, so the voice sounds like a resonant buzz or a sung "ah" rather than a plain
oscillator. Shorten the grains for a thin, bright buzz; drop pulses at random for a broken, crackling tone; take
the pitch far down and the pulses become a rhythm.

It's in the **Csound user bank** as `009_pulsar` (orange page, Reset button).

## Panel map
```
            [ speed ]            speed   = CHIRP  none between the
 start                  size               clicks, R up, L down
                                 start   = FORMANT  100 Hz .. 8 kHz
 density    [ pitch ]  overlap   size    = DUTY  thin -> round
                                 density = MASK  sparse -> every pulse
       blend     window          overlap = FM  clean -> noisy
                                 window  = GRAIN SHAPE
                                 blend   = dry <-> pulsar
                                 pitch   = PITCH, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  PLUCK     WAVE      AUDIO IN  SYNC/NOTE TRACK
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The note (the pulse rate): the click = C3 |
| **Start** | Formant: 100 Hz to 8 kHz, fixed while the pitch moves (vowel-like). With Freeze (Track) on, it's a multiple of the pitch instead (0.5× to 16×), so the timbre stays the same on every note |
| **Size** | Duty cycle, the grain's share of each period: anticlockwise = short grains (thin, bright, buzzy); clockwise = grains filling the whole period (round, closer to a plain tone) |
| **Density** | Masking: fully clockwise = every pulse sounds; turning it down drops pulses at random, to silence fully anticlockwise |
| **Window** | Grain shape: anticlockwise = square-ish (hard-edged, brighter); noon = a smooth bell; clockwise = sharp attack, long tail (percussive) |
| **Overlap** | FM inside each grain, by a sine at the pitch: clean → brassy → noisy |
| **Speed** | Chirp. Between the two clicks: none. Clockwise: each grain sweeps up, to 2 octaves at the end; anticlockwise: down. Clearest on long grains and at low pitches |
| **Blend** | Dry input ↔ pulsar (equal power). It loads fully clockwise |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Sync: the pulse train restarts on the gate, so a clock locks it. With Pluck on, it also plays a note | — |
| **Record** (button or gate) | Pluck: the voice is silent until Reset, and each Reset plays a note that dies away (alt Window sets how fast). Off = a drone | on = pluck |
| **Source** (button or gate) | The grains are made of the live input instead of a waveform: whatever you play, chopped into grains at the pitch. Start then transposes it (±2 octaves, noon = as played) | on = input |
| **Freeze** (button or gate) | Track: the formant follows the pitch (Start becomes a multiple of it) | on = tracking |
| **File** | Next grain waveform: sine, saw, square, vowel, noise | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Formant 2: its frequency, 0.5× to 4× formant 1 | about 1.2× |
| alt **Size** | Formant 2 level (a second resonance, for vowels) | off |
| alt **Density** | Stereo scatter: alternate grains go left and right | a little |
| alt **Window** | Pluck decay: 20 ms to 4 s | about 0.3 s |
| alt **Overlap** | Reverb size | half |
| alt **Blend** | Reverb amount | a little |
| alt **Pitch** | Sub-octaves: takes the pulse rate down by up to 8 octaves, from a tone into a rhythm (at C3, six octaves down is 2 pulses a second) | none |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `009_pulsar`: a C3 drone. Play notes on **Pitch** (or V/oct).
2. Turn **Start** slowly: the formant moves through the harmonics, like a filter sweep that stays put as the
   pitch moves. Turn **Size** down for a thinner buzz, up for a rounder tone.
3. Turn **Density** down: pulses drop out and the tone breaks up.
4. Press **File** for other grain waveforms; try **Overlap** for FM grit.
5. Hold Source and turn alt **Pitch** up: the pulses slow to a rhythm. Patch a clock into **Reset** to lock it, or
   press **Record** (Pluck) and play notes with gates.

## Notes
- The formant only shows clearly when a grain lasts a few of its own cycles: at the default Size a 1 kHz formant
  is under one cycle long, so the spectrum is broad (that's the buzz). Turn Size up for a sharper vowel.
- Short duty cycles are made louder so the level stays roughly even across Size.
- CPU, measured offline: under a third of the factory granular looper.
