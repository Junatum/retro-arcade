import test from 'node:test';
import assert from 'node:assert/strict';
import { Chip8, FONT, ROM_START, MAX_ROM_BYTES } from '../web/chip8.mjs';
import { DEMO_ROM } from '../web/demo.mjs';
function machine(...ops) {
  const m=new Chip8(()=>0.5);
  m.load(Uint8Array.from(ops.flatMap(op=>[op>>>8,op&255])));
  return m;
}
test('ROM limits and built-in font',()=>{
  const m=new Chip8();
  assert.equal(m.pc,ROM_START);assert.deepEqual(m.memory.slice(0x50,0x55), FONT.slice(0,5));
  assert.throws(()=>m.load(new Uint8Array(0)),/ROM/);
  assert.throws(()=>m.load(new Uint8Array(MAX_ROM_BYTES+1)),/ROM/);
});
test('load, add, skip and jump',()=>{
  const m=machine(0x6005,0x7003,0x3008,0x6000,0x120a,0x6109);
  for(let i=0;i<5;i++)m.step();
  assert.equal(m.v[0],8);assert.equal(m.v[1],9);
});
test('call and return',()=>{
  const m=machine(0x2206,0x600a,0x120a,0x6003,0x00ee);
  m.step(); assert.equal(m.pc,0x206);assert.equal(m.sp,1);
  m.step(); m.step(); assert.equal(m.pc,0x202);assert.equal(m.sp,0);
  m.step();assert.equal(m.v[0],10);
});
test('arithmetic carry, borrow and shift',()=>{
  const m=machine(0x60ff,0x6102,0x8014,0x62ff,0x8015,0x8206,0x820e);
  for(let i=0;i<3;i++)m.step();
  assert.equal(m.v[0],1);assert.equal(m.v[15],1);
  m.step();m.step();assert.equal(m.v[0],255);assert.equal(m.v[15],0);
  m.step();assert.equal(m.v[2],127);assert.equal(m.v[15],1);
  m.step();assert.equal(m.v[2],254);assert.equal(m.v[15],0);
});
test('sprite draw and collision',()=>{
  const m=machine(0x6000,0x6100,0xa050,0xd015,0xd015);
  for(let i=0;i<4;i++)m.step();
  assert.equal(m.pixels[0],1);assert.equal(m.v[15],0);
  m.step();assert.equal(m.pixels[0],0);assert.equal(m.v[15],1);
});
test('key wait and timer decrements',()=>{
  const m=machine(0x6003,0xf015,0xf00a,0x6101);
  for(let i=0;i<3;i++)m.step();
  assert.equal(m.waitingForKey,0);
  m.step();assert.equal(m.pc,0x206);
  m.key(0xa,true);assert.equal(m.waitingForKey,null);assert.equal(m.v[0],0xa);
  m.tick();assert.equal(m.delay,2);
  m.step();assert.equal(m.v[1],1);
});
test('BCD and register store/load',()=>{
  const m=machine(0x607b,0xa300,0xf033,0xf055,0x6000,0xf065);
  for(let i=0;i<3;i++)m.step();
  assert.deepEqual([...m.memory.slice(0x300,0x303)],[1,2,3]);
  m.step();m.step();m.step();assert.equal(m.v[0],123);
});
test('demo draws glyphs without unsupported opcode',()=>{
  const m=new Chip8();m.load(DEMO_ROM);
  for(let i=0;i<50;i++)m.step();
  assert.ok(m.pixels.reduce((a,b)=>a+b,0)>30);
  assert.equal(m.pc,0x224);
});
test('bad unknown opcode fails closed',()=>{
  const m=machine(0x00fd);assert.throws(()=>m.step(),/지원하지/);
});
