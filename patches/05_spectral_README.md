# 05_spectral — Spectral Clouds+ for the Nebulae (user guide)

WIP: CURRENT CLICKS

A spectral instrument in the spirit of **WorkshopSpectral** (the Workshop Computer adaptation of Julius Kammerl's
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

## First steps

A guided tour, about ten minutes. Each step builds on the one before.

**0. Clean slate.** The Nebulae carries button states and Speed over from the last instrument, so check first:
- **Record**, **Freeze** and **Source** LEDs off. Press any that are lit. (Tap Source; don't hold it.)
- **Speed** turned to the centre: it snaps there, and the band pattern stands still.
- **Pitch** on its click (no shift).

**1. Set up.**
1. Patch a sustained sound into the inputs: a pad, a drone, a held chord, or noise.
2. Set the knobs:
   - **blend** fully CW (wet only);
   - **density** at noon;
   - **size** about 2 o'clock;
   - **window** about 2 o'clock;
   - **overlap** and **start** fully CCW.

You should hear your sound with slowly shifting holes in it.

**2. Density.**
1. Sweep **density** from CCW to CW: sparse ringing bands → your sound with holes → nearly the full sound.
2. Leave it at noon.

**3. Size.**
1. Turn **size** down to about 9 o'clock: a few broad bands, like a random multiband gate.
2. Turn it up to full: fine, comb-like shimmer.
3. Leave it around 1 o'clock.

**4. Re-roll and smoothing.**
1. Press **Reset**: every band gets a new random gain, and the bands morph to it.
2. Turn **window** fully CCW and press Reset again: now the bands snap.
3. Turn **start** up a little: re-rolls now happen on their own, slow at first and faster as you turn.
4. Try **window** CCW with **start** high for a stuttering spectral gate.
5. Then set start back to CCW and window to about 2 o'clock.
6. Optional: patch a clock into the **Reset** jack, with start CCW, for re-rolls in time.

**5. Texture.** Turn up **overlap**: transients smear into a wash and the stereo image widens. Then back to CCW.

**6. Drift.**
1. Turn **Speed** right of centre: the hole pattern climbs up through the spectrum and wraps round, like a barber
   pole.
2. Turn it left of centre and it falls.
3. Further from the centre is faster.
4. Back to the centre to stop.

**7. Freeze.**
1. Press **Freeze** while the sound is playing: the spectrum holds, and the bands keep moving over it.
2. Play something different into it: the held sound changes colour, because normal freeze takes its phase from the
   live input.
3. Pull the input: the level drops.
4. Now tap **Source** (LED on = Sealed) and re-patch the input: the held sound rings on by itself.
5. Press **File** to re-capture whatever is playing now, without unfreezing.

**8. Play the freeze.**
1. Keep Freeze and Sealed on and turn **Pitch**: the held spectrum transposes, from 3 octaves down to 2 up.
2. Patch a sequencer into the **1V/oct** jack and the frozen sound becomes a playable chord.
3. Click Pitch to return to the original.

**9. Gather.**
1. Turn Freeze off and press **Record**.
2. Change chords or notes slowly: each new sound hangs on and blurs into the next, fading over several seconds.
3. Press **Freeze** too: the fading stops, and anything louder you play now **adds** to the hold. Build up a cloud
   chord by chord.
4. **Hold Source** and turn **size** to set how long gathered sound takes to fade.
5. Press Record and Freeze again to return to live.

**10. Alt layer.** Hold **Source** and move a knob:
- **blend:** tape mix (fully CCW is off);
- **window:** tape time;
- **overlap:** tape feedback;
- **density:** tape wow;
- **start:** stereo spread (the left and right band patterns drift apart).

Each alt knob takes over once you move it.

**Back to plain:**
- Record, Freeze and Source off;
- Pitch on its click;
- Speed at the centre;
- tape mix (alt blend) fully CCW.

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
- **No clicks:** bands fade open and shut over about 50 ms rather than switching instantly, so drift and re-rolls
  don't tick on held notes. Snap smoothing (window CCW) is therefore a fast flicker rather than a hard chop.

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

Julius Kammerl (the Spectral Clouds algorithm), Émilie Gillet (Clouds), and My WorkshopSpectral card. All MIT.
