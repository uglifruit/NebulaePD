/*
03_sc_strike: a plucked string (Karplus-Strong) with a resonant body. Play it from the Reset gate.

  Reset           pluck (button or gate; a trigger or clock into the Reset jack plays it)
  Pitch + V/oct   pitch, 1 V/oct (click = C4)
  Size            decay (0.3 .. 20 s)
  Density         brightness of the pluck
  Window          body: dry string -> resonant wooden body
  Start           pluck position (near the bridge = thin, middle = round)
  Overlap         second string: detune and stereo width
  Speed           auto-pluck rate when Record is on (encoder; 0.5 .. 16 per second)
  Record          auto-pluck on/off (an internal clock)
  Freeze          sustain: the string rings on (very long decay)
  Source          chord: adds a fifth above
  Blend           output level

Every control arrives as OSC /neb/<name> and goes to the synth argument of the same name (see 02_sc_drift).
*/
~neb = ();
~neb.name = \sc_strike;
~neb.controls = [\speed, \pitch, \start, \size, \density, \overlap, \window, \blend, \freeze, \source, \record];
~neb.def = SynthDef(\sc_strike, { |out = 0, speed = 0.625, pitch = 0.6, start = 0.3, size = 0.4, density = 0.6,
	overlap = 0.2, window = 0.3, blend = 0.6, freeze = 0, source = 0, record = 0, t_reset = 0|
	var freq = (60 + ((pitch - 0.6) * 60)).lag(0.002).midicps;
	var clock = Impulse.kr(speed.linexp(0, 1, 0.5, 16)) * (record > 0.5);
	var trig = Trig1.kr(t_reset + clock, 0.002);
	var decay = Select.kr(freeze > 0.5, [size.linexp(0, 1, 0.3, 20), 120]);
	var coef = density.linlin(0, 1, 0.7, 0.05);
	var burst = WhiteNoise.ar(0.5) * EnvGen.ar(Env.perc(0.0005, 0.01), trig);
	var pos = start.linlin(0, 1, 0.05, 0.5);
	var excite = burst - DelayC.ar(burst, 0.05, pos / freq);
	var detune = 1 + (overlap * 0.006);
	var strings = [freq, freq * detune].collect { |f|
		Pluck.ar(excite, trig, 0.05, 1 / f, decay, coef)
	};
	var fifth = Pluck.ar(excite, trig, 0.05, 1 / (freq * 1.5), decay, coef) * Lag.kr(source > 0.5, 0.05);
	var mix = [strings[0] + (fifth * 0.6), strings[1] + (fifth * 0.6)];
	var width = overlap.linlin(0, 1, 0, 0.8);
	var sig = [mix[0] + (mix[1] * (1 - width)), mix[1] + (mix[0] * (1 - width))] * 0.5;
	var body = sig.collect { |c| BPF.ar(c, [180, 420, 1150, 2400], [0.2, 0.25, 0.3, 0.35], [1.0, 0.7, 0.45, 0.25]).sum };
	sig = (sig * (1 - window)) + (body * window * 2.5);
	sig = LeakDC.ar(sig);
	sig = Limiter.ar(sig * blend.lag(0.05) * 1.5, 0.95);
	Out.ar(out, sig);
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
		"03_sc_strike running".postln;
	});
});
