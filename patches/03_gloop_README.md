# 03_gloop — 4-head looper for the Nebulae (user guide)

A Pure Data take on the Cutlasses **Gloop** looper. Record a loop (up to 2 minutes, stereo), then play it back with
**four play heads** at once. Each head can play a different part of the loop, at its own speed, direction, pitch,
volume and pan. That makes it good for layered loops, phasing, canons and granular-style textures.

Install: copy `03_gloop.pd` to the **root** of the Nebulae USB drive, then load it from the instrument selector
(hold Speed → turn until only the right speed LED is lit → press the button for the patch → click Speed).

---

## Panel map

```
                 [ speed ]                          speed  = RATE of selected head
   start                          size              start  = POSITION of selected head    (alt: VOLUME head 1)
                                                    size   = SIZE of selected head        (alt: VOLUME head 2)
   density       [ pitch ]        overlap           density= JITTER of selected head      (alt: VOLUME head 3)
                                                    overlap= PAN of selected head         (alt: VOLUME head 4)
          blend          window                     pitch  = TRANSPOSE ALL heads, 1V/oct  (alt: INTERVAL of selected head)
                                                    blend  = input <-> loop mix           (alt: DEGRADE)
                                                    window = CROSSFADE at loop edges      (alt: TAPE WOBBLE)

  [record]  [file]  [source]  [reset]  [freeze]
   REC/OVD   PAUSE   HEAD bit1 RESTART  HEAD bit2       (hold Source = alt layer)
   alt:CLEAR alt:GRID
```

## Choosing a head (watch the Source and Freeze LEDs)

| Head | Source LED | Freeze LED |
|:---:|:---:|:---:|
| **1** | off | off |
| **2** | **ON** | off |
| **3** | off | **ON** |
| **4** | **ON** | **ON** |

- **Tap Source:** swaps 1↔2 and 3↔4.
- **Press Freeze:** swaps 1↔3 and 2↔4.
- The LEDs always show the selected head, even after a power cycle.
- Gates into the Source and Freeze jacks select heads too, so you can sequence head selection.

## Knobs (normal layer — they edit the **selected head**)

| Knob | Does | Notes |
|---|---|---|
| **start** | where the head's sub-loop sits in the main loop | |
| **size** | length of the head's sub-loop | from the whole loop down to tiny grain-sized slices |
| **density** | jitter: how far the sub-loop jumps randomly on each repeat | 0 = steady |
| **overlap** | pan | CCW = left, centre = both, CW = right |
| **speed** (encoder) | playback rate and direction | centre = stopped. Click = 1× forward, click again = 1× reverse. Turn out to 4× either way |
| **pitch** (encoder + 1V/oct jack) | transpose **all heads** together, in semitones | click = original pitch. Heads keep their intervals, so a V/oct sequence plays the whole chord of heads in tune |
| **window** | crossfade at the sub-loop edges (all heads) | CCW = 5 ms (tight) … CW = 1 s (soft, swelling) |
| **blend** | dry input ↔ loop playback | CW = loops only |

**Takeover** (start, size, density, overlap, speed): when you switch heads, a knob doesn't change the new head until you **turn** it. Each head keeps its own
settings until you deliberately change them. CV into a knob counts as turning it, so CV always modulates the
**currently selected** head.

## Alt layer (hold **Source**)

| Control | Does |
|---|---|
| **start / size / density / overlap** | volume of heads **1 / 2 / 3 / 4** (Gloop's four volume pots) |
| **blend** | degrade: each pass gets quieter and duller (sound-on-sound fade) |
| **window** | tape wobble (wow and flutter) on all heads |
| **pitch** (encoder) | **interval of the selected head**: semitones above/below the global pitch, ±2 octaves. The Pitch LEDs show the amount. Set it per head (select the head, hold Source, turn) |
| **Record** | **clear the loop** |
| **File** | grid: off → 4 → 8 → 16 → off. Positions and sizes snap to 1/4, 1/8 or 1/16 of the loop |

Heads 2–4 start **muted**. Hold Source and turn up size, density or overlap to hear them.

> **Never click the Pitch encoder while holding Source.** On the Nebulae that resets every alt setting to default:
> the head volumes jump, and the encoder's alt value resets. The head intervals are protected (the patch ignores the jump),
> but you'll need to turn the encoder back up before adjusting an interval again.

## Buttons (normal layer)

| Button | Does |
|---|---|
| **Record** (+gate) | 1st press: start recording. 2nd press: close the loop and start playing. Later presses: overdub on/off |
| **Reset** (+gate) | restart all heads from the start of their sub-loops |
| **File** | pause the selected head (it fades and winds down like tape). Press again: it restarts from the top |
| **Source / Freeze** | select the head (see above) |

## Quick start

1. Patch audio into **In L** (and **In R** for stereo). Set **blend** to about noon.
2. Press **Record**, play something, press **Record** again. The loop plays on head 1.
3. Turn **blend** fully CW to hear only the loop.
4. **Tap Source** (Source LED on = head 2). Hold Source and turn **size** up to hear head 2.
5. Let go of Source. Turn **speed** a little clockwise (head 2 now runs faster than head 1) and turn **size** down. Head 2
   now loops a shorter, faster slice against head 1.
6. **Press Freeze** (both LEDs on = head 4). Hold Source, raise **overlap** for its volume and turn **pitch** down
   for an octave below. Let go and set its **speed** to reverse.
7. Patch a sequencer into **V/oct**: every head follows, keeping the intervals you set.
8. Press **Reset** to bring all heads back into sync.
9. Hold Source + **Record** to clear and start again.

## Tips

- **Granular:** small **size**, some **density** (jitter), **window** CW for soft grains, several heads at different intervals.
- **Chords:** give heads 2–4 intervals (e.g. +7, +12, −12) with Source + Pitch, then play the chord from V/oct.
- **Rhythmic slicing:** hold Source and press **File** to set grid 8 or 16, so sizes and positions lock to the beat.
- **Sound on sound:** hold Source and raise **blend** (degrade), then turn overdub on. Older layers slowly fade away.
- **Tape vibe:** a little alt **window** (wobble) and slow **speed** changes.
- Gate into **Reset** to retrigger all heads in time with a clock.

## Limits (compared with the real Gloop)

- No screen. The only feedback is the head shown by the Source and Freeze LEDs.
- Not yet included: delay, reverb, bit crusher, wavefolder, tape saturation/hiss/dropouts, tilt EQ.
- CV goes to fixed knobs (no assignable CV targets). No one-shot or jump triggers, overdub only (no replace mode).
- Long crossfades dip in volume at the loop point rather than overlapping.
- Not yet tested on hardware: built and tested offline in Pd. Please report how it feels.

More technical detail: [`docs/GLOOP.md`](../docs/GLOOP.md).
