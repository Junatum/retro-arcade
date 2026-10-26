import test from 'node:test';
import assert from 'node:assert/strict';
import { SYSTEMS,detectSystem,validateRom } from '../web/systems.js';

test('CHIP-8 and one mGBA engine provide GB/GBC/GBA platforms',()=>{
  assert.deepEqual(SYSTEMS.map(s=>s.id),['chip8','mgba-gb','mgba','nes']);
  assert.equal(detectSystem('puzzle.CH8'),SYSTEMS[0]);
  assert.equal(detectSystem('game.gb'),SYSTEMS[1]);
  assert.equal(detectSystem('game.GBC'),SYSTEMS[1]);
  assert.equal(detectSystem('Advance.GBA'),SYSTEMS[2]);
  assert.equal(detectSystem('unknown.nes'),SYSTEMS[3]);
});
test('ROM validation prevents wrong types and oversized files',()=>{
  const ch8=SYSTEMS[0],gb=SYSTEMS[1],gba=SYSTEMS[2];
  assert.equal(validateRom({name:'tiny.c8',size:8},ch8),null);
  assert.match(validateRom({name:'a.nes',size:8},ch8),/ch8/);
  assert.match(validateRom({name:'a.ch8',size:3585},ch8),/3,584/);
  assert.equal(validateRom({name:'gbc.gbc',size:32768},gb),null);
  assert.equal(validateRom({name:'gb.gb',size:8192},gb),null);
  assert.match(validateRom({name:'short.gb',size:16},gb),/너무 작/);
  assert.match(validateRom({name:'a.gbc',size:8*1024*1024+1},gb),/8MiB/);
  assert.match(validateRom({name:'a.ch8',size:2048},gb),/\.gb/);
  assert.match(validateRom(null,gb),/선택/);
  assert.equal(validateRom({name:'game.gba',size:1024},gba),null);
  assert.match(validateRom({name:'tiny.gba',size:50},gba),/너무 작/);
  assert.match(validateRom({name:'big.gba',size:32*1024*1024+1},gba),/32MiB/);
  assert.match(validateRom({name:'game.gb',size:1024},gba),/\.gba/);
});
test('NES/Famicom is the fourth platform and validates size',()=>{
  const nes=SYSTEMS.find(s=>s.id==='nes');
  assert.ok(nes);
  assert.equal(detectSystem('Mario.NES'),nes);
  assert.equal(validateRom({name:'game.nes',size:32768},nes),null);
  assert.match(validateRom({name:'short.nes',size:100},nes),/너무 작/);
  assert.match(validateRom({name:'huge.nes',size:8*1024*1024+1},nes),/8MiB/);
});
