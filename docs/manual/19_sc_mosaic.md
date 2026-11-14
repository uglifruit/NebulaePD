# sc_mosaic — concatenative resynthesis

A SuperCollider instrument that rebuilds what you play out of another sound. Every few milliseconds it looks
through a recording (the **corpus**) for the piece that best matches the input right now, in loudness, noisiness
and brightness, and plays that piece instead. Play a drum loop and it answers with matching bits of a choir; talk
and a piano talks; play anything into it with its own past as the corpus and it stutters and echoes itself.

It's in the **SuperCollider bank** as `07_sc_mosaic` (orange page, File button). Expect 5–10 s of silence while
SuperCollider starts.

## Panel map
```
            [ speed ]            speed   = CORPUS SPEED centre stop,
 start                  size               clicks 1x, ends 4x
                                 start   = LOOK BACK  0.2-10 s
 density    [ pitch ]  overlap   size    = GRAIN  10-250 ms
                                 density = MATCH  loose -> strict
       blend     window          overlap = MATCH ON loud/noisy ->
                                           bright/tilt
                                 window  = SEARCH WIDTH
                                 blend   = dry <-> mosaic
                                 pitch   = TRANSPOSE, 1V/oct

 [record]  [file]    [source]  [reset]   [freeze]
  HEAR CORP NEXT FILE SELF      FILE START FREEZE CORPUS
```

## Controls
| Control | Does |
|---|---|
| **Size** | Grain: how long each matched piece is, 10 ms (a fine, buzzy mosaic) to 250 ms (recognisable phrases) |
| **Density** | Match: anticlockwise = loose (pieces nearly at random), clockwise = strict (the best match every time) |
| **Start** | How far back in the corpus store it looks, 0.2 to 10 s |
| **Window** | How wide the search is: a narrow slice of the store, or all of it |
| **Overlap** | What counts as a match: anticlockwise = loudness and noisiness (rhythm), clockwise = brightness and tilt (timbre) |
| **Speed** | The corpus file's speed as it feeds the store: centre = stopped (the store keeps what it has), the clicks = 1× (left = backwards), the ends = 4×. It loads on the forward click |
| **Pitch** + 1 V/oct | Transpose the output, ±3 octaves; the click = none |
| **Blend** | Dry ↔ mosaic (equal power). It loads mostly wet |

| Button / jack | Does | LED |
|---|---|---|
| **File** | Next stick file as the corpus (wav, aif and flac all work here) | — |
| **Source** | The corpus is the input's own past instead of the file | on = self |
| **Freeze** (button or gate) | Freeze the corpus: the store stops taking in new sound | on = frozen |
| **Record** (button or gate) | Also hear the corpus itself (its level on alt Start) | on = hearing it |
| **Reset** (button or gate) | The file back to its start | — |

## Alt layer (hold Source)
| Control | Does | Default |
|---|---|---|
| alt **Start** | Corpus level when Record is on | half |
| alt **Size** | Stereo width | a little |
| alt **Window** | Reverb size | medium |
| alt **Blend** | Reverb amount | a little |

## Quick start
1. Put some recordings on the stick (voices, choirs, pianos, field recordings). Load `07_sc_mosaic`.
2. Patch a drum loop or a voice into the inputs. After a few seconds (the corpus store fills) you hear the input
   rebuilt from the first file.
3. Press **File** for another corpus. Turn **Size** up for longer pieces, **Density** down for a looser,
   more random mosaic.
4. Turn **Overlap** clockwise to match on timbre instead of rhythm.
5. Press **Source** to use your own playing as the corpus; **Freeze** to keep a corpus you like.

## Notes
- The output keeps the input's dynamics: loud where you play loud, silent where you stop.
- The corpus is a rolling 10 s store of the file as it plays (or of the input). With Speed at the centre, or
  Freeze on, it stops changing.
- It's built on `Concat` (sc3-plugins, in the module's SuperCollider). CPU and the feel of the matching are for
  the hardware test.
