// Run a .csd's orchestra+score in Csound 6.09.1 (emscripten build) under Node, like the Nebulae does:
// compileOrc (result checked here, unlike nebulae.py), readScore, start, performKsmps.
// usage: node tools/run_csound609.js file.csd seconds
// Needs csound-emscripten-6.09.1.zip (GitHub release 6.09.1) unzipped into tools/csound609/ (gitignored),
// or CS609_DIR pointing at the unzipped csound-emscripten-6.09.1 folder.
const fs = require('fs');
const path = require('path');
const BASE = process.env.CS609_DIR || path.join(__dirname, 'csound609', 'csound-emscripten-6.09.1');
const lib = path.join(BASE, 'javascripts', 'libcsound.js');
global.require = require; global.__dirname = path.join(BASE,'javascripts'); global.Module = { memoryInitializerPrefixURL: BASE + '/', print: s => console.log(s), printErr: s => console.log(s) };
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
  const r = _compileOrc(cs, orc);
  console.log('### compileOrc returned', r);
  _readScore(cs, sco);
  _prepareRT(cs);
  const ksmps = _getKsmps(cs);
  const kcycles = Math.round(secs * 48000 / ksmps);
  let peak = 0, nan = 0, ret = 0, k = 0;
  for (; k < kcycles; k++) {
    ret = _performKsmps(cs);
    const p = _getOut(cs) / 4; // MYFLT=float in this build
    for (let i = 0; i < ksmps * 2; i++) {
      const v = M.HEAPF32[p + i];
      if (Number.isNaN(v)) nan++; else if (Math.abs(v) > peak) peak = Math.abs(v);
    }
    if (ret !== 0) break;
  }
  console.log(`### ksmps=${ksmps} kcycles_run=${k} last_ret=${ret} peak=${peak} nan_samples=${nan}`);
}
if (M.calledRun) go(); else M.onRuntimeInitialized = go;
