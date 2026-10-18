# instr/ - Csound instruments

- `00_template.instr` - minimal passthrough with config + globals reference (start here)
- `demos/` - small factory/community instruments copied from the upstream repo (MIT, Qu-Bit Electronix; V1 ports by
  Chris Erin, originals by Collin Russell and others - see headers). For study; each is one file for the USB root.

| demo | what it does | size |
|---|---|---|
| test_io | audio passthrough, source = mute (the official template) | 17 lines |
| synth_voice | vco2 saw/square + sub, moogladder; pitch=freq, density=cutoff, overlap=res, blend=wave, window=sub | 45 |
| drip_water | `dripwater` physical model through ladder filter, random drip scheduling | 35 |
| vinyl_dust | `dust2` noise through moogvcf2 | 29 |
| bowed_drone | bowed string / physical model drone | 45 |
| fm_grit | extreme-ratio FM + reverb | 60 |

`gendyn_fixed.instr` - rewrite of GENDYN (original boot-loops; see `docs/INSTR.md`). Untested on hardware.
Not copied: original GENDYN. Larger upstream instruments (Granular Looper ~1000 lines,
Realms, Mars Affects, Avalon, One Shot) are in `external/QB_Nebulae_V2/Instruments/` for reading.
