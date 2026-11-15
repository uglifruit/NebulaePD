# sc_strike: a plucked string

A SuperCollider plucked string (Karplus-Strong), with a pluck-position comb and a wooden body. Pluck it from
Reset, or let it pluck itself.

**Bank:** SuperCollider. Expect 5–10 s of silence while SuperCollider starts.

## Panel map
```
            [ speed ]            speed   = AUTO-PLUCK RATE
 start                  size     start   = PLUCK POSITION  thin <-> round
                                 size    = DECAY  0.3 .. 20 s
 density    [ pitch ]  overlap   density = BRIGHTNESS
                                 overlap = SECOND STRING  detune + width
       blend     window          window  = BODY  dry <-> wooden
                                 blend   = LEVEL
                                 pitch   = PITCH, 1V/oct (click = C4)

 [record]    [file]  [source]  [reset]  [freeze]
  AUTO-PLUCK          CHORD     PLUCK    SUSTAIN
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | Pitch (click = C4). A sequencer into Pitch + a gate into Reset = a melody |
| **Start** | Pluck position: thin (near the bridge) → round (middle) |
| **Size** | Decay (0.3 – 20 s) |
| **Density** | Brightness of the pluck |
| **Window** | Body: dry string → resonant wooden body |
| **Overlap** | Second string: detune and stereo width |
| **Speed** | Auto-pluck rate (0.5 – 16 a second) |
| **Blend** | Level |

| Button / jack | Does | LED |
|---|---|---|
| **Reset** (button or gate) | Pluck. A clock or trigger sequence plays it | — |
| **Record** (button or gate) | Auto-pluck on/off (its own clock) | on = auto |
| **Freeze** (button or gate) | Sustain: the string rings on | on = sustain |
| **Source** (button or gate) | Chord: adds a fifth | on = chord |

## Quick start
1. Load it and press **Reset**: a pluck.
2. Size for the decay, Density for brightness, Window for the body.
3. Patch a sequencer: CV → Pitch, gate → Reset. Or press Record and set Speed for a self-playing pattern.
