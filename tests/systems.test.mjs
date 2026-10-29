import test from 'node:test';
import assert from 'node:assert/strict';
import { SYSTEMS,detectSystem,validateRom } from '../web/systems.js';

test('CHIP-8 and one mGBA engine provide GB/GBC/GBA platforms',()=>{
  assert.deepEqual(SYSTEMS.map(s=>s.id),['chip8','mgba-gb','mgba','nes','gearsystem-gg','gearsystem-sms','gearsystem-sg','blastem','mame']);
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

test('Gearsystem and BlastEm cartridge limits and mappings',()=>{
  const gg=SYSTEMS.find(s=>s.id==='gearsystem-gg');
  const sms=SYSTEMS.find(s=>s.id==='gearsystem-sms');
  const sg=SYSTEMS.find(s=>s.id==='gearsystem-sg');
  const md=SYSTEMS.find(s=>s.id==='blastem');
  assert.equal(detectSystem('game.gg'),gg);
  assert.equal(detectSystem('game.sms'),sms);
  assert.equal(detectSystem('game.sg'),sg);
  assert.equal(detectSystem('game.MD'),md);
  assert.equal(detectSystem('game.gen'),md);
  assert.equal(detectSystem('game.bin'),md);
  assert.equal(validateRom({name:'game.gg',size:32768},gg),null);
  assert.equal(validateRom({name:'game.sms',size:131072},sms),null);
  assert.equal(validateRom({name:'game.sg',size:4096},sg),null);
  assert.equal(validateRom({name:'game.md',size:2*1024*1024},md),null);
  assert.match(validateRom({name:'game.md',size:9*1024*1024},md),/8MiB/);
  assert.match(validateRom({name:'tiny.gg',size:20},gg),/너무 작/);
  assert.match(validateRom({name:'wrong.gg',size:256},md),/\.md/);
});

test('MAME 0.289 accepts compiled machine identifiers, without public ROM metadata',()=>{
  const arcade=SYSTEMS.find(s=>s.id==='mame');
  assert.equal(detectSystem('pacman.zip'),arcade);
  assert.equal(validateRom({name:'pacman.zip',size:6000},arcade),null);
  assert.equal(validateRom({name:'GALAXIAN.ZIP',size:20000},arcade),null);
  assert.equal(validateRom({name:'mooncrst.zip',size:8000},arcade),null);
  assert.equal(validateRom({name:'mspacman.zip',size:8000},arcade),null);
  assert.match(validateRom({name:'tetris.zip',size:10000},arcade),/지원하지 않는/);
  assert.match(validateRom({name:'pacman.zip',size:20},arcade),/ZIP/);
  assert.match(validateRom({name:'pacman.zip',size:13*1024*1024},arcade),/12MiB/);
  assert.match(validateRom({name:'pacman.nes',size:20000},arcade),/지원하지 않는/);
});
