# stretch — extreme time-stretch and freeze

A Csound instrument that slows sound right down, up to 1000× slower, **without changing its pitch**. It can also
freeze a moment and hold it, play backwards, or scrub through a sound by hand. The sound is either a file from
the stick, or what you just played into the inputs: Record grabs the last few seconds, so you never miss the
moment. Layers, smear, blur and a reverb turn a few seconds of anything into a slowly breathing landscape.

It's in the **Csound user bank** as `006_stretch`. Under the hood is a phase vocoder (`mincer`) with a time
pointer that the panel moves. The pointer can stand still, crawl, run backwards or jump, and the pitch stays
independent of it.

## Panel map
```
            [ speed ]              speed   = STRETCH  centre frozen, CW fwd, CCW back
 start                    size     start   = POSITION (turning it scrubs)
                                   size    = REGION the playhead loops in
 density    [ pitch ]   overlap    density = LAYERS 1-4, offset in time
                                   window  = SMEAR  clear -> washy
       blend      window           overlap = BLUR   smoothed over 0-2 s
                                   blend   = dry <-> stretched
                                   pitch   = TRANSPOSE, 1V/oct

 [record]  [file]    [source]   [reset]    [freeze]
  GRAB      NEXT      FILE/LIVE  TO START   PAUSE
```

## Controls
| Control | Does |
|---|---|
| **Speed** | Centre = frozen in place. Turn clockwise to move forward: glacial at first, reaching the original speed at the click. Past the click it goes faster, up to 4×. Anticlockwise does the same backwards. The rate curve is logarithmic, so most of the knob is the slow end. A gentle forward crawl is set when it loads |
| **Start** | Where in the sound the playhead is. Turning it scrubs the playhead through the sound, like moving a tape by hand |
| **Size** | The region the playhead travels in, starting at Start. It wraps round at the end. Small = a short loop of one moment; fully clockwise = from Start to the end of the sound |
| **Pitch** + 1 V/oct | Transpose, ±3 octaves; the click = original pitch. Independent of Speed: a frozen sound can be played as a note |
| **Density** | Layers: fully anticlockwise = one reader. Turning up fades in three more, each reading a little earlier or later in the sound and placed across the stereo field. Gives a thick, chorus-like cloud of the same moment |
| **Window** | Smear. Anticlockwise = clear and precise. Turning up reads each analysis frame from a slightly different place, so the sound turns washy and diffuse (paulstretch-like). Past 70 % the phase locking is also released, for the full wash |
| **Overlap** | Blur. The spectrum is smoothed over time, from none up to 2 s: changes melt into each other and sounds hang on |
| **Blend** | Dry input ↔ stretched sound (equal power). Fully clockwise = only the stretch |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Pause: holds the current moment, whatever Speed says. Press again to carry on. A gate toggles it | on = paused |
| **Reset** (button or gate) | Jump back to Start, with a short soft dip. Clock it to re-strike in time | — |
| **Record** (button or gate) | Grab the last N seconds of the input (N = alt Size, default 30 s). It is always listening, so press it *after* something good happened. The grab plays when Source is on | — |
| **File** | Next file from the stick | — |
| **Source** | Off = stick files. On = the grabbed input. With nothing grabbed yet, the first 5 s you play are grabbed by themselves | on = live |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Layer spread: how far apart the layers sit in the stereo field | half |
| alt **Size** | Grab length N: 5 – 120 s | 30 s |
| alt **Density** | How far apart in time the layers read: 0.02 – 4 s | ≈ 0.4 s |
| alt **Window** | Tone: dark (−18 dB treble) ↔ bright (+6 dB); noon = flat | flat |
| alt **Overlap** | Reverb size | medium |
| alt **Blend** | Reverb amount | a little |
| alt **Pitch** | Layer detune: up to ±30 cents between the layers (turn it past noon) | none |
| alt **Speed** | Not used (it's the Nebulae's input gain) | — |

## Quick start
1. Put a few audio files on the stick (anything: a voice, a chord, a field recording). Load `006_stretch`. It
   starts crawling through the first file. Set Blend fully clockwise.
2. Turn Speed towards the centre: slower and slower, until it freezes. Turn Start to scrub to another moment.
3. Turn Pitch: the frozen moment becomes a note. Patch V/oct and play it.
4. Bring up Density for layers, Window for smear, Overlap for blur. Hold Source and raise Blend for reverb.
5. Live: play something into the inputs, press Record, tap Source (LED on). What you just played is now frozen
   in time.

## Notes
- Long files and long grabs cost memory, not CPU: up to 120 s of input is kept twice (one buffer recording while
  the other plays).
- CPU with everything on is measured at about 1.2–1.5× the factory granular looper (offline, PC).
- Files at any sample rate play at the right pitch and speed.
- Reset and File changes dip the sound for a moment (20 ms down, 40 ms up), so jumps don't click.
