# shift: frequency shifter in a feedback delay

A Pure Data effect. A frequency shifter moves every partial by the same number of Hz, so it doesn't transpose:
small shifts phase and swirl, big ones turn anything into bells and clangs. Here the shifter sits inside a
tape-style feedback delay, so **each echo is shifted again**. The echoes climb, or fall, step by step forever:
barber-pole echoes. Ring mode turns it into a ring modulator, and Barber mode fades the echoes out at the top
of a band, so the climb seems endless.

It's in the **Pd bank** as `N_shift` (yellow page, Reset button), file `12_shift.pd` in the repo.

## Panel map
```
            [ speed ]            speed   = TIME   2 ms .. 2 s
 start                  size               (clock on Reset: division)
                                 start   = PING-PONG  left <-> right
 density    [ pitch ]  overlap   size    = STEREO  right side same ->
                                           none -> opposite shift
       blend     window          density = FEEDBACK  0 .. 110 %
                                 overlap = DIRECT  shifted, no delay
                                 window  = TONE  dark <-> thin
                                 blend   = dry <-> wet
                                 pitch   = SHIFT  click = none

 [record]  [file]    [source]  [reset]   [freeze]
  FLIP      BARBER    RING      CLOCK     HOLD
```

## Controls
| Control | Does |
|---|---|
| **Pitch** | Shift amount. The click = no shift. Clockwise shifts up, anticlockwise down: just past the click it's 0.1 Hz (slow phasing), at the end of the turn 1 kHz (clang). Pitch CV sweeps it too, up to 2 kHz, but it isn't 1 V/oct (see Notes) |
| **Speed** | Delay time, 2 ms to 2 s. With a clock on the Reset jack, Speed picks a division of the beat in 7 zones instead: 1/16, 1/8, dotted 1/8, 1/4, 1/2, 1 bar, 2 bars. Time changes glide, like tape |
| **Density** | Feedback, 0 to 110 %. Above about 90 % the loop saturates softly instead of running away |
| **Window** | Tone of the loop. Noon = flat; anticlockwise = darker each pass; clockwise = thinner each pass. In Barber mode it moves the band instead (200 Hz to 4 kHz) |
| **Blend** | Dry ↔ wet (equal power) |
| **Size** | Stereo. Anticlockwise: both sides shift the same. Noon: the right side isn't shifted. Clockwise: the right side shifts the opposite way (left climbs, right falls) |
| **Start** | Ping-pong: anticlockwise = two separate loops; clockwise = each echo crosses to the other side |
| **Overlap** | Direct: the shifted input heard straight away, with no delay. Turn it up for a plain frequency shifter or ring modulator in front of the echoes |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (jack or button) | Clock. Pulses 30 ms to 4 s apart set the beat, and Speed then picks the division. With no pulse for 2 s (or 2.5 beats, if that's longer) it goes back to free time | — |
| **Source** (button or gate) | Ring: both sidebands at once (a ring modulator: up and down together) | on = Ring |
| **File** | Barber: the loop becomes a band (Window moves it). Echoes climb out of the band and fade, while new ones come in at the bottom: an endless climb. Press again for the tone filter | — |
| **Record** (button or gate) | Flip: the shift goes the other way, instantly | on = flipped |
| **Freeze** (button or gate) | Hold: the feedback goes to 100 % and the input is shut out. The loop keeps going round, still shifting and climbing | on = held |

Pd can't light the File LED, so Barber has no light: you hear it (the echoes thin out at the top and bottom).

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Wow depth: the tape's slow pitch wobble (0 to 4 ms of delay swing) | a little (0.6 ms) |
| alt **Size** | Drive into the loop's soft clip (×1 to ×6): more = warmer, denser long tails | ×2 |
| alt **Density** | Low cut in the loop (20 to 500 Hz): keeps down-shifted echoes from piling up as rumble | 27 Hz |
| alt **Overlap** | Wow rate (0.1 to 5 Hz) | about 0.5 Hz |
| **Source + Record** | All of the above back to their defaults | — |

Alt values only count once you move the knob (holding Source shows the old values first).

## Quick start
1. Patch something into the inputs. Load `N_shift`. Blend at noon, Density at about 10 o'clock, Speed at noon.
2. Turn **Pitch** a few clicks clockwise: each echo comes back a little higher. Turn further for bigger steps
   and metallic clangs. Anticlockwise falls instead. Click Pitch for no shift (a plain tape delay).
3. Turn **Density** up: the echoes keep climbing. Press **Freeze** to hold the loop and play over it.
4. Press **Source** for Ring; press **File** for Barber and turn **Window** to move its band.
5. Patch a clock into **Reset**: the echoes lock to the beat, and Speed picks the division.

## Notes
- **Pitch CV isn't 1 V/oct.** One knob covers 0.1 Hz to 1 kHz, about 13 octaves, while 1 V/oct would only give
  the 5 octaves of the knob's travel. So CV into Pitch sweeps the shift on the same curve as the knob: fast
  near the ends, gentle near the click.
- Shifting changes the sound's harmonic relationships, so a chord or a voice turns inharmonic. Small shifts
  (under 5 Hz) are the classic phaser-like swirl.
- Freeze holds the level, but the top end softens over the first second (the delay reads between samples,
  like tape), then stays.
- The shifter is Pd's own Hilbert filter pair (the one in `hilbert~`). From 100 Hz to 12 kHz the unwanted
  sideband is 45 to 60 dB down. Below about 50 Hz and above 15 kHz the shift gets less clean (both directions
  leak), which the low cut and the tone filter mostly take care of in the loop.
- CPU, measured offline: about a quarter of shimmer's.
