import test from 'node:test';
import assert from 'node:assert/strict';
import { SYSTEMS,detectSystem,validateRom } from '../web/systems.mjs';

test('only actually shipped platform is advertised',()=>{
  assert.deepEqual(SYSTEMS.map(s=>s.id),['chip8']);
  assert.equal(detectSystem('puzzle.CH8'),SYSTEMS[0]);
  assert.equal(detectSystem('unknown.nes'),null);
  assert.equal(detectSystem('game.gb'),null);
});
test('ROM validation prevents wrong types and oversize',()=>{
  const s=SYSTEMS[0];
  assert.equal(validateRom({name:'tiny.c8',size:8},s),null);
  assert.match(validateRom({name:'a.nes',size:8},s),/ch8/);
  assert.match(validateRom({name:'a.ch8',size:3585},s),/3,584/);
  assert.match(validateRom(null,s),/선택/);
});
