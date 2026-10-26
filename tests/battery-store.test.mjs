import test from 'node:test';
import assert from 'node:assert/strict';
import {romStorageKey,batteryRead,batteryWrite} from '../web/battery-store.js';
test('mGBA save key is deterministic and separated by ROM bytes',()=>{
  assert.equal(romStorageKey(new Uint8Array([1,2,3])),romStorageKey(new Uint8Array([1,2,3])));
  assert.notEqual(romStorageKey(new Uint8Array([1,2,3])),romStorageKey(new Uint8Array([1,2,4])));
  assert.match(romStorageKey(new Uint8Array([1,2,3])),/^mgba:/);
});
test('no IndexedDB means no game-save network fallback',async()=>{
  assert.equal(await batteryRead('sample'),null);
  assert.equal(await batteryWrite('sample',new Uint8Array([1])),false);
});

test('NES save keys do not collide with existing mGBA keys',()=>{
  const rom=new Uint8Array([1,2,3,4]);
  assert.ok(romStorageKey(rom).startsWith('mgba:'));
  assert.ok(romStorageKey(rom,'jsnes').startsWith('jsnes:'));
  assert.notEqual(romStorageKey(rom),romStorageKey(rom,'jsnes'));
});
