# chop — slice sequencer

A Pure Data instrument that cuts a loop into slices at its hits and plays them back in a new order, in time with
your clock. The loop is either something you grab from the inputs (Record grabs exactly 1, 2 or 4 bars, starting
on a bar line) or a WAV from the stick (File). Turned all the way down, chop plays the loop back exactly as it
was. Turning the knobs up shuffles the hits, drops some, repeats them as ratchets, plays them backwards and makes
them jump in pitch. The rhythm of the loop always stays: only what plays on each hit changes.

It's in the **Pd bank** as `K_chop` (yellow page, Record button), file `09_chop.pd` in the repo.

## Panel map
```
            [ speed ]            speed   = PITCH JUMPS  off between
 start                  size               the clicks, R up, L down
                                 start   = SHUFFLE   own -> any slice
 density    [ pitch ]  overlap   size    = GATE      stabs -> full
                                 density = HITS      none -> all
       blend     window          overlap = RATCHET   chance of 2-6x
                                 window  = REVERSE   chance
                                 blend   = input <-> chop
                                 pitch   = TRANSPOSE, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  GRAB      WAV       STEP 1    CLOCK     HOLD DICE
```

## Controls
| Control | Does |
|---|---|
| **Start** | Shuffle: the chance that a hit plays another slice of the loop instead of its own. Fully anticlockwise = the original loop; fully clockwise = every hit picks any slice |
| **Size** | Gate: how much of each slice plays. Fully clockwise = the whole slice (a perfect replay); anticlockwise = short stabs (down to 12 ms) |
| **Density** | Hits: the chance that a hit plays at all. Fully clockwise = every hit; turning down drops hits out (silence until the next one) |
| **Overlap** | Ratchet: the chance that a hit repeats 2, 3, 4 or 6 times within its 16th (the counts are set on alt Overlap). The last repeat plays on |
| **Window** | Reverse: the chance that a hit plays backwards (from the end of its slice) |
| **Blend** | Input ↔ chop (equal power). Fully clockwise = only chop |
| **Pitch** + 1 V/oct | Transpose every hit, in semitones; the click = original. Like a sampler: higher is also shorter |
| **Speed** | Pitch jumps. Between the two clicks: none (a load on either click is safe). Clockwise of the right-hand click: a growing chance that a hit jumps **up** (+5, +7 or +12). Anticlockwise of the left-hand click: **down** (−12 or −24, a tape drop) |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Clock in: **one pulse = one beat** (a quarter note). chop runs 16th steps inside the beat. Tap the button twice for a tempo by hand. With no clock it runs at 120 BPM from load, and keeps the last tempo when the clock stops. If the clock stops for over 2 s, the next pulse is step 1 (so starting your sequencer starts chop's bar) | — |
| **Record** (button or gate) | Grab: the next 1, 2 or 4 bars of the input (alt Start), starting at the next bar line. When the grab ends, at a bar line, it plays at once. A press during a grab is ignored | toggles (no meaning) |
| **File** | Short press: the next `.wav` / `.aif` on the stick (FLAC can't be read by Pd). It plays from the next bar line. **Held ½ s**: back to the last grab | — |
| **Source** (button or gate) | Step 1: the next beat becomes step 1. A gate up to 30 ms after a beat re-plays that beat as step 1, so a gate sent together with the clock is never a beat late. Holding Source still opens the alt layer | toggles (no meaning) |
| **Freeze** (button or gate) | Hold the dice. Off: a new pattern is rolled at the start of every cycle. On: the same pattern repeats. The knobs still work while it's held: turning Shuffle up adds swaps (the same ones each time), and turning it back takes them away again | on = held |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Grab length: 1 / 2 / 4 bars (three zones) | 1 bar |
| alt **Size** | Slicing. Fully anticlockwise = equal 16ths. Then onset detection, more sensitive clockwise (more slices). It re-slices at once | noon |
| alt **Density** | Swing on the 16ths: straight → heavy (the off-16ths up to half a 16th late) | straight |
| alt **Overlap** | Ratchet counts: anticlockwise 2× only → 2–3× → 2–4× → clockwise 2, 3, 4 or 6× | 2–4× |
| alt **Window** | Slice edges: tight 1 ms fades → soft 20 ms fades | 1.5 ms |
| alt **Blend** | Stutter: the chance that a hit repeats the slice of the hit before it (beat-repeat) | off |
| alt **Pitch**, alt **Speed** | Not used (alt Speed is the Nebulae's input gain) | — |
| **Source + Record** | All of the above back to their defaults | — |

Alt values only count once you move the knob (holding Source shows the old values first).

## Quick start
1. Patch a clock (one pulse per beat) into **Reset** and a drum loop or drum machine into the inputs. Load
   `K_chop`. Set Blend fully clockwise, Size fully clockwise, Density fully clockwise, the rest anticlockwise.
2. Press **Record** just before a bar starts. One bar later chop plays the grab back: it sounds like the input.
3. Turn **Start** up: the hits get swapped around. Every cycle brings a new pattern. Like one? Press **Freeze**.
4. Add **Overlap** for rolls, **Window** for reversed hits, **Speed** past a click for pitch jumps, and pull
   **Density** and **Size** down for space.
5. Or press **File** to chop a loop from the stick instead (no clock needed: it runs at 120 BPM until one comes).

## How it slices
- When a grab ends or a file loads, chop looks for **onsets** (sudden rises in level). Each 16th step that has
  an onset near it starts a slice, and the slice starts 1.5 ms before the onset, so no attack is cut. Steps
  without an onset let the previous slice play on: this is how the loop's rhythm stays when hits are swapped.
- If it finds fewer than 2 onsets per bar (a pad, a drone), it uses equal 16ths instead. So does alt Size fully
  anticlockwise.
- A WAV doesn't say its tempo. chop takes its length against the current tempo as 1, 2 or 4 bars (the nearest),
  and plays each slice at its own speed, starting on its step. So a file follows the clock without changing
  pitch, like a sliced break. Files longer than 6 bars give their first 4 bars.
- Files at any sample rate play at the right pitch; mono files come out of both sides.

## Notes
- A hit sounds about 1.5 ms after its step: that's the pre-roll before the onset. There's no other added
  latency, and the dry input is not delayed.
- Loading a file reads it in one go, so expect a very short dropout when you press File (Pd can't read files in
  the background). Grabs have no dropout.
- Up to 43 s per grab or file. chop keeps two grabs and two files in memory, so what's playing is never
  overwritten by what's loading.
- CPU, measured offline: about the same as glitch.
