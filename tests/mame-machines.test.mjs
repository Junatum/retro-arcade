import test from 'node:test';
import assert from 'node:assert/strict';
import { ARCADE_MACHINES, arcadeMachine } from '../web/mame/machines.js';
import { SYSTEMS, validateRom } from '../web/systems.js';
const oldWindow=globalThis.window, oldLocation=globalThis.location;
globalThis.location={origin:'http://router.local'};
globalThis.window={parent:{postMessage() {}},addEventListener() {}};
const {driverName,makeConfiguration,installRom}=await import('../web/mame/runner.js');
globalThis.window=oldWindow;globalThis.location=oldLocation;

test('Arcade allowlist uses only names registered in the bundled MAME 0.289', () => {
  assert.equal(ARCADE_MACHINES.length, 454);
  assert.equal(new Set(ARCADE_MACHINES).size, ARCADE_MACHINES.length);
  for (const name of ['pacman','galaxian','mooncrst','mspacman','puckman','tst_galx']) {
    assert.equal(arcadeMachine(name.toUpperCase() + '.ZIP'), name);
    assert.equal(driverName(name + '.zip'), name);
    assert.equal(validateRom({name:name + '.zip',size:64},SYSTEMS.at(-1)),null);
  }
});

test('MAME rejects unsupported, malformed and traversal-prone names before startup', () => {
  for (const bad of ['tetris.zip','unknown.zip','/tmp/pacman.zip','../pacman.zip',
    'pacman.zip/../malicious.zip','foo\\pacman.zip','.zip','pacman.exe','páčman.zip',
    'pacman.zip?download=1', 'pacman.zip/']) {
    assert.equal(arcadeMachine(bad),null,bad);
    assert.notEqual(validateRom({name:bad,size:64},SYSTEMS.at(-1)),null,bad);
    assert.throws(()=>makeConfiguration(bad,new Uint8Array([80,75,3,4,...new Uint8Array(26)]),{},()=>{},()=>{}),/허용되지 않은/,bad);
  }
  assert.match(validateRom({name:'mooncrst.zip',size:13*1024*1024},SYSTEMS.at(-1)),/12MiB/);
});

test('new built-in machine IDs map to local paths without remote access',()=>{
  const bytes = Uint8Array.from([80,75,3,4,...new Uint8Array(26)]);
  const calls=[];
  const module={FS_createPath:(...args)=>calls.push(args),FS_createDataFile:(...args)=>calls.push(args)};
  installRom(module,'mooncrst',bytes);
  assert.deepEqual(calls[0],['/','roms',true,true]);
  assert.deepEqual(calls[1].slice(0,3),['/roms','mooncrst.zip',bytes]);
  const config=makeConfiguration('MOONCRST.ZIP',bytes,{},()=>{},()=>{});
  assert.deepEqual(config.arguments.slice(0,3),['mooncrst','-rompath','/roms']);
});
