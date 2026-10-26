import test from 'node:test';
import assert from 'node:assert/strict';
import {MgbaPlayer,GBA_BUTTONS,GBA_WIDTH,GBA_HEIGHT,GB_WIDTH,GB_HEIGHT} from '../web/mgba-player.mjs';
function createMock(){
  const bytes=new Uint8Array(32*1024*1024+256);
  const calls={painted:0,loads:[],frames:0,pressed:[],freed:[],restored:0,destroyed:0};
  let width=GBA_WIDTH,height=GBA_HEIGHT;
  const canvas={width:0,height:0,getContext:()=>({
    createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),
    putImageData:()=>{calls.painted++},
  })};
  const mod={HEAPU8:bytes,_malloc:()=>2048,_free:(p)=>calls.freed.push(p),
    _ssh_mgba_load:(ptr,len,platform)=>{calls.loads.push(platform);width=platform?GB_WIDTH:GBA_WIDTH;height=platform?GB_HEIGHT:GBA_HEIGHT;return 1},
    _ssh_mgba_width:()=>width,_ssh_mgba_height:()=>height,
    _ssh_mgba_frame:()=>calls.frames++, _ssh_mgba_framebuffer:()=>65536,
    _ssh_mgba_key:(button,pressed)=>calls.pressed.push([button,pressed]),
    _ssh_mgba_save_size:()=>4, _ssh_mgba_save:ptr=>{bytes.set([3,4,5,6],ptr);return 4},
    _ssh_mgba_restore:()=>{calls.restored++;return 1},
    _ssh_mgba_destroy:()=>calls.destroyed++,
  };
  return {canvas,mod,calls};
}
test('mGBA GBA display and savedata lifecycle',async()=>{
  const {canvas,mod,calls}=createMock();
  const player=await MgbaPlayer.create(canvas,async()=>({default:async()=>mod}));
  assert.equal(canvas.width,GBA_WIDTH);assert.equal(canvas.height,GBA_HEIGHT);
  player.load(new Uint8Array(1024),'gba');assert.deepEqual(calls.loads,[0]);
  player.frame();assert.equal(calls.frames,1);assert.equal(calls.painted,1);
  player.key('r',true);player.key('l',false);
  assert.deepEqual(calls.pressed,[[GBA_BUTTONS.r,1],[GBA_BUTTONS.l,0]]);
  assert.deepEqual(Array.from(player.battery()),[3,4,5,6]);
  assert.equal(player.restore(new Uint8Array([1,2])),true);
  assert.equal(calls.restored,1);player.destroy();assert.equal(calls.destroyed,1);
});
test('mGBA GB/GBC uses GB core, 160x144 canvas and same inputs',async()=>{
  const {canvas,mod,calls}=createMock();
  const player=await MgbaPlayer.create(canvas,async()=>({default:async()=>mod}));
  player.load(new Uint8Array(32768),'gb');
  assert.deepEqual(calls.loads,[1]);
  assert.equal(canvas.width,GB_WIDTH);assert.equal(canvas.height,GB_HEIGHT);
  player.frame();assert.equal(calls.painted,1);
  player.key('a',true);
  assert.deepEqual(calls.pressed.at(-1),[GBA_BUTTONS.a,1]);
  player.destroy();
});
test('mGBA rejects invalid ROM, unexpected dimensions and missing ABI',async()=>{
  const {canvas,mod,calls}=createMock();
  const player=await MgbaPlayer.create(canvas,async()=>({default:async()=>mod}));
  assert.throws(()=>player.load(new Uint8Array(100),'gba'),/유효한 GBA ROM/);
  assert.throws(()=>player.load(new Uint8Array(100),'gb'),/유효한 GB\/GBC ROM/);
  assert.throws(()=>player.load(new Uint8Array(1024),'nes'),/지원하지 않는/);
  player.load(new Uint8Array(1024),'gba');
  assert.equal(player.restore(new Uint8Array(256*1024+1)),false);
  assert.equal(calls.restored,0);
  const wrong={...mod};delete wrong._ssh_mgba_width;
  await assert.rejects(MgbaPlayer.create(canvas,async()=>({default:async()=>wrong})),/API 누락/);
  await assert.rejects(MgbaPlayer.create(canvas,async()=>{throw Error('not found')}),/mGBA WASM/);
});
