# 06_topo — Topo drums for the Nebulae (user guide)

A clocked **drum machine that writes its own patterns** and plays them on its **own analog-style drum synth**. Send it a
clock and it plays. The patterns come from a map of drum styles that you move through with two knobs (the idea of
Mutable Instruments' Grids, with our own map). They can **mutate**, by hand or on their own, and you can always go
back **home**.

- **Six voices:** kick, snare, clap, closed hat, open hat (choked by the closed hat), perc/tom. All are synthesised,
  so there are no samples to load.
- **The map:** 25 hand-written patterns on a 5 × 5 grid, from four-on-the-floor to broken polyrhythms, and from sparse
  to busy. Map X/Y blend smoothly between neighbouring patterns.
- **Mutation:** Record re-draws a few steps; Window re-draws some every cycle; Speed makes the map position drift.
  Freeze locks it all.
- **Sound:** one knob morphs between three hand-designed kits: 808-ish, 909-ish, crunchy. The sounds never change
  unless you turn it.

Install: copy `06_topo.pd` to the **root** of the Nebulae USB drive, then load it from the instrument selector.
No audio input is used.

---

## Panel map

```
                 [ speed ]                       start   = MAP X   four-on-floor -> electro/funk -> hip-hop -> breaks -> broken
   start                          size           size    = MAP Y   sparse -> busy
                                                 density = FILL    how many steps play (bottom of the travel = silence)
   density       [ pitch ]        overlap        overlap = CHAOS   random ghost notes / dropouts on every pass
                                                 window  = MUTATE  auto re-draws per cycle (CCW = none)
          blend          window                  blend   = SOUND   808 (CCW) -> 909 (noon) -> crunch (CW)
                                                 pitch   = TUNE    whole kit, 1V/oct (click = normal)
                                                 speed   = DRIFT   map position wanders; still between the two clicks

  [record]  [file]   [source]  [reset]  [freeze]
   MUTATE    HOME     (alt)     CLOCK     LOCK
```

| Button / jack | Does | LED |
|---|---|---|
| **Reset** jack | **Clock in: one pulse = one 16th step.** The button is a manual step (tap through the pattern) | flashes |
| **Source** gate jack | **Back to step 1:** the next clock plays the pattern's first step (send it once per bar or phrase) | — |
| **Freeze** (button or gate) | **Lock:** no automatic mutation, no drift. Record still mutates | on = locked |
| **Record** (button or gate) | **Mutate now:** re-draws a burst of steps (4, up to 16 with Window turned up). Every gate edge mutates once. The LED just toggles; ignore it | — |
| **File** (button) | **Short press: go home.** Brings back the home pattern. **Hold 1 s: store** the current pattern as home. Home at load = the plain map | — |
| **Source** button | Hold for the alt layer. Its latch does nothing here (the Source gate jack also toggles it) | — |

All six pots have CV jacks. Sweeping **Map X/Y** with an LFO or envelope is the classic way to play this kind of
sequencer. **Fill** CV makes builds and breakdowns. **Pitch** tracks 1V/oct for the whole kit.

**Alt layer (hold Source):**

| Knob | Does | Default |
|---|---|---|
| start | **Kick fill** offset (± around the main Fill) | centre = none |
| size | **Snare + clap fill** offset | centre |
| density | **Hats fill** offset | centre |
| overlap | **Perc fill** offset | centre |
| window | **Length** 1 – 32 steps | 32 (fully CW) |
| blend | **Decay**: the whole kit ×0.25 (tight) – ×4 (boomy) | ×1 at centre |
| speed encoder | **Swing**: click = straight; 8 detents either way = full **12/8** (triplet); in between = in between | straight |

Alt knobs (and alt Speed) only act once you **move** them, so holding Source doesn't make anything jump to where
another instrument left them.

**Swing and input gain:** alt Speed is also the Nebulae's **input gain**. 06 has no audio input, so that doesn't
matter here, but the gain carries over to the next instrument. **Click alt Speed (straight = 0 dB) before switching
instruments**, or swing CCW: that only ever lowers the input gain, while CW raises it.

## First steps

**0. Clean slate.**
- **Freeze** LED off (tap it if it's lit).
- **blend** fully CCW (the 808 kit). The Nebulae remembers blend from the last instrument, which usually leaves it
  fully CW (the crunch kit).
- **Speed** between its two clicks (no drift). It snaps to the clicks.
- **Pitch** on its click.

**1. A beat.**
1. Patch a clock into **Reset**, one pulse per 16th note. For 120 BPM that is 8 pulses per second (a ×4 clock from a
   quarter-note clock).
2. Set **start** fully CCW, **size** at noon, **density** at noon, and **overlap**, **window** and **blend** fully
   CCW.
3. You hear a four-on-the-floor house beat: kick on every beat, clap + snare on 2 and 4, open hats on the off-beats.
   (No clock? Tap **Reset** to step through it by hand.)
4. Patch a once-per-bar trigger into the **Source gate** jack, so step 1 lands on your downbeat.

**2. Fill.** Turn **density** down: the beat strips to its skeleton (kick, backbeat), then to silence. Turn it up:
ghost notes, 16th hats and perc fills appear, in order of importance. Every pattern is written so the lowest fill is
the core of the groove.

**3. The map.** Turn **start** (X) slowly from CCW to CW: house → electro/funk → hip-hop → breakbeat/jungle → broken
polyrhythms. Turn **size** (Y): sparse at CCW, busy at CW. Positions between the 25 written patterns blend their
neighbours, so every knob position is a groove.

**4. Chaos.** Bring **overlap** up a little: each pass adds or drops random ghost notes. Nothing is stored, so turn it
back down and the pattern is clean again.

**5. Mutate by hand.** Press **Record**: a few steps change, and they stay changed. Press it again for more. Too far?
A **short File press** brings home back.

**6. Find a home.** When a mutated pattern is good, **hold File for a second**: that is now home. Keep mutating; a
short press returns to it.

**7. Let it evolve.** Turn **window** up: the pattern re-draws a few steps at the end of every cycle (32 steps, or the
Length you set). Low = slow evolution, high = constant change. Press **Freeze** to hold what you have; press it again
to carry on.

**8. Drift.** Turn **Speed** past either click: the map position wanders by itself around where X/Y are set, drifting
between styles. The further from centre, the faster. Freeze stops it.

**9. Sound.** Turn **blend**:
- **CCW, 808-ish:** a long boomy kick, a tonal snare, and the 808's six-oscillator metal hats.
- **Noon, 909-ish:** a punchier, slightly driven kick, a snappier snare, brighter hats.
- **CW, crunch:** a short, hard-driven kick, a noisy snare, high hats, a rim-like perc. Past noon a **crunch
  bus** fades in on the whole kit: drive into a hard clip, a bit-crush down to 6 bits, and sample-rate reduction
  down to 6 kHz, all getting stronger towards CW.

Positions in between blend the two neighbouring kits, and any position is repeatable. The sounds don't change unless
the knob (or its CV) moves. Pitch tunes the whole kit, and alt **blend** sets the decay.

## How the patterns work

Each of the 25 map patterns gives every step of four lanes (kick, snare, hats, perc) an **importance** level. **Fill**
sets the level a step needs to play, so low Fill keeps only the most important hits. The strongest snare steps also
fire the **clap**, and the strongest hat steps are **open** hats (a closed hat chokes an open one).

Mutations are stored as changes on top of the map, so X/Y still move the groove while your mutations come along. Each
mutation picks a random lane and step, then does one of three things:
- **Move** (half of them): swap a playing step with a silent neighbour up to 2 steps away. The hit moves in time.
- **Flip** (30%): turn a silent step on, or a playing step off.
- **Heal** (20%): remove the change on that step, so heavy mutation doesn't turn into noise.

**Home** stores those changes and the drift position. **Length** shortens the cycle, which is good for odd meters:
12 steps for 3/4, 20 for 5/4.

## Differences from Grids

- **Our own map**, not Grids' (Grids' code is GPL; this repo is MIT). It is laid out by style on X and density on Y,
  with four lanes instead of three, and a 25-node grid like Grids'.
- **Built-in drum synth** with six voices, instead of trigger outputs (the Nebulae has no gate outs for Pd).
- **Mutation, home, lock and drift** are new. Chaos works like Grids' randomness.
- **Clock = 16ths only** (Grids also takes 24 ppqn). Swing and Length are on the alt layer.
- No accent outputs: accent is the velocity of each hit (stronger steps play louder).

## Credits

Pattern-map concept after Émilie Gillet's Mutable Instruments Grids. Map data, mutation and drum synth are original to
this patch.
