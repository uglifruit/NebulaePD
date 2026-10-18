# 03_gloop — a Gloop-style 4-play-head looper for the Nebulae

A functional take on [Cutlasses Gloop](https://github.com/cutlasses/GloopResources) (manual v1.3.0) in vanilla Pd.
Gloop records a loop and plays it with **four simultaneous play heads**. Each head has its own position, sub-loop size,
speed/direction, jitter, volume and pan. The Nebulae has no screen, and while Pd runs the Nebulae's own software
draws every LED from fixed functions: button LEDs show each button's latch state; the Speed and Pitch RGB LEDs show
those encoders. So the selected head is encoded in the **Source and Freeze latch states**: their LEDs show it.

## Controls

| Control | Normal | Hold Source (alt) |
|---|---|---|
| **start** | position of the selected head's sub-loop | volume, head 1 |
| **size** | sub-loop size of the selected head | volume, head 2 |
| **density** | jitter of the selected head (how far the sub-loop moves each repeat) | volume, head 3 |
| **overlap** | pan of the selected head (CCW = L, CW = R) | volume, head 4 |
| **speed** | rate of the selected head: centre stops, click = 1× fwd, click again = 1× reverse, ends = 4× | — |
| **pitch** | transpose the selected head in semitones, 1V/oct (click position = unison) | — |
| **window** | crossfade at the sub-loop edges, 5 ms – 1 s (all heads) | tape wobble (all heads) |
| **blend** | input (dry) ↔ loop mix | loop degrade per pass |
| **Source** (tap) + **Freeze** | select the head (table below) | — (holding Source is the alt layer) |
| **Record** | 1st press record, 2nd press close the loop; then overdub on/off (gate input works too) | **clear loop** |
| **Reset** | restart all heads from the top of their sub-loops (gate input works too) | — |
| **File** | pause / resume the selected head (fades and winds down; resume restarts it from the top) | grid: off → 4 → 8 → 16 → off |

| Head | Source LED | Freeze LED |
|---|---|---|
| 1 | off | off |
| 2 | **on** | off |
| 3 | off | **on** |
| 4 | **on** | **on** |

Tap Source to flip 1↔2 / 3↔4, press Freeze to flip 1↔3 / 2↔4. The Nebulae remembers both states across power
cycles, so the LEDs and the selected head always agree.

- **Knob takeover:** after you select a head, a knob only affects that head once you turn it, so heads keep their
  settings when you switch. CV into a knob counts as movement, so CV modulates the selected head.
- At load the head follows the Source/Freeze LEDs. Head 1 starts at full volume; heads 2–4 are muted until you set
  their volumes on the alt layer.
  (The Nebulae only sends alt values while Source is held.)
- Gates into Source/Freeze also change the head (and knob CV then follows the selection). Reset gate restarts heads.
- Proper per-head LEDs would need a custom Nebulae firmware that lets Pd send LED states back (not done).

## Engine
- Stereo buffer, 2 minutes at 48 kHz (`table gl_bufl/gl_bufr`, ~46 MB). Loop length is rounded to 64-sample blocks.
- **Write loop:** a sample counter reads the old sample, applies degrade, adds input when overdubbing, and writes it
  back. Counter and `tabwrite~` restart together at each wrap. Verified lossless and aligned over many passes.
- **Heads:** `phasor~` over the sub-loop. Position, size and jitter are latched at each wrap (`samphold~`), so moving
  them is click-free and lands on the next repeat. Read with `tabread4~`, edge fade, volume (squared), linear pan.
- A new loop restarts every head from the top of its sub-loop.

## Differences from Gloop / not implemented yet
- Effects pass still to do: delay, reverb, bit crusher, wavefolder, tape saturation/hiss/age, tilt EQ, wet/dry.
  (Degrade and wobble are in.)
- No assignable CV targets: Nebulae CV inputs are hard-wired to knobs, so CV modulates the selected head's parameter.
- No one-shot / jump triggers, no "replace" write mode (overdub only), no fine-sensitivity mode.
- Crossfade is a fade-out/fade-in at the sub-loop edges (a dip at long settings), not Gloop's overlapping crossfade.
- Gloop's input is mono; this records stereo.

## Testing on a PC
`python tools/gen.py` builds `sim/test_03_gloop.pd`; `pd -nogui -batch -r 48000 -open sim/test_03_gloop.pd` records a 1 s
loop from a test blip, switches heads via Source/Freeze, pauses and resumes a head, and restarts all heads. `tools/gen.py` also has `gloop_full_test` (overdub, size, reverse, degrade,
clear) and `gloop_grid_test` (grid, pan, jitter, wobble). Pass `wav=` to record the output, then inspect it with
`python tools/wavpeaks.py`. All three scenarios pass in Pd 0.57; not yet run on the module.
