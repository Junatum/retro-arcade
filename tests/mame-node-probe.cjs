'use strict';
// Run the shipped MAME/Emscripten program with its real WASM (not a stub).
// The selected -listfull command needs no game ROM, graphics or audio.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const base = path.resolve(__dirname, '../web/mame');

// The MAME JS bundle references window for its optional audio adapters even
// in Node. Provide only the global alias; the native Node loading path and
// actual WebAssembly executable remain in use.
globalThis.window = globalThis;
globalThis.require = require;
globalThis.__dirname = base;

let booted = false;
let mounted = false;
let pacman = false;
let galaxian = false;
let completed = false;
const fail = (message) => {
  if (completed) return;
  completed = true;
  console.error('FAIL MAME runtime:', String(message).slice(0, 500));
  process.exitCode = 1;
  clearTimeout(watchdog);
};
const pass = () => {
  if (completed || !booted || !mounted || !pacman || !galaxian) return;
  completed = true;
  clearTimeout(watchdog);
  console.log('PASS: real MAME JS/WASM, memory FS and selected driver listing (no game ROM)');
};
const watchdog = setTimeout(() => fail('timed out before native -listfull output'), 15000);
process.on('unhandledRejection', reason => fail(reason?.message || reason));
process.on('uncaughtException', reason => fail(reason?.message || reason));

globalThis.Module = {
  arguments: ['-listfull'],
  locateFile: name => path.join(base, name.endsWith('.wasm') ? 'mame.wasm' : name),
  preRun: [() => {
    const m = globalThis.Module;
    if (typeof m.FS_createPath !== 'function' || typeof m.FS_createDataFile !== 'function') {
      fail('missing actual MAME memory filesystem exports');
      return;
    }
    m.FS_createPath('/', 'roms', true, true);
    // Original diagnostic bytes only; -listfull never attempts to play them.
    m.FS_createDataFile('/roms', 'ci-fixture.zip',
      Uint8Array.from([80, 75, 3, 4, 0, 0, 0, 0]), true, false, true);
    mounted = true;
  }],
  onRuntimeInitialized: () => { booted = true; pass(); },
  onAbort: reason => fail(reason),
  print: line => {
    const text = String(line);
    if (/\bpacman\b/i.test(text)) pacman = true;
    if (/\bgalaxian\b/i.test(text)) galaxian = true;
    pass();
  },
  printErr: line => { if (/^Aborted\(/.test(String(line))) fail(line); },
};
vm.runInThisContext(fs.readFileSync(path.join(base, 'mame.js'), 'utf8'),
  { filename: path.join(base, 'mame.js') });
