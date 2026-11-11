/*
04_sc_cloud: granular clouds from the audio input. A 4-second buffer records the input all the time (stereo summed
to mono); grains read it back, pitched and scattered.

  Audio in        the source (patch something in)
  Start           how far back the grains read (0 = just recorded .. 1 = 4 s ago)
  Size            grain length (20 .. 500 ms)
  Density         grains per second (1 .. 80); fully clockwise = denser random grains
  Window          position scatter (grains spread around Start)
  Pitch + V/oct   grain pitch, 1 V/oct (click = original pitch)
  Overlap         stereo spread of the grains
  Speed           pitch scatter (encoder; 0.625 = none, either way = more random detune)
  Blend           dry/wet
  Freeze          stop recording: the buffer holds what it has
  Reset           a burst of grains (button or gate)
  Source          reverse: grains play backwards

Every control arrives as OSC /neb/<name> and goes to the synth argument of the same name (see 02_sc_drift).
*/
~neb = ();
~neb.name = \sc_cloud;
~neb.controls = [\speed, \pitch, \start, \size, \density, \overlap, \window, \blend, \freeze, \source];
~neb.def = SynthDef(\sc_cloud, { |out = 0, speed = 0.625, pitch = 0.6, start = 0.1, size = 0.3, density = 0.4,
	overlap = 0.5, window = 0.2, blend = 0.6, freeze = 0, source = 0, t_reset = 0|
	var frames = 48000 * 4;
	var buf = LocalBuf(frames, 1).clear;
	var in = SoundIn.ar([0, 1]);
	var mono = in.sum * 0.5;
	var writing = 1 - (freeze > 0.5);
	var phase = Phasor.ar(0, writing, 0, frames);
	var rate = density.linexp(0, 1, 1, 80);
	var burst = EnvGen.kr(Env([0, 1, 0], [0.001, 0.4], [0, -3]), t_reset);
	var trig = Impulse.ar(rate * (density < 0.9)) + Dust.ar(rate * (density >= 0.9)) + Dust.ar(burst * 120);
	var dur = size.linexp(0, 1, 0.02, 0.5);
	var scatter = (speed - 0.625).abs * 2;
	var transpose = 2 ** (((pitch - 0.6) * 5) + (TRand.ar(-1, 1, trig) * scatter));
	var dir = Select.kr(source > 0.5, [1, -1]);
	var back = start * 0.95 + (TRand.ar(0, window * 0.5, trig)) + (dur * transpose.max(1) / 4);
	var pos = ((phase / frames) - back).wrap(0, 1);
	var pan = TRand.ar(overlap.neg, overlap, trig);
	var grains = GrainBuf.ar(2, trig, dur, buf, transpose * dir, pos, 2, pan, -1, 128);
	var wet = blend.lag(0.05);
	var sig;
	BufWr.ar(mono, buf, phase);
	sig = (in * (1 - wet)) + (LeakDC.ar(grains) * wet * 1.2);
	Out.ar(out, Limiter.ar(sig, 0.95));
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
		"04_sc_cloud running".postln;
	});
});
