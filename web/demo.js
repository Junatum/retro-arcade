/*
 * Paddle Rally — a newly authored CHIP-8 paddle-and-ball mini-game.
 * Copyright (C) 2026 SmartSafeHub contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * This is original CHIP-8 code and sprites, not an Atari game ROM or a port.
 * Up: CHIP-8 key 5 (W on the keyboard); Down: key 8 (S on the keyboard).
 * Score is displayed at the top: AI left, player right. The colors are
 * applied by the browser only when this bundled demo is selected.
 *
 * Compile human-readable 16-bit opcodes to CHIP-8 ROM bytes, resolving
 * label references at module load. ROM starts at 0x200 and needs no assets.
 */
import { ROM_START, MAX_ROM_BYTES } from './chip8.js';

export const DEMO_TITLE = '패들 랠리';
export const DEMO_CONTROLS = '패들 이동: W / S (터치 키패드 5 / 8)';
export const DEMO_WIN_SCORE = 5;
export const DEMO_SERVE_DELAY_TICKS = 120; // 2 seconds at 60Hz after a point

function createPaddleRallyRom(){
  const bytes=[];
  const labels=new Map();
  const fixes=[];
  const op=word=>{bytes.push(word >>> 8, word & 255);};
  const mark=name=>{
    if(labels.has(name))throw Error(`CHIP-8 duplicate label: ${name}`);
    labels.set(name,ROM_START+bytes.length);
  };
  const ref=(base,name)=>{fixes.push({at:bytes.length,base,name});op(0);};
  const jump=name=>ref(0x1000,name);
  const call=name=>ref(0x2000,name);
  const sprite=(name,data)=>{mark(name);bytes.push(...data);};

  // v2=right-side player Y, v3=left-side computer Y, v4/v5=ball X/Y,
  // v6/v7=ball delta X/Y, v8/v9=scores, vD=AI counter, vE=winner (1 player, 2 AI).
  op(0x00E0);   // CLS
  op(0x620E);   // player Y = 14
  op(0x630E);   // opponent Y = 14
  op(0x6420);   // ball X = 32
  op(0x650F);   // ball Y = 15
  op(0x66FF);   // ball delta X = -1
  op(0x6701);   // ball delta Y = +1
  op(0x6800);   // player score = 0
  op(0x6900);   // AI score = 0
  op(0x6D00);   // AI step counter = 0
  op(0x6E00);   // no winner yet

  mark('loop');
  op(0x3E00);jump('finished'); // freeze permanently after the fifth point
  // Move player paddle with CHIP-8 keys 5 and 8; clamp to playfield.
  op(0x6A05);op(0xEA9E);jump('downKey');
  op(0x3207);op(0x72FF);
  mark('downKey');
  op(0x6A08);op(0xEA9E);jump('ai');
  op(0x3217);op(0x7201);

  mark('ai');
  // Deliberately slow opponent (one step every four ball movements).
  op(0x7D01);op(0x3D04);jump('advance');op(0x6D00);
  op(0x8B50);       // vB=ball Y
  op(0x8C30);op(0x7C02);  // vC=opponent Y + 2
  op(0x8BC5);       // vB=ball Y-(opponent Y+2), vF = no borrow
  op(0x3F01);jump('aiUp');
  op(0x3317);op(0x7301);jump('advance');
  mark('aiUp');
  op(0x3307);op(0x73FF);

  mark('advance');
  op(0xFC07);op(0x3C00);jump('render'); // keep ball still during serve countdown
  op(0x8464);op(0x8574); // move ball
  op(0x3507);jump('bottom');call('reverseY');
  mark('bottom');
  op(0x351B);jump('left');call('reverseY');

  mark('left');
  op(0x3405);jump('right'); // ball reaches computer at x=5
  op(0x8B50);op(0x8B35);   // vB=ball Y-computer Y
  op(0x3F01);jump('missLeft'); // ball above computer paddle
  op(0x6C05);op(0x8CB5);   // vC=5-difference
  op(0x3F01);jump('missLeft'); // ball below computer paddle
  op(0x6601);jump('right'); // successful return → right

  mark('missLeft');
  op(0x7801); // player scores when left-side computer misses
  op(0x3800 | DEMO_WIN_SCORE);jump('resetTowardPlayer');op(0x6E01);jump('endPoint');
  mark('resetTowardPlayer');
  op(0x6420);op(0x650F);op(0x6601);op(0x6000 | DEMO_SERVE_DELAY_TICKS);op(0xF015);jump('render');

  mark('right');
  op(0x3439);jump('render'); // ball reaches player at x=57
  op(0x8B50);op(0x8B25);   // vB=ball Y-player Y
  op(0x3F01);jump('missRight');
  op(0x6C05);op(0x8CB5);
  op(0x3F01);jump('missRight');
  op(0x66FF);jump('render'); // successful player return → left

  mark('missRight');
  op(0x7901); // computer scores when right-side player misses
  op(0x3900 | DEMO_WIN_SCORE);jump('resetTowardAi');op(0x6E02);jump('endPoint');
  mark('resetTowardAi');
  op(0x6420);op(0x650F);op(0x66FF);op(0x6000 | DEMO_SERVE_DELAY_TICKS);op(0xF015);jump('render');

  mark('endPoint');
  op(0x6420);op(0x650F); // show centered ball and final scoreboard

  mark('render');
  op(0x00E0);
  op(0x6018);op(0x6100);op(0xF929);op(0xD015); // left computer score glyph
  op(0x6024);op(0xF829);op(0xD015);             // right player score glyph
  // Draw the separator as part of the CHIP-8 scoreboard so it scales with it.
  op(0x601F);op(0x6100);ref(0xA000,'scoreColon');op(0xD015); // centered ':'
  op(0x6003);op(0x8130);ref(0xA000,'paddle');op(0xD016); // left computer
  op(0x603A);op(0x8120);ref(0xA000,'paddle');op(0xD016); // right player
  op(0x8040);op(0x8150);ref(0xA000,'ball');op(0xD012);
  jump('loop');

  mark('reverseY');
  op(0x6C00);op(0x8C75);op(0x87C0);op(0x00EE);

  mark('finished');
  jump('finished');

  sprite('paddle',[0xE0,0xE0,0xE0,0xE0,0xE0,0xE0]);
  sprite('ball',[0xC0,0xC0]);
  sprite('scoreColon',[0x00,0xC0,0x00,0xC0,0x00]); // ':' between x=24 and x=36

  for(const fix of fixes){
    const target=labels.get(fix.name);
    if(target===undefined||target>0xFFF)throw Error(`CHIP-8 unknown label: ${fix.name}`);
    const word=fix.base|target;
    bytes[fix.at]=word>>>8;
    bytes[fix.at+1]=word&255;
  }
  if(bytes.length>MAX_ROM_BYTES)throw Error('CHIP-8 game exceeds ROM memory');
  return {rom:Uint8Array.from(bytes), finishedPc:labels.get('finished')};
}
const demoProgram=createPaddleRallyRom();
export const DEMO_ROM=demoProgram.rom;
export const DEMO_FINISHED_PC=demoProgram.finishedPc;
