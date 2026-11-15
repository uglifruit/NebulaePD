# lattice: a network of delays from reverb to multi-tap echo

A Csound stereo effect. Eight delay paths are tied together into a network. With Plexus low, all eight are
entangled and you hear a dense reverb; turned up, they come apart into two separate paths with extra taps, a
multi-tap echo. Between the two lie rooms, combs, smeared echoes and metallic resonances. There are no modes: every
control moves smoothly through the whole range.

**Inspired by:** Make Noise **Soundhack Plexiphon** (with Tom Erbe). Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = COUPLE  left/right apart ->
 start                  size               interlaced
                                 start   = PLEXUS  reverb -> multi-tap
 density    [ pitch ]  overlap   size    = (not used)
                                 density = DIFFUSE  sharp -> blurred
       blend     window          overlap = DECAY  to super-infinite
                                 window  = COLOR  dark <- 1 o'clock -> bright
                                 blend   = MIX  live <-> network
                                 pitch   = SIZE  5 ms .. 1.4 s (1V/oct)

 [record]  [file]    [source]  [reset]   [freeze]
     -      SKEW      HOLD      CLEAR     SEND
            off/inv/            (empty)   (held: nothing
            tandem                         new goes in)
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Size: the time between paths, 5 ms to 1.4 s (120 ms at the click). A room's size with Plexus low, an echo's repeat with it high. It glides |
| **Start** | Plexus: all eight paths entangled (reverb) → two apart, with taps (multi-tap echo) |
| **Overlap** | Decay: the feedback, up to super-infinite at the top (it grows, held by a soft limiter) |
| **Density** | Diffuse: sharp ↔ softened (the input blurred into early reflections before the network) |
| **Window** | Color: darker below 1 o'clock, brighter above, more with every pass |
| **Speed** | Couple: left and right apart (dual mono) → fully interlaced |
| **Blend** | Mix: live ↔ the network |
| **Size** | Not used |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** (button or gate) | Send (momentary): while held, or while a gate is high, nothing new goes in; the network rings on | on while held |
| **Reset** (button or gate) | Clear: the network empties | flashes |
| **Source** | Hold (latching): the Decay goes to infinity and nothing new goes in | on = holding |
| **File** | Skew, three settings in turn: off → inverse (Plexus, Size and Color pushed apart, left against right) → tandem (pushed the same way) | — |
| **Record** | Not used | — |
| **Pulse** out | High while the network is sounding (above −30 dB): an envelope follower as a gate | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Input level into the network (unity at three quarters) | unity |
| alt **Size** | Skew amount (how far File's skew pushes the sides apart) | a little |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `lattice` and play into it: a reverb.
2. Turn **Start** (Plexus) up slowly: the reverb opens into echoes. **Pitch** sets their time (or the room's size).
3. **Overlap** lengthens the tail; at the top it never dies (super-infinite).
4. **Window** darkens or brightens it, **Density** blurs it, **Speed** spreads it between the sides.
5. Hold **Freeze** to keep new sound out, or latch **Source** to hold what's there forever. **Reset** clears it.
6. Press **File** for skew: the two sides go different ways (inverse) or further the same way (tandem).

## Notes
- Moving **Pitch** with the network full re-pitches what's in it, like tape.
- CPU, measured offline: about two fifths of the factory granular looper.
