import test from 'node:test';
import assert from 'node:assert/strict';

test('MAME runner uses the compiled machine allowlist without remote ROM fetch',async()=>{
  const oldWindow=globalThis.window, oldLocation=globalThis.location;
  const subscriptions=[];
  globalThis.location={origin:'http://router.local'};
  globalThis.window={parent:{postMessage(){}},addEventListener:(...args)=>subscriptions.push(args)};
  try {
    const {driverName,makeConfiguration}=await import('../web/mame/runner.js');
    assert.equal(driverName('pacman.zip'),'pacman');
    assert.equal(driverName('GALAXIAN.ZIP'),'galaxian');
    assert.equal(driverName('tetris.zip'),null);
    assert.equal(driverName('../pacman.zip'),null);
    assert.throws(()=>makeConfiguration('tetris.zip',new Uint8Array(30),{},()=>{},()=>{}),/허용되지 않은/);
    const mod=makeConfiguration('pacman.zip',Uint8Array.from([0x50,0x4b,3,4,...new Uint8Array(36)]),{},()=>{},()=>{});
    assert.deepEqual(mod.arguments.slice(0,3),['pacman','-rompath','/roms']);
    assert.match(mod.locateFile('mame_ssharcade.wasm'),/\/mame\/mame.wasm$/);
    assert.equal(subscriptions.length,1);
  } finally {globalThis.window=oldWindow;globalThis.location=oldLocation;}
});
