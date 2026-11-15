# The two granular loopers: what's different

The stick had the granular looper twice:
- `a_granularlooper`: the built-in one in the **Factory bank** (Speed in the middle, Record button).
- `001_a_granular_looper_Factory_Default`: a copy that was in the **Csound user bank** (taken off the stick on
  2026-11-15, because the Factory one does everything it does).

They sound the same. The grains, pitch, speed, recording, overdubbing and the alt knobs all come from almost
identical Csound code, so Qu-Bit's manual covers both. The difference is the firmware around them. It gives
the looper five extras, but only to an instrument named exactly `a_granularlooper`. The user-bank copy has a
different name, so it never gets them. Its Csound code is also an older release, and that release can't save
the loop to a WAV.

## What only the Factory looper does
| | Factory `a_granularlooper` | User-bank `001_…Factory_Default` |
|---|---|---|
| **alt File** (hold Source, press File): the order the files play in | Each press steps forward → backward → random. The File light shows the order: it fades up for forward, fades down for backward, and flickers for random | File always steps forward. Alt File still counts presses, but nothing reads them |
| **alt Freeze** (hold Source, press Freeze): grain sync | With Density fully anticlockwise, every gate into the **Source jack** fires a grain. The Source jack stops switching between file and live input, so the clock only fires grains | The grains still fire, but every gate also flips Source between file and live input, so a clock makes it jump back and forth |
| **File while on the live input** (Source lit) | Ignored: the file stays where it was, so you go back to the same file when you leave live input | Each press still moves on through the files without telling you, so you come back to a different file |
| **Reset light** | Flashes at the end of every loop (with the EOL gate), and stays lit when the loop is very short | Only lights when you press Reset |
| **Speed lights while recording** | Both turn **red** while Record is on | They keep showing the speed |
| **Hold File, press Freeze**: save the loop to the stick | The Freeze and Record lights blink while it writes `neb_buffer_N.wav` to the stick | Fails: all five lights flash 10 times. The older Csound code never reports how long the loop is |

## The same in both
- **Hold File, press Reset**: clears the recorded loop.
- **Hold File, press Source**: reloads the instrument.
- Every alt knob (hold Source and turn), including the input gain on alt Speed, and alt Record (the overdub mode).
- The 300-second record buffer, and the same buffer, ksmps and sample-rate settings.

## Which to use
Use the **Factory** one. It is the newer code and has every feature, which is why the user-bank copy came off
the stick.

`bt_storyteller` (Csound user, yellow page, File) is the newer Factory code, so it can save loops with File + Freeze. Like
the `001` copy, it is in the user bank under a different name, so it lacks the other five extras in the table.

## Why
The firmware (`controlhandler.py` and `ui.py`) checks `if currentInstr == "a_granularlooper"` before it sets the
file order, mutes the Source gate for grain sync, holds the file on live input, and drives the Reset and red
Speed lights. Saving a WAV reads the loop length from the instrument's `bufferlength` channel and the audio
from tables 200 and 201. Only the Factory version sets that channel and uses those tables.
