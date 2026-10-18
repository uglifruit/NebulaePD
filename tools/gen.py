#!/usr/bin/env python3
"""Generates the .pd files in lib/, patches/ and sim/ (source of truth).

Run from the repo root:  python tools/gen.py
Instruments embed the control receiver as a [pd nebulae_controls] subpatch so each
patch is a single self-contained file (no abstraction paths to worry about on the Nebulae).
"""
import os

PRIMARY = "start size density overlap blend window pitch speed record file source reset freeze filestate sourcegate".split()
ALT = "start_alt size_alt density_alt overlap_alt blend_alt window_alt pitch_alt record_alt file_alt source_alt freeze_alt".split()


class Canvas:
    def __init__(self, header):
        self.header = header
        self.lines = []
        self.n = 0

    def add(self, line):
        self.lines.append(line)
        self.n += 1
        return self.n - 1

    def obj(self, x, y, text):
        return self.add(f"#X obj {x} {y} {text};")

    def msg(self, x, y, text):
        return self.add(f"#X msg {x} {y} {text};")

    def text(self, x, y, text):
        text = text.replace(",", " \\,").replace(";", " -")
        return self.add(f"#X text {x} {y} {text};")

    def raw(self, line):
        return self.add(line)

    def connect(self, a, o, b, i):
        self.lines.append(f"#X connect {a} {o} {b} {i};")

    def sub(self, x, y, name, canvas):
        """Embed another canvas as [pd name] subpatch."""
        self.lines.append(canvas.header.replace("%NAME%", name))
        self.lines.extend(canvas.lines)
        self.lines.append(f"#X restore {x} {y} pd {name};")
        self.n += 1
        return self.n - 1

    def render(self):
        return "\n".join([self.header.replace("%NAME%", "")] + self.lines) + "\n"


def controls_canvas(top=False):
    """netreceive 3000 -> route -> [s name]; plus DSP-on at load."""
    c = Canvas("#N canvas 0 50 900 520 10;" if top else "#N canvas 0 50 900 520 %NAME% 0;")
    c.text(10, 5, "Nebulae control receiver (FUDI over TCP 3000). Use [r name] elsewhere.")
    nr = c.obj(10, 30, "netreceive 3000")
    r1 = c.obj(10, 80, "route " + " ".join(PRIMARY))
    r2 = c.obj(10, 230, "route " + " ".join(ALT))
    c.connect(nr, 0, r1, 0)
    for i, name in enumerate(PRIMARY):
        s = c.obj(10 + (i % 8) * 105, 130 + (i // 8) * 30, f"s {name}")
        c.connect(r1, i, s, 0)
    c.connect(r1, len(PRIMARY), r2, 0)
    for i, name in enumerate(ALT):
        s = c.obj(10 + (i % 6) * 140, 290 + (i // 6) * 30, f"s {name}")
        c.connect(r2, i, s, 0)
    # DSP on shortly after load (unverified whether the Nebulae launcher already does this).
    lb = c.obj(600, 30, "loadbang")
    d = c.obj(600, 55, "delay 300")
    m = c.msg(600, 80, "\\; pd dsp 1")
    c.connect(lb, 0, d, 0)
    c.connect(d, 0, m, 0)
    c.text(10, 380, "pitch: 0-1 modified log curve; x5 octaves for 1V/oct. clicks to 0.6. speed clicks 0.375-0.625.")
    c.text(10, 400, "speed_alt / reset_alt are consumed by the Nebulae (input gain / reset-all-alts); not routed here.")
    return c


def smooth(c, x, y, src, ms=20):
    pk = c.obj(x, y, "pack f %d" % ms)
    ln = c.obj(x, y + 25, "line~")
    c.connect(src, 0, pk, 0)
    c.connect(pk, 0, ln, 0)
    return ln


def drone_patch():
    c = Canvas("#N canvas 0 50 1000 700 10;")
    c.text(10, 5, "01_drone: demo instrument. pitch=osc pitch(27.5-880Hz), overlap=detune, window=lowpass,")
    c.text(10, 20, "density=tremolo rate(0-20Hz), size=tremolo depth, blend=dry(adc)/wet(osc).")
    c.sub(780, 5, "nebulae_controls", controls_canvas())

    # pitch -> freq signal
    rp = c.obj(10, 60, "r pitch")
    m1 = c.obj(10, 85, "* 60")
    m2 = c.obj(10, 110, "+ 21")
    m3 = c.obj(10, 135, "mtof")
    for a, b in [(rp, m1), (m1, m2), (m2, m3)]:
        c.connect(a, 0, b, 0)
    fl = smooth(c, 10, 160, m3, 30)

    # overlap -> detune ratio signal
    ro = c.obj(200, 60, "r overlap")
    d1 = c.obj(200, 85, "* 0.02")
    d2 = c.obj(200, 110, "+ 1")
    c.connect(ro, 0, d1, 0)
    c.connect(d1, 0, d2, 0)
    dl = smooth(c, 200, 160, d2)

    o1 = c.obj(10, 220, "phasor~")
    mul = c.obj(200, 220, "*~")
    o2 = c.obj(200, 250, "phasor~")
    c.connect(fl, 0, o1, 0)
    c.connect(fl, 0, mul, 0)
    c.connect(dl, 0, mul, 1)
    c.connect(mul, 0, o2, 0)
    sm = c.obj(10, 290, "+~")
    c.connect(o1, 0, sm, 0)
    c.connect(o2, 0, sm, 1)
    # remove DC (two phasors 0..1 summed -> 0..2) and scale
    ac = c.obj(10, 315, "-~ 1")
    sc = c.obj(10, 340, "*~ 0.25")
    c.connect(sm, 0, ac, 0)
    c.connect(ac, 0, sc, 0)

    # window -> lowpass
    rw = c.obj(400, 60, "r window")
    w1 = c.obj(400, 85, "* 110")
    w2 = c.obj(400, 110, "+ 20")
    w3 = c.obj(400, 135, "mtof")
    for a, b in [(rw, w1), (w1, w2), (w2, w3)]:
        c.connect(a, 0, b, 0)
    wl = smooth(c, 400, 160, w3, 30)
    lp = c.obj(10, 370, "lop~")
    c.connect(sc, 0, lp, 0)
    lp2 = c.obj(10, 395, "lop~")
    c.connect(lp, 0, lp2, 0)
    c.connect(wl, 0, lp, 1)
    c.connect(wl, 0, lp2, 1)

    # tremolo: lfo rate from density, depth from size
    rd = c.obj(600, 60, "r density")
    t1 = c.obj(600, 85, "* 20")
    c.connect(rd, 0, t1, 0)
    lfo = c.obj(600, 120, "osc~")
    c.connect(t1, 0, lfo, 0)
    l1 = c.obj(600, 145, "+~ 1")
    l2 = c.obj(600, 170, "*~ 0.5")
    c.connect(lfo, 0, l1, 0)
    c.connect(l1, 0, l2, 0)
    rs = c.obj(800, 60, "r size")
    sl = smooth(c, 800, 90, rs)
    dep = c.obj(600, 200, "*~")
    c.connect(l2, 0, dep, 0)
    c.connect(sl, 0, dep, 1)
    inv = c.obj(600, 225, "*~ -1")
    one = c.obj(600, 250, "+~ 1")
    c.connect(dep, 0, inv, 0)
    c.connect(inv, 0, one, 0)
    am = c.obj(10, 430, "*~")
    c.connect(lp2, 0, am, 0)
    c.connect(one, 0, am, 1)

    # blend dry/wet
    rb = c.obj(400, 300, "r blend")
    bl = smooth(c, 400, 330, rb)
    wet = c.obj(10, 470, "*~")
    c.connect(am, 0, wet, 0)
    c.connect(bl, 0, wet, 1)
    inv2 = c.obj(400, 370, "*~ -1")
    one2 = c.obj(400, 395, "+~ 1")
    c.connect(bl, 0, inv2, 0)
    c.connect(inv2, 0, one2, 0)
    adc = c.obj(200, 440, "adc~ 1 2")
    dryl = c.obj(200, 470, "*~")
    dryr = c.obj(300, 470, "*~")
    c.connect(adc, 0, dryl, 0)
    c.connect(one2, 0, dryl, 1)
    c.connect(adc, 1, dryr, 0)
    c.connect(one2, 0, dryr, 1)
    sl_ = c.obj(10, 520, "+~")
    sr_ = c.obj(300, 520, "+~")
    c.connect(wet, 0, sl_, 0)
    c.connect(dryl, 0, sl_, 1)
    c.connect(wet, 0, sr_, 0)
    c.connect(dryr, 0, sr_, 1)
    dac = c.obj(10, 570, "dac~ 1 2")
    c.connect(sl_, 0, dac, 0)
    c.connect(sr_, 0, dac, 1)
    return c


def template_patch():
    c = Canvas("#N canvas 0 50 700 400 10;")
    c.text(10, 5, "00_template: controls + audio passthrough. Copy and build on this.")
    c.sub(10, 30, "nebulae_controls", controls_canvas())
    a = c.obj(10, 80, "adc~ 1 2")
    d = c.obj(10, 120, "dac~ 1 2")
    c.connect(a, 0, d, 0)
    c.connect(a, 1, d, 1)
    c.text(10, 160, "Use [r density] [r pitch] etc. anywhere in this patch.")
    return c


def sim_patch():
    c = Canvas("#N canvas 0 50 760 420 10;")
    c.text(10, 5, "Desktop control simulator. Sends the same names as the Nebulae via [s name] (no TCP needed).")
    c.text(10, 20, "Open in the same Pd session as an instrument, or use sim/send_fudi.py over TCP 3000.")
    names = "start size density overlap blend window pitch speed".split()
    for i, n in enumerate(names):
        x = 10 + i * 85
        v = c.raw(f"#X obj {x} 50 vsl 25 150 0 1 0 0 empty empty {n} 0 -9 0 10 -262144 -1 -1 0 1;")
        s = c.obj(x, 220, f"s {n}")
        c.connect(v, 0, s, 0)
    for i, n in enumerate("record file source freeze".split()):
        x = 10 + i * 85
        t = c.raw(f"#X obj {x} 260 tgl 20 0 empty empty {n} 25 10 0 10 -262144 -1 -1 0 1;")
        s = c.obj(x, 290, f"s {n}")
        c.connect(t, 0, s, 0)
    b = c.msg(360, 260, "1")
    ps = c.obj(360, 290, "s reset")
    c.connect(b, 0, ps, 0)
    c.text(400, 262, "<- reset (momentary)")
    return c


def write(path, canvas):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        f.write(canvas.render())
    print("wrote", path)


if __name__ == "__main__":
    write("lib/nebulae_controls.pd", controls_canvas(top=True))
    write("patches/00_template.pd", template_patch())
    write("patches/01_drone.pd", drone_patch())
    write("sim/sim_controls.pd", sim_patch())
