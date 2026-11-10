// SuperCollider probe, stage 1: an offline (NRT) render, no audio device. See sc/probe/run.sh.
// 2 s, 48 kHz stereo: 440 Hz sine on the left, white noise through DFM1 (sc3-plugins) or LPF on the right.
(
var path = "/tmp/sc_probe/out/probe_nrt.wav";
var dfm = \DFM1.asClass;
var def, score, opts;
SystemClock.sched(150, { "SCPROBE: NRT timeout".postln; 1.exit; nil });
("SCPROBE: sclang " ++ Main.version ++ ", sc3-plugins classes: " ++ dfm.notNil).postln;
def = SynthDef(\probe, {
	var env = EnvGen.kr(Env.linen(0.01, 1.8, 0.1), doneAction: 2);
	var left = SinOsc.ar(440, 0, 0.3);
	var noise = WhiteNoise.ar(0.3);
	var right = if(dfm.notNil, { dfm.ar(noise, 1000, 0.5) }, { LPF.ar(noise, 1000) });
	Out.ar(0, [left, right] * env);
});
score = Score([
	[0.0, ['/d_recv', def.asBytes]],
	[0.0, [\s_new, \probe, 1000, 0, 0]],
	[2.0, [\c_set, 0, 0]]
]);
opts = ServerOptions.new;
opts.numOutputBusChannels = 2;
opts.numInputBusChannels = 0;
opts.ugenPluginsPath = "/tmp/sc/plugins";
score.recordNRT(
	outputFilePath: path, sampleRate: 48000, headerFormat: "WAV", sampleFormat: "int16",
	options: opts, duration: 2,
	action: { ("SCPROBE: NRT done, file " ++ File.exists(path)).postln; 0.exit }
);
)
