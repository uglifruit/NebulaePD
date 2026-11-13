// Run a .csd's orchestra+score in Csound 6.09.1 (emscripten build) under Node, like the Nebulae does:
// compileOrc (result checked here, unlike nebulae.py), readScore, start, performKsmps.
// usage: node tools/run_csound609.js file.csd seconds [out.wav]   (out.wav: stereo 32-bit float render)
//        CS609_FILES=a.wav,b.wav node ...   preloads audio files the orchestra reads (no live input in wasm)
// Needs csound-emscripten-6.09.1.zip (GitHub release 6.09.1) unzipped into tools/csound609/ (gitignored),
// or CS609_DIR pointing at the unzipped csound-emscripten-6.09.1 folder.
const fs = require('fs');
const path = require('path');
const BASE = process.env.CS609_DIR || path.join(__dirname, 'csound609', 'csound-emscripten-6.09.1');
const lib = path.join(BASE, 'javascripts', 'libcsound.js');
global.require = require; global.__dirname = path.join(BASE,'javascripts'); global.Module = { memoryInitializerPrefixURL: BASE + '/', print: s => console.log(s), printErr: s => console.log(s) };
// CS609_MEM=256: heap size in MB (the build's default is small; big tables need more)
if (process.env.CS609_MEM) global.Module.TOTAL_MEMORY = parseInt(process.env.CS609_MEM, 10) * 1024 * 1024;
const src = fs.readFileSync(lib, 'utf8');
// eval in this scope so Module/cwrap end up global
(0, eval)(src);
const M = global.Module;
const cw = M.cwrap || global.cwrap;
function go() {
  const csd = fs.readFileSync(process.argv[2], 'utf8');
  const secs = parseFloat(process.argv[3] || '5');
  const orc = csd.split('<CsInstruments>')[1].split('</CsInstruments>')[0];
  const sco = csd.split('<CsScore>')[1].split('</CsScore>')[0];
  const _new = cw('CsoundObj_new', 'number', []);
  const _compileOrc = cw('CsoundObj_compileOrc', 'number', ['number', 'string']);
  const _readScore = cw('CsoundObj_readScore', 'number', ['number', 'string']);
  const _prepareRT = cw('CsoundObj_prepareRT', null, ['number']);
  const _performKsmps = cw('CsoundObj_performKsmps', 'number', ['number']);
  const _getKsmps = cw('CsoundObj_getKsmps', 'number', ['number']);
  const _getOut = cw('CsoundObj_getOutputBuffer', 'number', ['number']);
  const cs = _new();
  // CS609_FILES="a.wav,b.wav": copied into the wasm file system (by base name) for GEN01 / filelen etc.
  for (const f of (process.env.CS609_FILES || '').split(',').filter(Boolean)) {
    M.FS_createDataFile('/', path.basename(f), new Uint8Array(fs.readFileSync(f)), true, true);
  }
  const r = _compileOrc(cs, orc);
  console.log('### compileOrc returned', r);
  _readScore(cs, sco);
  _prepareRT(cs);
  const ksmps = _getKsmps(cs);
  const kcycles = Math.round(secs * 48000 / ksmps);
  let peak = 0, nan = 0, ret = 0, k = 0;
  const wavPath = process.argv[4], rec = wavPath ? new Float32Array(kcycles * ksmps * 2) : null;
  for (; k < kcycles; k++) {
    ret = _performKsmps(cs);
    const p = _getOut(cs) / 4; // MYFLT=float in this build
    for (let i = 0; i < ksmps * 2; i++) {
      const v = M.HEAPF32[p + i];
      if (rec) rec[k * ksmps * 2 + i] = v;
      if (Number.isNaN(v)) nan++; else if (Math.abs(v) > peak) peak = Math.abs(v);
    }
    if (ret !== 0) break;
  }
  if (rec) writeWav(wavPath, rec.subarray(0, k * ksmps * 2), 48000);
  console.log(`### ksmps=${ksmps} kcycles_run=${k} last_ret=${ret} peak=${peak} nan_samples=${nan}`);
}
function writeWav(file, data, sr) {
  const b = Buffer.alloc(44 + data.length * 4);
  b.write('RIFF', 0); b.writeUInt32LE(36 + data.length * 4, 4); b.write('WAVEfmt ', 8);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(3, 20); b.writeUInt16LE(2, 22); b.writeUInt32LE(sr, 24);
  b.writeUInt32LE(sr * 8, 28); b.writeUInt16LE(8, 32); b.writeUInt16LE(32, 34);
  b.write('data', 36); b.writeUInt32LE(data.length * 4, 40);
  for (let i = 0; i < data.length; i++) b.writeFloatLE(data[i], 44 + i * 4);
  fs.writeFileSync(file, b);
}
if (M.calledRun) go(); else M.onRuntimeInitialized = go;
