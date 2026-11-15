# c_synth: Qu-Bit's synth voice

Qu-Bit's built-in synth: a saw-like and a square oscillator, a sine sub an octave down, and a Moog-style ladder
filter. Qu-Bit marks it as a work in progress, so several controls do nothing.

**Bank:** factory. This page is a summary from its code.

## Panel map
```
            [ speed ]            speed   = (not used)
 start                  size     start   = (not used)
                                 size    = (not used)
 density    [ pitch ]  overlap   density = FILTER CUTOFF
                                 overlap = RESONANCE
       blend     window          window  = SUB LEVEL
                                 blend   = WAVE  square <-> saw
                                 pitch   = PITCH, 1V/oct
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The note: 80 Hz fully anticlockwise to 2.5 kHz, 1 V/oct (the click is about 640 Hz) |
| **Density** | Filter cutoff (0 – 6 kHz) |
| **Overlap** | Filter resonance |
| **Blend** | Waveform: square ↔ saw |
| **Window** | Sub oscillator (a sine an octave down) level |
| **Speed, Start, Size** | Not used |

The buttons and the alt layer do nothing.

## Quick start
1. Load it: a tone at once (it has no envelope; patch a VCA after it to play notes).
2. Turn **Density** and **Overlap** for the filter, **Blend** for the wave, **Window** for weight.

## Notes
- Mono: the same signal on both outputs.
