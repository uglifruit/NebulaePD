# topo kits — topo with sample kits

topo's drum patterns playing **your own samples** from the stick. Everything else is topo: the same map,
mutation, Freeze, File, clock and knobs (see the topo guide). What's new is that each of the six drum sounds can
be a sample, chosen kit by kit.

It's in the **Pd bank** as `M_topokits` (yellow page, Source button), file `11_topokits.pd` in the repo. The
original `H_topo` stays as it is.

## Making a kit
Put WAV files on the stick named like this, up to 8 kits:

```
kit1_kick.wav   kit1_snare.wav   kit1_clap.wav
kit1_hat.wav    kit1_open.wav    kit1_perc.wav
kit2_kick.wav   ...              kit8_perc.wav
```

- A kit can be any subset: a voice without a file in that kit plays topo's synth voice as usual. So
  `kit2_kick.wav` alone gives you your own kick over topo's snare and hats.
- Mono or stereo (the left channel is used), any sample rate, up to 5 s each. Use WAV: Pd can't read FLAC.
- The files are read when the patch loads, so copy them to the stick before choosing `M_topokits`.

## Choosing a kit
**Hold Source and turn Pitch**: about every 12 clicks is the next kit, from **kit 0 = synth only** (where it
starts) up to kit 8. There's no light for it, so count clicks or listen. Clicking Pitch while holding Source
resets the alt layer, which also takes you back to kit 0. The kit only changes once you turn the encoder.

## What reaches the samples
| Control | On the samples |
|---|---|
| Pattern (map, Fill, Chaos, mutation, Freeze, File) | Exactly as for the synth: the samples play topo's hits |
| Velocity (accents) | Sample level |
| **Pitch** (tune) | Sample pitch and speed, like a sampler (higher = shorter) |
| alt **Blend** (decay) | Below noon it shortens each sample (with a 5 ms fade); at noon and above the whole sample plays |
| Closed hat | Cuts the open-hat sample off |
| **Blend** (Sound) | Only the synth voices; the crunch past noon is on everything |

## Notes
- A new hit on the same voice fades the previous one out in 3 ms (two players per voice), so rolls don't click.
- Panning is topo's (each voice has its place).
- CPU, measured offline: about 1.2× topo.
