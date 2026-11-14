"""11_topokits: 06_topo with sample kits from the stick (built 2026-11-14 while the owner was away: decisions to
review in docs/TOPOKITS.md). The pattern engine, synth voices and controls are topo's (tools/topo.py,
topo_patch(kits=True)); this module adds the kit layer.

- Kits are stick files named kit<N>_<voice>.wav, N = 1..8, voice = kick snare clap hat open perc. Any subset: a
  voice without a file in the selected kit stays the synth voice.
- Kit select: alt Pitch (hold Source, turn Pitch), every KIT_STEP of its accumulator one kit (0 = synth only);
  it applies once the encoder moves.
- Router: each tp_trig_<V> hit goes to the sample voice (tp_smp_<V>) when the kit has that sound, else to topo's
  synth voice (tp_syn_<V>).
- Sample voices: two halves per voice (round robin; the new hit fades the other half out in 3 ms), vline~ index
  at topo's tune x file sr / 48k, velocity, decay (alt Blend) below 1 shortens the hit with a 5 ms fade; a closed
  hat chokes the open hat. Panned like topo's voices.
"""

import math

from glitch import chain
from spectral import op, pickup
from resonator import V, mn, mx
from chop import prog, when, tab, packmsg, tprint, vrecv, to_voice   # noqa: F401
import topo

SR = 48000
KITS = 8
KIT_STEP = 0.025                 # alt Pitch accumulator per kit (about 12 encoder clicks)
NAMES = dict(K="kick", S="snare", C="clap", CH="hat", OH="open", P="perc")
VOICES = topo.VOICES
MAXLEN = 5 * SR                  # longest sample read (5 s)


def idx(k, vi):
    return k * len(VOICES) + vi


def loader(c, x, y, kit_dir):
    """At load: for every kit and voice, glob the exact file name; if it exists read it into tk_<k>_<V> and set
    tk_have / tk_len / tk_sr."""
    lb = c.obj(x, y, "loadbang")
    d = chain(c, x, y, lb, ["delay 200"])
    for k in range(1, KITS + 1):
        for vi, Vn in enumerate(VOICES):
            xx, yy = x + (vi % 6) * 160, y + 60 + (k - 1) * 260
            i = idx(k, vi)
            m = c.msg(xx, yy, f"symbol {kit_dir}/kit{k}_{NAMES[Vn]}.wav")
            c.connect(d, 0, m, 0)
            up = op(c, xx, yy + 44, "unpack s f", op(c, xx, yy + 22, "file glob", m))
            sf = chain(c, xx, yy + 44, up, [f"list prepend read -resize -maxsize {MAXLEN}",
                                            f"list append tk_{k}_{Vn}", "list trim", "soundfiler"])
            # info (sample rate) first, then the frame count
            ts = op(c, xx + 80, yy + 154, "t f b", op(c, xx + 80, yy + 132, "unpack f", (sf, 1)))
            c.connect(ts, 1, c.msg(xx + 120, yy + 176, str(i)), 0)
            tws = c.obj(xx + 80, yy + 198, "tabwrite tk_sr")
            c.connect(c.n - 2, 0, tws, 1)
            c.connect(ts, 0, tws, 0)
            tf = op(c, xx, yy + 154, "t f f b", sf)
            c.connect(tf, 2, c.msg(xx + 40, yy + 176, str(i)), 0)
            twl, twh = c.obj(xx, yy + 220, "tabwrite tk_len"), c.obj(xx + 40, yy + 242, "tabwrite tk_have")
            c.connect(c.n - 3, 0, twl, 1)
            c.connect(c.n - 3, 0, twh, 1)
            c.connect(tf, 1, twl, 0)
            c.connect(chain(c, xx + 40, yy + 198, tf, ["> 0"]), 0, twh, 0)


def kits(Canvas, kit_dir, test=False):
    """Router + sample voices + loader -> two outlet~ (summed with the synth voices before topo's crunch)."""
    c = Canvas("#N canvas 0 50 1600 1200 %NAME% 0;")
    c.text(10, 5, "kits: tp_trig_V -> sample (tk_have) or synth. Kit = alt Pitch. Files kit<N>_<voice>.wav")
    n = (KITS + 1) * len(VOICES)
    for i, tn in enumerate(("tk_have", "tk_len", "tk_sr")):
        c.obj(1000 + i * 130, 30, f"table {tn} {n}")
    for k in range(1, KITS + 1):
        for vi, Vn in enumerate(VOICES):
            c.obj(1000 + vi * 100, 60 + k * 22, f"table tk_{k}_{Vn} 1")
    for n in ("tp_tune", "tp_decay", "tk_kit"):
        vrecv(c, 10 + ["tp_tune", "tp_decay", "tk_kit"].index(n) * 120, 30, n)
    c.connect(c.obj(400, 30, "loadbang"), 0, c.msg(400, 52, "\\; tk_kit 0"), 0)
    # kit select on alt Pitch (pickup: the stored accumulator doesn't count until the encoder moves)
    pickup(c, 600, 30, "pitch_alt", "tk_kitq", ["clip 0 1", f"/ {KIT_STEP:g}", "int", f"clip 0 {KITS}"])
    chain(c, 600, 260, c.obj(600, 260, "r tk_kitq"), ["change", "s tk_kit"])
    if test:
        tprint(c, 800, 260, c.obj(800, 240, "r tk_kit"), "kit")
    loader(c, 10, 2000, kit_dir)
    KIT = V("tk_kit")
    sums = [c.obj(10, 1800, "+~"), c.obj(200, 1800, "+~")]
    first = [True, True]
    outs = [c.obj(10, 1900, "outlet~"), c.obj(200, 1900, "outlet~")]
    acc = [None, None]
    for vi, Vn in enumerate(VOICES):
        x0 = 10 + vi * 260
        # router
        tr = op(c, x0, 100, "t f f", c.obj(x0, 80, f"r tp_trig_{Vn}"))
        c.connect(tr, 1, c.obj(x0 + 60, 122, f"v tk_vel{Vn}"), 0)
        rt = when(c, x0, 140, (tr, 0), tab("tk_have", KIT * len(VOICES) + vi), both=True)
        for o, dst in ((0, f"tp_smp_{Vn}"), (1, f"tp_syn_{Vn}")):
            c.connect(op(c, x0 + o * 100, 230, f"v tk_vel{Vn}", (rt, o)), 0, c.obj(x0 + o * 100, 252, f"s {dst}"), 0)
        if test:
            tprint(c, x0, 280, c.obj(x0, 260, f"r tp_smp_{Vn}"), f"smp_{Vn}")
        # sample voice: two halves
        p = f"tk{Vn}_"
        t = op(c, x0, 420, "t b b b b b", op(c, x0, 400, "t b", c.obj(x0, 380, f"r tp_smp_{Vn}")))
        I = KIT * len(VOICES) + vi
        prog(c, x0 + 300, 380, (t, 4), [
            (f"v:{p}vt", 1 - V(f"{p}vt")),
            (f"s:{p}s0", 1 - V(f"{p}vt")), (f"s:{p}s1", V(f"{p}vt")),          # spigots: the half that starts
            (f"v:{p}n", tab("tk_len", I)),
            (f"v:{p}rate", V("tp_tune") * tab("tk_sr", I) / 1000),           # samples per ms
            (f"v:{p}d", V(f"{p}n") / mx(1e-3, V(f"{p}rate")) * mn(1, V("tp_decay"))),
            (f"v:{p}i1", V(f"{p}rate") * V(f"{p}d")),
            (f"v:{p}dm", mx(0, V(f"{p}d") - 5)),
            (f"v:{p}vel", V(f"tk_vel{Vn}")),
            (f"v:{p}k", KIT),
        ])
        # table: tk_<kit>_<V>
        ml = chain(c, x0, 460, op(c, x0, 440, f"v {p}k", (t, 3)), [f"makefilename tk_%d_{Vn}", "list prepend set",
                                                                     "list trim"])
        for h in (0, 1):
            sp = op(c, x0 + h * 120, 540, "spigot", ml)
            c.connect(c.obj(x0 + h * 120 + 50, 518, f"r {p}s{h}"), 0, sp, 1)
            c.connect(sp, 0, c.obj(x0 + h * 120, 562, f"s {p}tab{h}"), 0)
        ix = packmsg(c, x0, 600, (t, 2), [f"{p}i1", f"{p}d"], "0 \\, \\$1 \\$2")
        en = packmsg(c, x0 + 130, 600, (t, 1), [f"{p}vel", f"{p}dm"], "0 \\, \\$1 0.5 \\, 0 5 \\$2")
        if test:
            tprint(c, x0 + 200, 640, packmsg(c, x0 + 200, 560, (t, 0), [f"{p}d", f"{p}rate", f"{p}k"],
                                             "\\$1 \\$2 \\$3"), f"dur_{Vn}")
        ch = c.msg(x0 + 200, 720, "0 3")
        c.connect(t, 0, ch, 0)
        for h in (0, 1):
            for m_, nm, gate in ((ix, "ix", h), (en, "en", h), (ch, "en", 1 - h)):
                sp = op(c, x0 + h * 120, 760 + (nm == "en") * 40 + (m_ is ch) * 80, "spigot", m_)
                c.connect(c.obj(x0 + h * 120 + 50, 740 + (nm == "en") * 40 + (m_ is ch) * 80,
                                f"r {p}s{gate}"), 0, sp, 1)
                c.connect(sp, 0, c.obj(x0 + h * 120, 782 + (nm == "en") * 40 + (m_ is ch) * 80, f"s {p}{nm}{h}"), 0)
        # a closed hat chokes the open hat's sample halves
        if Vn == "CH":
            c.connect(c.obj(x0, 900, "r tp_trig_CH"), 0, c.msg(x0, 922, "\\; tkOH_en0 0 3 \\; tkOH_en1 0 3"), 0)
        # signal
        vs = None
        for h in (0, 1):
            xi = op(c, x0 + h * 120, 1000, "vline~", c.obj(x0 + h * 120, 980, f"r {p}ix{h}"))
            rd = op(c, x0 + h * 120, 1040, f"tabread4~ tk_1_{Vn}", xi)
            c.connect(c.obj(x0 + h * 120 + 60, 1020, f"r {p}tab{h}"), 0, rd, 0)
            ev = op(c, x0 + h * 120 + 60, 1060, "vline~", c.obj(x0 + h * 120 + 60, 1040, f"r {p}en{h}"))
            g = op(c, x0 + h * 120, 1090, "*~", rd, ev)
            vs = g if vs is None else op(c, x0, 1120, "+~", vs, g)
        th = (topo.PAN[Vn] + 1) * math.pi / 4
        for chn, gg in enumerate((math.cos(th) * math.sqrt(2), math.sin(th) * math.sqrt(2))):
            gm = op(c, x0 + chn * 100, 1160, f"*~ {gg:.4f}", vs)
            acc[chn] = gm if acc[chn] is None else op(c, x0 + chn * 100, 1190, "+~", acc[chn], gm)
    for chn in (0, 1):
        c.connect(acc[chn], 0, outs[chn], 0)
    del sums, first
    return c
