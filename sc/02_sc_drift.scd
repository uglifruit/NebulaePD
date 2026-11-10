/*
02_sc_drift: an evolving drone / pad. Five detuned voices, a morphing oscillator, a resonant filter that drifts.

  Pitch + V/oct   pitch, 1 V/oct (click = C4)
  Start           oscillator: saw -> pulse -> sine
  Size            detune spread (unison -> wide)
  Density         filter cutoff (80 Hz .. 12 kHz)
  Window          filter resonance
  Overlap         drift depth (filter and pulse width movement)
  Speed           drift rate (encoder; 0.02 .. 8 Hz)
  Blend           output level
  Freeze          sub-octave on/off
  Source          chord: adds a fifth and an octave
  Reset           swell: the level dips and blooms back (button or gate)

How the patch is built (all four uf2 example patches work this way): every control arrives as OSC /neb/<name> and
goes to the synth argument of the same name; the SynthDef does all the mapping. With ~nrtTest set, the file only
defines ~neb.def (tools/sc_nrt_tests.py renders it offline on the PC).
*/
~neb = ();
~neb.name = \sc_drift;
~neb.controls = [\speed, \pitch, \start, \size, \density, \overlap, \window, \blend, \freeze, \source];
~neb.def = SynthDef(\sc_drift, { |out = 0, speed = 0.625, pitch = 0.6, start = 0, size = 0.3, density = 0.5,
	overlap = 0.3, window = 0.3, blend = 0.6, freeze = 0, source = 0, t_reset = 0|
	var base = (60 + ((pitch - 0.6) * 60)).lag(0.01).midicps;
	var rate = speed.lag(0.1).linexp(0, 1, 0.02, 8);
	var depth = overlap.lag(0.1);
	var spread = size.lag(0.1).linexp(0, 1, 0.0005, 0.03);
	var ratios = [1, 1, 1, 1, 1] * (1 + (spread * [-2, -1, 0, 1, 2]));
	var chord = Select.kr(source > 0.5, [[1, 1, 1, 1, 1], [1, 1.5, 1, 2, 1.5]]);
	var freqs = base * ratios * chord;
	var drift = LFNoise2.kr(rate ! 5) * depth;
	var morph = start.lag(0.1) * 2;
	var voices = freqs.collect { |f, i|
		var phase = Rand(0, 2pi);
		SelectX.ar(morph, [
			Saw.ar(f),
			Pulse.ar(f, (0.5 + (drift[i] * 0.4)).clip(0.05, 0.95)),
			SinOsc.ar(f, phase)
		])
	};
	var sub = SinOsc.ar(base * 0.5) * Lag.kr(freeze > 0.5, 0.2) * 0.5;
	var sig = Splay.ar(voices, 0.8) * 0.25 + (sub ! 2);
	var cutoff = (density.lag(0.1).linexp(0, 1, 80, 12000) * (2 ** (LFNoise2.kr(rate) * depth * 2))).clip(40, 16000);
	var rq = window.lag(0.1).linlin(0, 1, 1.0, 0.08);
	var swell = EnvGen.kr(Env([1, 0.15, 1], [0.02, 1.5], [-2, 2]), t_reset);
	sig = RLPF.ar(sig, cutoff, rq);
	sig = LeakDC.ar(sig).tanh;
	sig = Limiter.ar(sig * swell * blend.lag(0.05), 0.95);
	Out.ar(out, sig);
});

if(~nrtTest.isNil, {
	s.waitForBoot({
		~neb.def.add;
		s.sync;
		~neb.synth = Synth(~neb.name);
		~neb.controls.do { |name|
			OSCdef(("neb_" ++ name).asSymbol, { |msg| ~neb.synth.set(name, msg[1]) }, ("/neb/" ++ name).asSymbol,
				recvPort: 3000);
		};
		OSCdef(\neb_reset, { |msg| if(msg[1] > 0.5, { ~neb.synth.set(\t_reset, 1) }) }, '/neb/reset',
			recvPort: 3000);
		"02_sc_drift running".postln;
	});
});
