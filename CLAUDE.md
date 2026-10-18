# CLAUDE.md

Read [`HANDOFF.md`](HANDOFF.md) before doing anything in this repo. It covers project status, the Nebulae facts that
constrain every patch, the generate → batch-test → commit workflow, and tool gotchas.

Key rules:
- `.pd` files are generated: edit `tools/gen.py` / `tools/gloop.py`, then run `python tools/gen.py`.
- Test offline (`pd -nogui -batch -r 48000`, check WAVs with `tools/wavpeaks.py`) before handing a patch to the owner,
  who tests on real hardware.
- Write for unknown-version vanilla Pd (see HANDOFF.md §4).
