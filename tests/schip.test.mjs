import test from 'node:test';
import assert from 'node:assert/strict';
import {Chip8, DISPLAY_WIDTH, DISPLAY_HEIGHT, SCHIP_WIDTH, SCHIP_HEIGHT, LARGE_FONT, ROM_START} from '../web/chip8.js';
import {SYSTEMS, detectSystem, validateRom} from '../web/systems.js';

function machine(...ops) {
  const vm = new Chip8(() => 0.5);
  vm.load(Uint8Array.from(ops.flatMap(op => [op >> 8, op & 255])));
  return vm;
}

function steps(vm, n) { for (let i=0;i<n;i++) vm.step(); }
const pixel = (vm,x,y) => vm.pixels[y*vm.width+x];

test('one CHIP-8 platform accepts both classic and SCHIP ROM extensions', () => {
  assert.equal(SYSTEMS.filter(s=>s.id==='chip8').length, 1);
  assert.equal(SYSTEMS.some(s=>s.id==='schip'), false);
  for (const name of ['classic.ch8', 'classic.c8', 'hires.SC8', 'hires.sch8']) {
    assert.equal(detectSystem(name), SYSTEMS[0]);
    assert.equal(validateRom({name,size:512},SYSTEMS[0]), null);
  }
  assert.match(validateRom({name:'oversize.sc8',size:3585},SYSTEMS[0]),/3,584/);
});

test('CHIP-8 starts in classic mode without changing quirks and switches when SCHIP opcodes execute', () => {
  const vm=machine(0x60aa,0x61bb,0x6f07,0x8011,0x00ff,0x6f07,0x8011,0x00fe);
  assert.equal(vm.superchip, false);
  assert.deepEqual([vm.width,vm.height],[DISPLAY_WIDTH,DISPLAY_HEIGHT]);
  steps(vm,4);
  assert.equal(vm.v[15],0,'existing CHIP-8 OR clears VF');
  vm.step();
  assert.equal(vm.superchip,true);
  assert.deepEqual([vm.width,vm.height],[SCHIP_WIDTH,SCHIP_HEIGHT]);
  steps(vm,3);
  assert.equal(vm.v[15],7,'SCHIP OR retains VF');
  assert.deepEqual([vm.width,vm.height],[DISPLAY_WIDTH,DISPLAY_HEIGHT]);
  vm.load(Uint8Array.of(0x60,0x01));
  assert.equal(vm.superchip,false,'loading a new classic ROM does not retain SCHIP quirks');
});

test('explicit SCHIP mode supports 00FF/00FE, screen clears, and 00FD halts', () => {
  const vm=new Chip8(Math.random,{superchip:true});
  vm.load(Uint8Array.of(0x00,0xff,0x00,0xfe,0x00,0xfd));
  assert.equal(vm.superchip,true);
  vm.pixels[0]=1;vm.step();
  assert.equal(vm.pixels.length,128*64);
  assert.equal(vm.pixels[0],0);
  vm.pixels[0]=1;vm.step();
  assert.equal(vm.pixels.length,64*32);
  assert.equal(vm.pixels[0],0);
  vm.step();assert.equal(vm.halted,true);
  const pc=vm.pc;vm.step();assert.equal(vm.pc,pc);
});

test('SCHIP screen scroll clips at borders in both axes without wrapping', () => {
  const vm=machine(0x00ff,0x00fb,0x00fc,0x00c3);
  vm.step();
  vm.pixels[3]=1;vm.pixels[127]=1;
  vm.step();
  assert.equal(pixel(vm,7,0),1);
  assert.equal(pixel(vm,127,0),0);
  vm.step();
  assert.equal(pixel(vm,3,0),1);
  assert.equal(pixel(vm,123,0),0);
  vm.step();
  assert.equal(pixel(vm,3,3),1);
  assert.equal(pixel(vm,3,0),0);
  assert.equal(vm.changed,true);
});

test('00Cn/00FB scrolling uses modern SCHIP logical pixels even at low resolution', () => {
  const vm=machine(0x00fb,0x00c1,0x00fc);
  vm.pixels[0]=1;
  vm.step();assert.equal(pixel(vm,4,0),1);
  vm.step();assert.equal(pixel(vm,4,1),1);
  vm.step();assert.equal(pixel(vm,0,1),1);
  assert.equal(vm.superchip,true);
});

test('SCHIP DXY0 draws and collides 16x16 using 32 bytes, clips at edges', () => {
  const vm=machine(0x00ff,0xd010,0xd010);
  vm.step();vm.i=0x300;vm.v[0]=127;vm.v[1]=63;
  vm.memory.fill(255,0x300,0x320);
  vm.step();assert.equal(pixel(vm,127,63),1);assert.equal(vm.v[15],0);
  assert.equal(vm.pixels.reduce((a,b)=>a+b,0),1);
  vm.step();assert.equal(pixel(vm,127,63),0);assert.equal(vm.v[15],1);
  const broken=machine(0x00ff,0xd010);broken.step();broken.i=0xfe1;
  assert.throws(()=>broken.step(),/스프라이트 주소 오류/);
});

test('SCHIP large font points at a 10-byte glyph and RPL flags remain local', () => {
  const vm=machine(0x6009,0xf030,0xf075,0x6000,0xf085);
  steps(vm,2);
  assert.deepEqual([...vm.memory.slice(vm.i,vm.i+10)],[...LARGE_FONT.slice(90,100)]);
  steps(vm,3);assert.equal(vm.v[0],9);
  assert.equal(vm.rpl[0],9);
  vm.load(Uint8Array.of(0x00,0xff));
  assert.equal(vm.rpl[0],0);
});

test('RPL flags bound and CHIP-8 legacy memory invariants', () => {
  const vm=machine(0xf875);assert.throws(()=>vm.step(),/RPL 플래그 범위/);
  const classic=machine(0x6005,0xa300,0xf055,0x6000,0xf065);
  steps(classic,5);
  assert.equal(classic.v[0],5);assert.equal(classic.i,0x300);
  assert.equal(classic.superchip,false);
});

test('SCHIP can auto-enable large font without changing the public platform', () => {
  const vm=machine(0x6002,0xf030,0x00fd);
  steps(vm,2);
  assert.equal(vm.superchip,true);
  assert.equal(vm.i,0xa0+20);
  assert.equal(vm.memory[vm.i],LARGE_FONT[20]);
  assert.equal(vm.pc,ROM_START+4);
});
