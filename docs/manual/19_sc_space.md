# sc_space: diffuse delays into a long reverb

A SuperCollider effect for big spaces. What you play goes through diffuse delays (echoes that smear into a
wash), then into a long, lush reverb, from a small room to a minute of tail. Freeze holds the space for as long
as you like, Duck makes it dip while you play and swell in the gaps, Shimmer adds an octave above, and Reset
clears the tails in a moment.

It's in the **SuperCollider bank** as `08_sc_space` (orange page, Source button).

## Panel map
```
            [ speed ]            speed   = MOVEMENT  gentle between
 start                  size               the clicks, deeper at ends
                                 start   = DELAY TIME  20 ms .. 1.4 s
 density    [ pitch ]  overlap   size    = SIZE  small -> huge
                                 density = DIFFUSION  echoes -> wash
       blend     window          overlap = DELAY FEEDBACK
                                 window  = DECAY  0.3 .. 60 s
                                 blend   = dry <-> space
                                 pitch   = TONE  click = neutral

 [record]  [file]    [source]  [reset]   [freeze]
  DUCK      HOLD      SHIMMER   CLEAR     FREEZE
```

## Controls
| Control | Does |
|---|---|
| **Blend** | Dry ↔ space (equal power). Fully clockwise = the space only, for a send/return |
| **Start** | Delay time of the diffuse echoes: 20 ms to 1.4 s (Size adds a little: up to about 0.3 s at the largest) |
| **Overlap** | Delay feedback: one echo → many → nearly endless |
| **Density** | Diffusion: anticlockwise = distinct echoes; clockwise = they smear into a wash |
| **Size** | Room size, for the delays and the reverb together: small and close → huge |
| **Window** | Reverb decay: 0.3 s to 60 s |
| **Pitch** | Tone: the click = neutral; clockwise = brighter, anticlockwise = darker (more damping) |
| **Speed** | Movement: between the two clicks the space moves gently; towards either end the modulation gets deeper and faster (chorus, then warble) |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Hold the space as it is: nothing new goes in, and the sound you hear is held for as long as Freeze is on. Play over it | on = frozen |
| **File** (held) | Momentary freeze, for as long as you hold it | — |
| **Record** (button or gate) | Duck: the space dips while you play and swells back in the gaps (alt Density = how much, alt Window = how fast it comes back) | on = ducking |
| **Source** (button or gate) | Shimmer: an octave above goes round the reverb, so the tail rises and sparkles (alt Blend = how much) | on = shimmer |
| **Reset** (button or gate) | Clear: the tails drain away in a moment (also a frozen hold), and new sound goes in again after about 0.7 s | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Delays ↔ reverb: anticlockwise = only the diffuse delays; clockwise = only the reverb | half and half |
| alt **Size** | Stereo width: mono → full | full |
| alt **Density** | Duck depth (up to −30 dB) | 70 % |
| alt **Window** | Duck release: 50 ms to 2 s | about 0.2 s |
| alt **Overlap** | Bass decay: the low end rings shorter (anticlockwise) or longer (clockwise) than the rest | the same |
| alt **Blend** | Shimmer amount | 40 % |

Alt values only count once you move the knob (holding Source shows the old values first).

## Quick start
1. Patch a sound into the inputs. Load `08_sc_space` and wait for it to start (SuperCollider takes 5 to 10 s).
2. Blend at noon, Window at noon (a few seconds of tail). Play.
3. Turn **Window** up for a long wash, **Size** up for a bigger room, **Pitch** anticlockwise to darken it.
4. Turn **Overlap** and **Start** for rhythmic echoes inside the space; **Density** down to hear them distinct.
5. Press **Freeze** and play over the held space; **Reset** clears everything.

## Notes
- Freeze holds what you hear exactly (a spectral snapshot of the space). The reverb carries on underneath and
  takes over again when you let go.
- The output goes through a limiter at −0.5 dB. Like the other SuperCollider patches, this delays everything,
  the dry sound too, by 20 ms (measured). Mixing the dry signal back in elsewhere will comb-filter slightly; for
  a send/return, turn Blend fully clockwise.
- CPU, measured offline on the PC: about the same as sc_mosaic. Not measured on the module yet.
