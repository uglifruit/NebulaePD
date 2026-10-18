# 04_glitch — clock-synced beat-repeater for the Nebulae (user guide)

A Pure Data port of **Glitch** (Music Thing Workshop Computer program 57). The Nebulae is always recording into a
43-second circular buffer. Each clock pulse marks one **beat**, and the patch plays that beat back in one of two
modes:

- **Glitch** — ratchets the start of the last beat (÷1 to ÷6). Each repeat may be reversed, and may be degraded with
  sample-rate reduction and bitcrushing.
- **Stutter** — a live breakbeat slicer. It cuts the beat into 1–8 slices and plays them in a shuffled order. Slices
  may repeat, and they may come from earlier beats.

When a slice isn't glitched, live audio passes straight through, so the effect drops in and out of your signal.

Install: copy `04_glitch.pd` to the **root** of the Nebulae USB drive, then load it from the instrument selector.

---

## Panel map

```
                 [ speed ]                       start   = GATE: above half = glitch every slice
   start                          size           size    = DIVISION  Glitch ÷1 ÷2 ÷3 ÷4 ÷6 / Stutter 1 2 3 4 8 slices
                                                 density = PROBABILITY  Glitch: glitch + reverse / Stutter: drift
   density       [ pitch ]        overlap        window  = X  Glitch: degrade amount / Stutter: shuffle probability
                                                 overlap = Y  Glitch: degrade probability / Stutter: repeat probability
          blend          window                  blend   = dry <-> glitched
                                                 pitch   = TRANSPOSE the glitches, 1V/oct (click = original)
                                                 speed   = RAMP: each repeat steps up (right) / down (left), centre = flat

  [record]  [file]  [source]  [reset]  [freeze]
   FORCE      -      MODE      CLOCK    FREEZE
```

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (jack or button) | **Clock in.** Each pulse = one beat; the time between pulses sets the beat length (up to 10 s). Tap the button twice to set a tempo by hand | flashes on each pulse |
| **Source** | **Mode:** off = **Glitch**, on = **Stutter**. Takes effect at the next clock | on = Stutter |
| **Record** | **Force:** glitch / shuffle every slice (the WC switch held Down). A gate into the Record jack toggles it | on = forced |
| **Freeze** | **Freeze** the buffer: recording stops, playback keeps glitching the frozen material. A gate into the Freeze jack toggles it | on = frozen |

All six pots have CV jacks, so every parameter can be modulated.

## Which slices get the effect

For every slice, in this order:
1. **Record LED on** → always (Force).
2. **Start above half** (pot, or a gate into the Start CV jack with the pot fully CCW) → always (gate).
3. Otherwise **random**, with the probability set by **density** (Glitch) or **window** (Stutter).

Anything else is live pass-through. For pure gate behaviour (the WC's middle switch position), set the probability
to 0.

## Glitch mode (Source LED off)

At each clock pulse the patch measures the beat. It then plays the **first 1/div of the previous beat**, repeated div
times across the next beat.

| Control | Does |
|---|---|
| **size** | ratchet division: ÷1 (repeat the whole beat), ÷2, ÷3, ÷4, ÷6 — five equal zones |
| **density** | glitch probability (switch-Up behaviour) **and** reverse probability, rolled per slice |
| **window** | degrade amount. CCW = clean. First half: sample-rate reduction up to 16×. Second half: 16× plus bitcrush, up to 7 bits removed |
| **overlap** | degrade probability per slice. CCW = never, CW = always |

## Stutter mode (Source LED on)

At each clock pulse the beat is cut into slices, which are reshuffled and played back across the next beat.

| Control | Does |
|---|---|
| **size** | slices per beat: 1, 2, 3, 4, 8 |
| **density** | **drift** probability: how often the beat is taken from an earlier beat (up to 12 beats back) instead of the last one. The slice grid stays locked to real beats |
| **window** | shuffle probability per slice (else live pass-through) |
| **overlap** | repeat probability: how often a slice plays again before moving on. CW = one slice stutters for the whole beat |

## Pitch and Speed (both modes)

The rhythm never changes; only the material inside each slice does.

| Control | Does |
|---|---|
| **pitch** (encoder + 1V/oct jack) | **Transpose** in semitones. Click = original pitch; the range is −3 to +2 octaves. Live, so a sequencer into the 1V/oct jack plays the repeats as a melody. Glitched slices go up or down. **Pass-through goes down only** (see below) |
| **speed** (encoder + CV) | **Ramp** across the repeats of each beat: every slice after the first steps by N semitones. Left of centre = falling (a tape-slowing feel): left click = −3 semitones per repeat, left end = −12. **Centre to the right click = flat.** Past the right click = rising, up to +12 at the right end |

- A pitched-**up** slice plays its own material faster and then goes quiet until the next slice, so it sounds tighter
  and more staccato. A pitched-**down** slice plays only the start of its material, slower.
- **Pass-through with Pitch below the click** is slice-locked. At every slice boundary it picks up the live input
  exactly where it is and plays it slower and lower, until the next boundary snaps it back. A hit on the beat grid
  comes out **in time, with no added latency**: drums stay locked to the clock, each hit sounds like tape slowing
  under it, and only hits between boundaries drift later. Use ÷4 or ÷8 for tighter re-syncs.
  - **Pitch above the click:** pass-through stays untransposed. Live audio can't be played faster than it arrives
    without adding delay.
  - **While frozen:** pass-through is plain live audio.
  - Speed's ramp applies to glitched slices only.
- The total shift is limited to −48…+24 semitones, so steep ramps on ÷6 stop climbing at +2 octaves.
- **Speed remembers its last position.** On the right click the repeats are plain. On the left click they fall by 3
  semitones per repeat, so click it over for plain repeats.

## Freeze

Press Freeze, or send a gate to its jack. The buffer stops recording and the clock keeps running, so you can keep
re-cutting the same snapshot with any knob. Press it again to resume recording. The patch keeps playing the frozen
beat until one full beat of new audio has been recorded, so there's no stale audio at the changeover.

## Quick start

1. Patch a clock (one pulse per beat) into **Reset** and audio into the inputs (stereo, or mono into L). Set **blend**
   fully CW.
2. Turn **Record** on (Force): every beat now repeats the one before.
3. Turn **size** up through the zones for ÷2, ÷3, ÷4, ÷6 ratchets.
4. Turn Record off and raise **density** for random glitches and reverses.
5. Bring up **window** and **overlap** for lo-fi degradation.
6. Tap **Source** for Stutter mode: size fully CW (8 slices), Record on, and the beat is scrambled.
7. Press **Freeze** to hold a moment and keep chopping it.
8. Back in Glitch mode at ÷4, turn **speed** right of centre for rising ratchets, and patch a sequencer into the
   **pitch** 1V/oct jack to play the repeats as a melody.

## Differences from the Workshop Computer version

- **Buffer:** 43 s instead of 2.33 s. Beats can be up to 10 s long (bar-length clocks work), and Stutter drift
  reaches back up to 12 beats.
- **Outputs:** stereo processed audio only. The Nebulae has no outputs for the dry signal, slice clock, activity gate,
  slice ramp or clock mirror. Blend replaces the separate dry output.
- **Switch:** Up / Mid / Down becomes probability / Start gate / Record (Force), and they can be combined.
- **Freeze and Force** toggle on a gate's rising edge instead of following it, because those Nebulae inputs latch.
- **Mode** is the Source button and can change while playing. The WC chooses it at power-on.
- **Clock jitter:** control messages reach Pd over the network with about 1–3 ms jitter. Beat-length changes under
  5 ms are ignored, and each beat's slices end about 3 ms early (plus a 30 ms grace period) so a late pulse never cuts
  a slice off loudly.
