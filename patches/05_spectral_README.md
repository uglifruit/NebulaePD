# 05_spectral — Spectral Clouds+ for the Nebulae (user guide)

A spectral instrument in the spirit of **WorkshopSpectral** (the Workshop Computer port of Julius Kammerl's
**Spectral Clouds**). It is the same idea, grown up for the Nebulae rather than copied.

The patch splits your sound into **log-spaced frequency bands** and gives each band a random gain. A probability
threshold shuts the quiet ones, so the sound you hear is your input with **moving holes carved through its
spectrum**: few bands give broad, obvious sweeps, and many bands give fine, comb-like shimmer.

New on the Nebulae:
- **true stereo**, with a Spread control;
- **spectral pitch** (1V/oct, ±3 octaves): the frozen spectrum becomes a playable chord;
- **band drift**: the hole pattern scrolls up or down the spectrum like a barber pole;
- **gather**: layer several spectra into one cloud;
- **re-capture**;
- the original's **tape delay**, on the alt layer.

Install: copy `05_spectral.pd` to the **root** of the Nebulae USB drive, then load it from the instrument selector.

---

## Panel map

```
                 [ speed ]                       start   = RE-ROLL RATE  CCW = only on Reset, then every ~3 s .. every frame
   start                          size           size    = BANDS  4 .. 128 (log-spaced)
                                                 density = PROBABILITY  how many bands are open
   density       [ pitch ]        overlap        window  = SMOOTHING  CCW = snap, then 50 ms .. 3 s morphs
                                                 overlap = TEXTURE  phase scramble: smears into a wash
          blend          window                  blend   = dry <-> wet
                                                 pitch   = SPECTRAL PITCH, 1V/oct (click = original pitch)
                                                 speed   = DRIFT  the band pattern rises (right) / falls (left), centre = still

  [record]  [file]   [source]  [reset]  [freeze]
   GATHER  RE-CAPTURE  SEALED   RE-ROLL   FREEZE
```

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (jack or button) | **Re-roll** every band gain now. Clock it for rhythmic spectral patterns (start fully CCW so re-rolls only come from the clock) | flashes |
| **Freeze** | **Freeze** the spectrum: hold the magnitudes (see below). A gate into the Freeze jack toggles it | on = frozen |
| **Source** | **Sealed**: a frozen sound keeps its own phases, so nothing of the live input gets through. (Gathered sound always does this.) Hold Source for the alt layer | on = sealed |
| **Record** | **Gather**: the spectrum keeps the loudest of what it holds and what comes in, decaying slowly. A gate into the Record jack toggles it | on = gathering |
| **File** (button) | **Re-capture**: take the current input as the new held spectrum, without unfreezing | — |

All six pots have CV jacks, so every parameter can be modulated. Pitch tracks 1V/oct.

**Alt layer (hold Source):** start = **stereo spread**; size = **gather decay** (CCW ≈ 1 s, CW ≈ 60 s to silence);
window = **tape time** (25 ms – 2 s); overlap = **tape feedback**; density = **tape wow**; blend = **tape mix**
(CCW = off).

Alt knobs only take effect once you **move** them, so holding Source never makes the tape or spread jump to where the
knob happened to be left by another instrument.

## What to feed it

It carves holes in a spectrum, so it needs a **sustained, harmonically rich spectrum** to carve.

- **Great:** pads, drones, held chords, noise (BANDS low + SMOOTHING slow turns noise into a slow chord progression),
  feedback, cymbals, room tone, whole mixes, distorted guitar, organ.
- **Poor:** drums and sparse plucks (41 ms of latency and a 2048-point window smear transients into a wash), single
  sine waves (one band does all the work), and anything quiet (the effect scales with the input).

**Quick start:**
1. Patch noise or a held chord in.
2. Set size about 2 o'clock, window slow (about 2 o'clock), density at noon, blend fully CW.
3. Sweep density and listen to the holes open and close.
4. Turn Speed to its click for a slow rising drift, or patch a clock into Reset.

## The band filter

| Control | What you hear |
|---|---|
| **density** low | sparse, isolated resonant bands: pitched, gated, hollow |
| **density** noon | the source clearly present, with moving holes punched through it |
| **density** high | nearly the full spectrum, with a subtle shimmer |
| **size** low (4–8 bands) | broad, obvious sweeps, close to a random multi-band gate |
| **size** high (64–128) | fine comb-like textures |
| **window** CCW | gains snap: with a fast re-roll rate this is a stuttering spectral gate |
| **window** CW | bands drift open and shut over seconds |
| **overlap** | phase scramble: transients smear into a diffuse wash; independent per side, so it also widens the image |

Things to know:
- **Silences:** with few bands, a low density can shut every band, so the patch goes quiet through the bottom of
  density's travel. Turn size up for a smoother density sweep. (The original works the same way.)
- **Density and smoothing:** the threshold follows how spread out the gains currently are, so density opens about the
  same number of bands whatever smoothing is set to.
- **Low end:** everything below about 190 Hz moves as one band, so bass doesn't chatter at high band counts.

## Freeze, Sealed, Gather, Re-capture

**Freeze (Source off)** holds the **magnitudes** and keeps taking **phase from the live input**. That keeps the hold
alive and animated, and what you play into it reshapes it. Like the original, it is an effect *on* a signal: pull
the input and the level drops (measured −9.6 dB) into a thinner sound.

**Sealed freeze (Source on)** also holds each partial's frequency and keeps rotating it, so the held sound sustains on
its own as a chord. Pull the input and it carries on (measured: level holds). This is the one to pitch around.

**Gather (Record):**
- Unfrozen, the held spectrum keeps the loudest of itself and the input, decaying at the alt-size rate. Sounds hang
  and blur into each other, like a spectral sustain.
- Frozen, the decay stops: whatever you play **adds** to the hold wherever it's louder. Freeze a chord, turn Gather
  on, and play another chord into it.
- Gathered partials always ring on at their own frequencies, whatever Source is set to, so they sustain cleanly
  after the input moves on or stops. Sharp changes in the input (a chord change) are gathered too, and fade like
  everything else.

**Re-capture (File)** replaces the hold with the current input in one frame: a quick "refreeze" without the gap of
unfreezing.

The band filter, drift, texture and pitch all keep working on the frozen sound.

## Spectral pitch

Pitch moves the whole processed spectrum, 1V/oct, from −36 to +24 semitones (click = no shift):
- Each partial is re-rendered at its new frequency with the right spectral shape, so levels stay put and the result
  is clean (measured: level within 0.1 dB from −36 to +24, frequency within the analysis resolution).
- The band holes stay where they are in frequency, so the content moves *through* them.

On **sealed frozen** material this turns the hold into a playable chord: sequence it, or sweep it.

On live material it works too, as a spectral pitch shifter, with the usual phase-vocoder softening of transients.

Fast knob sweeps sound a little smeared until the knob settles: phases re-align 40 ms after the last change.

## Drift (Speed)

Speed scrolls the band pattern through the spectrum:
- **Centre (0.5):** still.
- **The clicks:** one cycle every 4 s, rising to the right and falling to the left.
- **The ends:** 4 cycles a second, a barber-pole flutter.

Because it is a cycle, the pattern comes back to where it started.

**Note:** the Nebulae remembers Speed across instruments, so 05 may load already drifting. Turn Speed to the centre
for a still pattern.

## Stereo

Left and right are analysed separately, so the input's stereo image is kept.

| Alt start | Pattern |
|---|---|
| CCW | both sides share one band pattern |
| CW | the right side has its own pattern, for wide, unlinked holes |
| in between | blends the two |

Texture also decorrelates the sides.

## Tape delay (alt layer)

This is the original's TAPE mode, after the spectral engine: the holes are carved first, then the delay carries the
result off. It is deliberately tape-like:
- two-LFO wow and flutter;
- each repeat gets darker (damping in the loop);
- a loop highpass stops the low end piling up;
- the feedback path soft-clips;
- feedback is capped at 0.85, so tails resolve rather than freeze. (The patch already has freezes for that.)

Moving the time while repeats are sounding gives the tape-speed swoop.

## Differences from WorkshopSpectral

| | WorkshopSpectral (Workshop Computer) | 05_spectral (Nebulae) |
|---|---|---|
| FFT | 1024 points, mono out | 2048 points (finer, cleaner low end), true stereo |
| Latency | 21 ms | 41 ms (the dry path is delayed to match, so blend never combs) |
| Sealed freeze | hold the switch Down 2 s | Source latch (the LED shows it) |
| Re-roll | Pulse In 1 + X knob | Reset jack/button + start |
| Output level | Y on page 2 | soft clip on the output (fixed level). Use blend and your mixer |
| Pitch, drift, gather, re-capture, spread | — | new |
| Tape | alt-boot mode, replaces page 2 | always available on the alt layer |
| CV / pulse outs (density, re-roll pulse, load) | yes | not possible: Pd can't drive the Nebulae's outputs or LEDs |

## Credits

Julius Kammerl (the Spectral Clouds algorithm), Émilie Gillet (Clouds), and WorkshopSpectral. All MIT.
