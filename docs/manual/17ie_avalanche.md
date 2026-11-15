# avalanche: four oscillators that charge, fire and kick each other

A Csound rhythm-and-tone generator. Four relaxation oscillators each charge towards their supply and fire, with a
sharp discharge, when they cross a threshold. Each firing kicks the others it's tied to, so the rhythms push and
pull, lock and slip. The fourth oscillator is a slow shutter that interrupts (or filters) the other three. Starve
the supply and they stutter, then stop. A fuzz smooths it all into tone, and a stereo reverb follows.

**Inspired by:** Jolin Lab **Tabor**. Our own design and name, not a copy.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = STARVE  full power at noon,
 start                  size               starved either way
                                 start   = OSC1's CROSS-MOD (kicked back)
 density    [ pitch ]  overlap   size    = OSC2's CROSS-MOD (kicked by 1)
                                 density = OSC2's RATE (x0.25 .. x4)
       blend     window          overlap = SHUTTER depth
                                 window  = SHUTTER rate (OSC4)
                                 blend   = NM (raw) <-> ZZ (fuzzed)
                                 pitch   = OSC1's RATE, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  SHUTTER   RANGE     INPUT     KICK      STEADY
  FILTERS   rhy/tone  STARVES
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | OSC1's rate, the fundamental: the click = 4 Hz in the rhythm range, C3 in the tone range (File) |
| **Start** | OSC1's cross-mod: how hard OSC2 and OSC3 kick it back when they fire |
| **Size** | OSC2's cross-mod: how hard OSC1 kicks it |
| **Density** | OSC2's rate, from a quarter to four times OSC1's |
| **Window** | OSC4's rate, the shutter: 0.2 to 20 Hz |
| **Overlap** | The shutter's depth: how much it interrupts the sound (or, with Record, how far it closes the filter) |
| **Speed** | Starve: full power at noon. Turning either way lowers the supply towards the threshold, so the oscillators slow, stutter, then fall silent |
| **Blend** | NM, the raw oscillators (ramps and spikes) ↔ ZZ, fuzzed and smoothed |

| Button / jack | Does | LED |
|---|---|---|
| **Freeze** | Steady (latching): the components' jitter stops, so the pattern settles into a repeating cycle | on = steady |
| **Reset** (button or gate) | Kick: every oscillator fires at once | flashes |
| **Record** | The shutter filters instead of interrupting (latching) | on = filtering |
| **Source** | Your input starves it (latching): the louder you play, the less power it has | on = your input starves it |
| **File** | Range: rhythm ↔ tone | — |
| **Pulse** out | TR: a 15 ms gate whenever two oscillators fire together, the engine's peaks | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | OSC3's rate (a multiple of OSC1's) | a little faster than OSC1 |
| alt **Size** | OSC3's cross-mod: how hard OSC1 and OSC2 kick it | some |
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount (a stereo reverb after) | a little |
| alt **Speed** | The Nebulae's input gain | — |

OSC1 kicks OSC2 and some of OSC3; OSC2 kicks OSC3 and back to OSC1; OSC3 kicks OSC1. OSC4 only shutters.

## Quick start
1. Load `avalanche`: OSC1 ticks at 4 Hz with the others joining in.
2. Turn **Density** for OSC2's rate, then **Size** and **Start** to tie the oscillators together: the rhythm locks, slips
   and tumbles.
3. Press **File** for the tone range: the same interplay as pitch. Play it from **Pitch** (1V/oct).
4. Turn **Speed** off noon to starve it into stutters. **Overlap** and **Window** bring the shutter in; **Blend** fuzzes.
5. **Freeze** settles a pattern you like into a loop; **Reset** (or a gate) kicks everything at once.

## Notes
- The oscillators are modelled sample by sample (charge, threshold, discharge), so their kicks land exactly.
- Patch **Pulse** to a drum: it fires on the engine's accents.
- CPU, measured offline: about three quarters of the factory granular looper, reverb included.
