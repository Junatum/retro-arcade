import test from 'node:test';
import assert from 'node:assert/strict';
import {JsnesPlayer, NES_WIDTH, NES_HEIGHT, validateNesBytes} from '../web/jsnes-player.mjs';
import {NesAudio} from '../web/nes-audio.mjs';

const blankRom = () => {
  const rom = new Uint8Array(16 + 16384);rom.set([0x4e,0x45,0x53,0x1a,1,0,2]);return rom;
};
const changes = [];
class MockController { static BUTTON_A=0; static BUTTON_B=1; static BUTTON_START=3; static BUTTON_SELECT=2; static BUTTON_UP=4; static BUTTON_DOWN=5; static BUTTON_LEFT=6; static BUTTON_RIGHT=7; }
class MockNes {
  constructor(opts) { this.opts=opts; this.cpu={mem:new Uint8Array(65536)};this.papu={sampleRate:48000,sampleTimerMax:1};this.rom={batteryRam:true};this.pressed=[]; }
  loadROM(bytes) { this.bytes=bytes; }
  frame() { this.opts.onFrame(new Int32Array(NES_WIDTH*NES_HEIGHT).fill(0xff123456));this.opts.onAudioSample(0.5,-0.5); }
  buttonDown(p,b) {this.pressed.push(['down',p,b]);}
  buttonUp(p,b) {this.pressed.push(['up',p,b]);}
}
function setup() {
  let actual;
  const canvas={width:0,height:0,getContext:()=>({createImageData:(width,height)=>({data:new Uint8ClampedArray(width*height*4)}),putImageData:image=>{actual=image;}})};
  const audio={push:(...sample)=>changes.push(sample), enable:async()=>true,sampleRate:48000,pause(){},resume(){},destroy(){}};
  const player=new JsnesPlayer(canvas,MockNes,MockController,audio);
  return {player,canvas,get image(){return actual;}};
}
test('NES ROM validates iNES magic and sane minimum length',()=>{
  assert.doesNotThrow(()=>validateNesBytes(blankRom()));
  assert.throws(()=>validateNesBytes(new Uint8Array(16)),/NES/);
  const broken=blankRom();broken[0]=0;
  assert.throws(()=>validateNesBytes(broken),/NES/);
});
test('NES frames are 256x240 and ARGB rendered in correct RGB order',()=>{
  const stage=setup(); stage.player.load(blankRom());stage.player.frame();
  assert.equal(stage.canvas.width,256);assert.equal(stage.canvas.height,240);
  assert.deepEqual([...stage.image.data.slice(0,4)],[0x12,0x34,0x56,255]);
  assert.deepEqual(changes.at(-1),[0.5,-0.5]);
});
test('NES buttons retain authentic A/B and SELECT/START mapping',()=>{
  const {player}=setup();player.load(blankRom());
  player.key('b',true);player.key('a',true);player.key('select',true);player.key('start',true);
  player.key('left',false);player.key('l',true);
  assert.deepEqual(player.core.pressed,[['down',1,1],['down',1,0],['down',1,2],['down',1,3],['up',1,6]]);
});
test('NES 8KiB battery RAM uses browser-only bytes; non-battery ROM saves nothing',()=>{
  const {player}=setup();player.load(blankRom());
  const data=new Uint8Array(8192);data[5]=42;
  assert.equal(player.restore(data),true);assert.equal(player.core.cpu.mem[0x6005],42);
  assert.equal(player.battery()[5],42);
  player.core.opts.onBatteryRamWrite(0x6006,78);
  assert.equal(player.sram[6],78);
  assert.equal(player.restore(new Uint8Array(10)),false);
  player.core.rom.batteryRam=false;assert.equal(player.battery(),null);
});
test('AudioContext sample queue operates without AudioWorklet and stops safely',async()=>{
  let output;
  const fakeScope={AudioContext:class {
    constructor(){this.sampleRate=48000;this.destination={};}
    createScriptProcessor(){return {connect(){},disconnect(){},set onaudioprocess(fn){output=fn;},get onaudioprocess(){return output;}};}
    async resume(){} async suspend(){} async close(){}
  }};
  const engine=new NesAudio(fakeScope);
  assert.equal(await engine.enable(),true);
  engine.push(0.25,-0.75);
  const a=new Float32Array(2),b=new Float32Array(2);
  output({outputBuffer:{getChannelData:i=>i?b:a}});
  assert.deepEqual([...a],[0.25,0]);assert.deepEqual([...b],[-0.75,0]);
  engine.destroy();
});
