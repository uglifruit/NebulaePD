# Nebulae → Pd control protocol

Transport: TCP to `localhost:3000`, text FUDI, one message per control update: `name value;`
(see `upstream/pdsender.py`; `sim/send_fudi.py` reproduces it).

## Primary controls
| name | range | notes |
|---|---|---|
| start, size, density, overlap, blend, window | 0–1 | pot + CV |
| pitch | 0–1 | pot/encoder + 1V/oct CV. Modified log curve: **multiply by 5 octaves** for 1V/oct tracking (with a frequency bias). Encoder clicks to **0.6**. |
| speed | 0–1 | encoder + CV (bipolar). Clicks between **0.375 and 0.625**. |
| reset | 1 | 10 ms pulse on press/trigger |
| freeze, record | 0/1 | latching, **rising**-edge sensitive |
| file, source | 0/1 | latching, **falling**-edge sensitive |
| filestate | 0/1 | file button state, independent of gate |
| sourcegate | 0/1 | source gate input, independent of button |

## Alt controls (hold the **source** button; pots/encoders only — no CV)
`start_alt size_alt density_alt overlap_alt blend_alt window_alt pitch_alt record_alt file_alt source_alt freeze_alt`
(0–1, or 0/1 for buttons). `reset_alt` (resets all alts to defaults) and `speed_alt` (hardware input gain) are
handled by the Nebulae itself and not meant for your patch. The reference PDF lists a few alt-edge-sensitivity
details inconsistently (e.g. `record_alt`); treat button semantics as unverified.

## Notes
- The Python app also exposes `file` as an index limited by the number of loaded files (Csound side); in Pd the
  value is simply a latched 0/1 — verify on hardware.
- Pots use pickup ("resist") behaviour when switching between normal and alt layers, so alt values may not update
  until the pot passes the stored value.
- Send rate and smoothing are set in `control.py` (not reviewed) — treat updates as asynchronous, ~control rate.
