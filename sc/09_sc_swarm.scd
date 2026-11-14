/*
09_sc_swarm: a drone of 32 drifting, detuned oscillators. Designed with the owner 2026-11-14 (Pitch click = C2,
Source gathers the swarm onto a chord, Blend mixes the input); the rest is in docs/SC_SWARM.md. MIT.

  Pitch + V/oct   the note (click = C2)
  Size            spread: unison -> beating -> a cluster (up to an octave either side)
  Density         how many play: 1 .. 32
  Window          how fast each one wanders
  Overlap         waveform: triangle (soft) -> saw (bright)
  Speed           breathing: between the clicks a gentle shimmer; towards the ends deeper, slower swells
  Start           chord shape (with Source on): fifth, major, minor, sus4, maj7, min7, add9, fourths
  Blend           dry input <-> swarm
  Source          gather: the swarm splits onto the chord's notes (glides there; alt Density = how slowly)
  Reset           shake: every oscillator jumps to a new place in the spread
  Freeze          hold: the wandering stops where it is
  Record          hush: the swarm fades out (LED on) and swells back when pressed again
  alt (hold Source): Start = stereo width, Size = sub octave level, Density = gather time, Overlap = tone (low-pass)
*/
~neb = ();
~neb.name = \sc_swarm;
~neb.controls = [\speed, \pitch, \start, \size, \density, \overlap, \window, \blend, \freeze, \source, \record,
	\start_alt, \size_alt, \density_alt, \overlap_alt];
~neb.def = SynthDef(\sc_swarm, { |out = 0, speed = 0.5, pitch = 0.6, start = 0.15, size = 0.3, density = 0.6,
	overlap = 0.3, window = 0.4, blend = 1, freeze = 0, source = 0, record = 0, t_reset = 0,
	start_alt = 1, size_alt = 0, density_alt = 0.4, overlap_alt = 1|
	var n = 32;
	var shapes = [[0, 7, 12, 19], [0, 4, 7, 12], [0, 3, 7, 12], [0, 5, 7, 12], [0, 4, 7, 11], [0, 3, 7, 10],
		[0, 4, 7, 14], [0, 5, 10, 15]];
	var base = 65.406 * (2 ** (((pitch - 0.6) * 5).clip(-4.5, 4.5)));
	var hold = 1 - (freeze > 0.5);
	var cents = size.squared * 1200;
	var rate = window.linexp(0, 1, 0.02, 3);
	var count = density.linlin(0, 1, 1, n);
	var chord = (start * 8).floor.clip(0, 7);
	var gath = (source > 0.5).lag(density_alt.linexp(0, 1, 0.3, 20));
	var mv = ((speed - 0.5).abs * 2).clip(0, 1);
	var bdepth = mv.linlin(0, 1, 0.1, 0.9).lag(0.2);
	var brate = mv.linexp(0, 1, 2, 0.08).lag(0.2);
	var o = overlap.lag(0.1);
	var hush = 1 - (record > 0.5).lag(3);
	var w = start_alt.lag(0.1);
	// the chord's four notes, looked up once (a flat table: shape x 4 + note)
	var notes = 4.collect { |k| Select.kr((chord * 4) + k, shapes.flat) * gath };
	// waveform: triangle (VarSaw at width 0.5, soft) -> saw (width towards 0): one oscillator per voice (CPU)
	var vw = 0.5 - (0.49 * o);
	var voices, mix, sub, sig, b;
	voices = n.collect { |i|
		// Freeze: Gate holds each wandering value where it is (an LFNoise at rate 0 doesn't hold still)
		var drift = Gate.kr(LFNoise2.kr(rate * Rand(0.6, 1.4)), hold);
		var shake = Lag.kr(TRand.kr(-1, 1, t_reset + Impulse.kr(0)), 0.3);
		var off = ((drift * 0.6) + (shake * 0.4)) * cents;
		var semi = notes[i % 4];
		var f = base * (2 ** (((semi * 100) + off) / 1200));
		var amp = (count - i).clip(0, 1).lag(0.3);
		var br = 1 - (bdepth * ((Gate.kr(LFNoise2.kr(brate * Rand(0.7, 1.3)), hold) * 0.5) + 0.5));
		Pan2.ar(VarSaw.ar(f, Rand(0, 1), vw), Rand(-1, 1) * w, amp * br);
	};
	mix = voices.sum / count.sqrt;
	sub = SinOsc.ar(base * 0.5) * size_alt.lag(0.1) * 0.5;
	sig = LPF.ar(mix, overlap_alt.linexp(0, 1, 300, 18000).lag(0.1)) * 0.3 + sub;
	sig = LeakDC.ar(sig) * hush;
	b = blend.lag(0.05);
	Out.ar(out, Limiter.ar((SoundIn.ar([0, 1]) * cos(b * 0.5pi)) + (sig * sin(b * 0.5pi)), 0.95));
});

if(~nrtTest.isNil, {
	s.waitForBoot({
		~neb.def.add;
		s.sync;
		~nebSynth = Synth(~neb.name);
		~neb.controls.do { |name|
			OSCdef(("neb_" ++ name).asSymbol, { |msg| ~nebSynth.set(name, msg[1]) }, ("/neb/" ++ name).asSymbol,
				recvPort: 3000);
		};
		OSCdef(\neb_reset, { |msg| if(msg[1] > 0.5, { ~nebSynth.set(\t_reset, 1) }) }, '/neb/reset',
			recvPort: 3000);
		"09_sc_swarm running".postln;
	});
});
