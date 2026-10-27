import test from 'node:test';
import assert from 'node:assert/strict';
import { Chip8, FONT, ROM_START, MAX_ROM_BYTES } from '../web/chip8.js';
import { DEMO_ROM, DEMO_TITLE, DEMO_CONTROLS, DEMO_FINISHED_PC, DEMO_WIN_SCORE, DEMO_SERVE_DELAY_TICKS } from '../web/demo.js';
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
test('original Paddle Rally CHIP-8 demo is playable and stays within ROM limits',()=>{
  assert.equal(DEMO_TITLE, '패들 랠리');
  assert.match(DEMO_CONTROLS,/W \/ S/);
  assert.ok(DEMO_ROM.length > 100 && DEMO_ROM.length < MAX_ROM_BYTES);
  const m=new Chip8();m.load(DEMO_ROM);
  for(let i=0;i<1200;i++)m.step();
  assert.ok(m.pixels.reduce((a,b)=>a+b,0)>15);
  assert.ok(m.v[4]>=5 && m.v[4]<=57, 'ball must remain inside the field');
  assert.ok(m.v[8]<=9 && m.v[9]<=9, 'both scores are single digits');
});
test('Paddle Rally renders the computer at left, player at right and scores on the correct sides',()=>{
  const m=new Chip8();m.load(DEMO_ROM);
  // Let the boot cycle complete a full sprite draw, then verify both paddles.
  let paddlesReady=false;
  for(let i=0;i<200;i++){
    m.step();
    if(m.pixels[(m.v[3])*64+3] && m.pixels[(m.v[2])*64+58]){
      paddlesReady=true;break;
    }
  }
  assert.ok(paddlesReady, 'left computer paddle uses v3, right player paddle uses v2');
  // The left scoreboard uses v9 (computer), the right uses v8 (player).
  assert.equal(m.v[8],0);assert.equal(m.v[9],0);
});
test('Paddle Rally credits the right-side player when left computer misses, and vice versa',()=>{
  const instructionAddress = target => {
    for (let i=0;i<DEMO_ROM.length-1;i+=2) {
      if ((DEMO_ROM[i]<<8 | DEMO_ROM[i+1]) === target) return ROM_START+i;
    }
    throw new Error(`missing CHIP-8 collision instruction ${target.toString(16)}`);
  };
  const simulate = ({address,x,y,playerY,computerY}) => {
    const m=new Chip8();m.load(DEMO_ROM);
    m.v[2]=playerY;m.v[3]=computerY;m.v[4]=x;m.v[5]=y;
    m.pc=instructionAddress(address);
    for (let i=0;i<17;i++)m.step();
    return m;
  };
  const leftMiss=simulate({address:0x3405,x:5,y:20,playerY:14,computerY:7});
  assert.equal(leftMiss.v[8],1,'right player earns a point when the left computer misses');
  assert.equal(leftMiss.v[9],0);
  assert.equal(leftMiss.v[6],1,'next serve goes toward the right player');
  const rightMiss=simulate({address:0x3439,x:57,y:7,playerY:20,computerY:14});
  assert.equal(rightMiss.v[8],0);
  assert.equal(rightMiss.v[9],1,'left computer scores when the right player misses');
  assert.equal(rightMiss.v[6],255,'next serve goes toward the left computer');
});
test('Paddle Rally renders a centered colon between computer and player scores',()=>{
  const m=new Chip8();m.load(DEMO_ROM);
  for(let i=0;i<100;i++)m.step();
  const pixel=(x,y)=>m.pixels[y*64+x];
  // The custom 2-pixel colon sits between the score digits (x=24 and 36).
  assert.equal(pixel(31,1),1);
  assert.equal(pixel(32,1),1);
  assert.equal(pixel(31,3),1);
  assert.equal(pixel(32,3),1);
  assert.equal(pixel(31,2),0,'two dots are visually separated');
});

test('Paddle Rally responds to virtual keys 5 and 8 and clamps paddle',()=>{
  const m=new Chip8();m.load(DEMO_ROM);
  m.key(5,true);
  for(let i=0;i<1400;i++)m.step();
  assert.equal(m.v[2],7, 'W / touch 5 moves paddle up');
  m.key(5,false);m.key(8,true);
  for(let i=0;i<1800;i++)m.step();
  assert.equal(m.v[2],23, 'S / touch 8 moves paddle down');
  m.key(8,false);
});
test('Paddle Rally uses timed serves, reaches five points and freezes the final score',()=>{
  const m=new Chip8();m.load(DEMO_ROM);
  let scores=0,last=0,ended=false;
  for(let i=0;i<120000;i++){
    m.step();
    if(i%12===0)m.tick(); // match the browser's 12 CHIP-8 steps per 60Hz tick
    if(m.v[8]+m.v[9]!==last){scores++;last=m.v[8]+m.v[9];}
    if(i>=15){
      assert.ok(m.v[2]>=7 && m.v[2]<=23);
      assert.ok(m.v[3]>=7 && m.v[3]<=23);
    }
    if(m.v[14] && m.pc===DEMO_FINISHED_PC){ended=true;break;}
  }
  assert.ok(scores>=DEMO_WIN_SCORE,'games must advance to the finish line');
  assert.ok(ended,'winner must enter the final state');
  assert.ok(m.v[8]===DEMO_WIN_SCORE || m.v[9]===DEMO_WIN_SCORE);
  assert.equal(m.v[14],m.v[8]===DEMO_WIN_SCORE?1:2);
  const snapshot=[...m.v];
  for(let i=0;i<300;i++){m.step();m.tick();}
  assert.deepEqual([...m.v],snapshot,'result and scores cannot change after game over');
});

test('Paddle Rally delays the next serve by two seconds, without moving the ball',()=>{
  const instr=0x3405;
  const offset=DEMO_ROM.findIndex((_,i)=>i%2===0 && ((DEMO_ROM[i]<<8)|DEMO_ROM[i+1])===instr);
  assert.ok(offset>=0);
  const m=new Chip8();m.load(DEMO_ROM);
  m.pc=ROM_START+offset;
  m.v[4]=5;m.v[5]=20;m.v[2]=14;m.v[3]=7;
  for(let i=0;i<80 && m.delay!==DEMO_SERVE_DELAY_TICKS;i++)m.step();
  assert.equal(m.v[8],1,'computer missed: player scored');
  assert.equal(m.delay,120);
  assert.equal(m.v[4],32);
  // The countdown is controlled by CHIP-8 timer ticks, not CPU instruction count.
  for(let tick=0;tick<119;tick++){
    for(let step=0;step<12;step++)m.step();
    assert.equal(m.v[4],32,'ball stays centered during the countdown');
    m.tick();
  }
  assert.equal(m.delay,1);
  for(let step=0;step<12;step++)m.step();
  assert.equal(m.v[4],32);
  m.tick();
  let resumed=false;
  for(let i=0;i<150;i++){
    m.step();
    if(m.v[4]!==32){resumed=true;break;}
  }
  assert.ok(resumed,'serve resumes only after the countdown reaches zero');
});

test('Paddle Rally reports both win and loss correctly at five points',()=>{
  const find=opcode=>{
    const offset=DEMO_ROM.findIndex((_,i)=>i%2===0 && ((DEMO_ROM[i]<<8)|DEMO_ROM[i+1])===opcode);
    assert.ok(offset>=0);return ROM_START+offset;
  };
  for(const outcome of [
    {point:0x3405,computerY:7,playerY:14,ballX:5,ballY:20,score8:4,score9:2,winner:1},
    {point:0x3439,computerY:14,playerY:20,ballX:57,ballY:7,score8:3,score9:4,winner:2},
  ]){
    const m=new Chip8();m.load(DEMO_ROM);
    m.pc=find(outcome.point);m.v[2]=outcome.playerY;m.v[3]=outcome.computerY;
    m.v[4]=outcome.ballX;m.v[5]=outcome.ballY;m.v[8]=outcome.score8;m.v[9]=outcome.score9;
    for(let i=0;i<90 && m.pc!==DEMO_FINISHED_PC;i++)m.step();
    assert.equal(m.v[14],outcome.winner,'the correct side must win');
    assert.equal(m.pc,DEMO_FINISHED_PC,'winner must enter the immutable final state');
    assert.equal(outcome.winner===1?m.v[8]:m.v[9],DEMO_WIN_SCORE);
  }
});
test('bad unknown opcode fails closed',()=>{
  const m=machine(0x00fd);assert.throws(()=>m.step(),/지원하지/);
});
