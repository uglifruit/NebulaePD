/*
08_sc_space: a big stereo space. Diffuse delays (Greyhole, sc3-plugins) feed a long reverb (JPverb), with freeze,
ducking and a tail clear. Built 2026-11-14 while the owner was away (decisions to review in docs/SC_SPACE.md). MIT.

  Blend           dry <-> space (equal power)
  Start           delay time 20 ms .. 1.4 s (the diffuse echoes)
  Overlap         delay feedback (0 .. 100 %)
  Density         diffusion: anticlockwise = distinct echoes, clockwise = a smeared wash
  Size            room size (both engines)
  Window          reverb decay 0.3 .. 60 s
  Pitch           tone: the click = neutral, clockwise brighter, anticlockwise darker
  Speed           movement: between the clicks gentle, towards the ends deeper, faster modulation (chorus, warble)
  Freeze          hold the space (the input stops going in; the tails ring on). File held = momentary freeze
  Record          duck: the space dips while you play, and swells in the gaps
  Source          shimmer: an octave up goes round the reverb
  Reset           clear: the tails drain away in a moment
  alt (hold Source): Start = delays <-> reverb balance, Size = stereo width, Density = duck depth,
    Window = duck release, Overlap = bass decay, Blend = shimmer amount
*/
~neb = ();
~neb.name = \sc_space;
~neb.controls = [\speed, \pitch, \start, \size, \density, \overlap, \window, \blend, \freeze, \source, \record,
	\start_alt, \size_alt, \density_alt, \window_alt, \overlap_alt, \blend_alt];
~neb.def = SynthDef(\sc_space, { |out = 0, speed = 0.5, pitch = 0.6, start = 0.5, size = 0.5, density = 0.6,
	overlap = 0.4, window = 0.5, blend = 0.5, freeze = 0, source = 0, record = 0, filehold = 0, t_reset = 0,
	start_alt = 0.5, size_alt = 1, density_alt = 0.7, window_alt = 0.4, overlap_alt = 0.5, blend_alt = 0.4|
	var dry = SoundIn.ar([0, 1]);
	var frz = (freeze + filehold > 0.5).lag(0.05);
	var open = 1 - frz;
	// Reset: shut the input and drain the tails (decay and feedback down), then back after 0.7 s
	var clr = EnvGen.kr(Env([1, 0, 0, 1], [0.03, 0.4, 0.3]), t_reset);
	var damp = (0.3 - ((pitch - 0.6) * 1.5)).clip(0, 0.95).lag(0.05);
	var mv = ((speed - 0.5).abs * 2).lag(0.1);                       // 0 between the clicks .. 1 at the ends
	var md = mv.linlin(0, 1, 0.05, 0.9);
	var mf = mv.linexp(0, 1, 0.5, 6);
	var sz = size.linexp(0, 1, 0.5, 5).lag(0.2);
	// JPverb rings about 1.4x its t60 argument (measured: tools/sc_space_tests.py decay)
	var t60 = (window.linexp(0, 1, 0.3, 60) / 1.4).lag(0.1);
	var bal = start_alt.lag(0.05);
	var send = dry * open * clr;
	var gh, sh, jin, jp, wet, fzon, held, env, duck, w, b;
	// Greyhole's echoes come about delayTime + 0.065 s x size apart, and its delay tops out near 1.43 s
	gh = Greyhole.ar(send, start.linexp(0, 1, 0.02, 1.4).lag(0.3), damp, sz,
		density.linlin(0, 1, 0, 0.99), (overlap * open + frz) * clr, md, mf);
	// shimmer: an octave up of the space goes back round (into the reverb's input)
	sh = PitchShift.ar(LocalIn.ar(2), 0.2, 2, 0, 0.01) * (source > 0.5).lag(0.1) * blend_alt * 0.5;
	jin = (send + (gh * (1 - bal)) + sh) * open * clr;              // frozen: nothing new goes into the reverb
	jp = JPverb.ar(jin, Select.kr(frz > 0.5, [t60, 1000]) * clr.max(0.01), damp * open, sz, 0.707, md, mf,
		overlap_alt.linexp(0, 1, 0.5, 2), 1, 1, 500, 2000);
	LocalOut.ar(jp);
	wet = (gh * (1 - bal)) + (jp * bal);
	// Freeze: JPverb's decay tops out at 60 s (about -1 dB/s), so what you hear while frozen is a spectral freeze
	// of the space (PV_MagFreeze), which holds for ever; the reverb rings on underneath and takes over on release.
	// A clear (Reset) lets go of the snapshot too, so it re-freezes on the drained (silent) space.
	fzon = (freeze + filehold > 0.5) * (clr > 0.99);
	held = wet.collect { |ch| IFFT(PV_MagFreeze(FFT(LocalBuf(2048), ch), fzon)) };
	wet = (wet * (1 - frz)) + (held * frz);
	// width (alt Size): mid/side
	w = size_alt.lag(0.1);
	wet = [(wet[0] + wet[1]) * 0.5 + ((wet[0] - wet[1]) * 0.5 * w), (wet[0] + wet[1]) * 0.5 - ((wet[0] - wet[1]) * 0.5 * w)];
	// duck (Record): the space dips under the dry signal
	env = Amplitude.kr(Mix(dry) * 0.5, 0.01, window_alt.linexp(0, 1, 0.05, 2));
	duck = 1 - ((record > 0.5).lag(0.05) * density_alt * 0.97 * (env * 8).clip(0, 1));    // at most -30 dB
	wet = LeakDC.ar(wet) * duck.lag(0.02) * clr.lag(0.01);
	b = blend.lag(0.05);
	Out.ar(out, Limiter.ar((dry * cos(b * 0.5pi)) + (wet * sin(b * 0.5pi)), 0.95));
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
		OSCdef(\neb_filestate, { |msg| ~nebSynth.set(\filehold, msg[1]) }, '/neb/filestate', recvPort: 3000);
		"08_sc_space running".postln;
	});
});
