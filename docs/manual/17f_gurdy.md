# gurdy: a hurdy-gurdy drone

A Csound hurdy-gurdy. The drone synth's mechanical ancestor: a rosined wheel bows the drone strings
continuously while you play a melody on top. **Speed is the crank**: stop it, turn it steadily, or speed it up.
Bursts on the crank, or gates into **Reset**, make the trompette's buzzing bridge (the "dog") bark in rhythm.

**Bank:** Csound user (the page and button are in `nebulae_banks.txt` on the stick).

## Panel map
```
            [ speed ]            speed   = THE CRANK  stopped .. steady
 start                  size               (noon) .. fast and bright
                                 start   = MELODY NOTE (in the scale)
 density    [ pitch ]  overlap   size    = BOW PRESSURE  smooth .. scratchy
                                 density = DRONES  melody alone .. full
       blend     window          overlap = SYMPATHETIC STRINGS
                                 window  = BODY  small/bright .. large/warm
                                 blend   = dry <-> gurdy
                                 pitch   = THE KEY, 1V/oct (click = C2)

 [record]  [file]    [source]  [reset]   [freeze]
  DOG ON    MODE      MELODY    STROKE    HOLD NOTE
```

## Controls
| Control | Does |
|---|---|
| **Pitch** + 1 V/oct | The key: the bourdon. The click = C2. The mouche sits a fifth up (an octave in minor), the trompette an octave up |
| **Speed** | The crank. Fully anticlockwise: stopped (silent). Noon: a steady turn. Clockwise: faster, louder, brighter. The wheel has a little inertia, and a quick turn up makes the dog bark |
| **Start** + CV | The melody note: two octaves of the mode's scale, from an octave above the key. Patch a sequencer into Start's jack to play tunes |
| **Size** | Bow pressure (rosin): smooth → scratchy |
| **Density** | Drones: melody alone → the full drone |
| **Overlap** | Sympathetic strings: a halo that rings along, and on after the wheel stops |
| **Window** | The body: small and bright → large and warm |
| **Blend** | Dry input ↔ gurdy (it loads fully clockwise) |

| Button / jack | Does | LED |
|---|---|---|
| **Source** (button or gate) | The melody string on. At load: the drones alone | on = melody |
| **Reset** (button or gate) | A crank stroke: the dog barks. Patch a clock for a rhythm | — |
| **Record** (button or gate) | The dog buzzes all the time | on = buzzing |
| **Freeze** (button or gate) | Hold the melody note: Start and its CV are ignored until released | on = held |
| **File** | Mode: major → mixolydian → dorian (fifth drones) → minor (octave drones). The scale and the drones change together | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Stereo width (bourdon left, mouche right, melody centre) | wide-ish |
| alt **Size** | Wheel irregularity: a once-per-turn wobble | a little |
| alt **Density** | Melody glide (none → slides) | a little |
| alt **Overlap** | How hard a crank surge must be to make the dog bark | middle |
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount | a little |
| alt **Speed** | The Nebulae's input gain | — |

## Quick start
1. Load `013_gurdy`: the drones on C2 at a steady turn.
2. Press **Source** for the melody, then turn **Start** (or patch a sequencer into it).
3. Patch a clock into **Reset** for the dog's rhythm, or flick **Speed** up and back.
4. Press **File** for another mode; turn **Overlap** for the sympathetic halo, **Window** for the body.

## Notes
- The strings are bowed-string models (Csound's `wgbow`), tuned to within 0.2 %.
- CPU, measured offline: about three-quarters of the factory granular looper.
