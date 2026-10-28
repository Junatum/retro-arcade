import test from 'node:test';
import assert from 'node:assert/strict';
import {SegaPlayer} from '../web/sega-player.js';

function fakeModule(){
  const mem=new ArrayBuffer(4*1024*1024),u8=new Uint8Array(mem);
  const statuses={started:false,loaded:false,buttons:[],destroyed:false};
  let alloc=1024;
  const mod={
    HEAPU8:u8,HEAPU16:new Uint16Array(mem),HEAPU32:new Uint32Array(mem),HEAP16:new Int16Array(mem),
    _malloc(size){const ptr=alloc;alloc+=size+8;return ptr;},_free(){},
    FS:{mkdir(){},writeFile(path,bytes){statuses.path=path;statuses.bytes=new Uint8Array(bytes);}},
    _ssh_retro_init(){statuses.started=true;return 1;},
    _ssh_retro_load(ptr,len,kind){statuses.kind=kind;statuses.rom=u8.slice(ptr,ptr+len);statuses.loaded=true;return 1;},
    _ssh_retro_key(id,pressed){statuses.buttons.push([id,pressed]);},
    _ssh_retro_run(){statuses.runs=(statuses.runs||0)+1;u8.set([12,34,56,255],16);},
    _ssh_retro_width(){return 1;},_ssh_retro_height(){return 1;},_ssh_retro_pixels(){return 16;},
    _ssh_retro_fps_milli(){return 59920;},_ssh_retro_audio_rate(){return 44100;},
    _ssh_retro_audio(max,out){mod.HEAPU32[out>>2]=0;return 512;},
    _ssh_retro_save_size(){return 8;},
    _ssh_retro_save(ptr,size){u8.set([1,2,3,4,5,6,7,8],ptr);return size;},
    _ssh_retro_restore(ptr,len){statuses.saved=u8.slice(ptr,ptr+len);return 1;},
    _ssh_retro_destroy(){statuses.destroyed=true;},
  };
  return {mod,statuses};
}
function canvas(){
  const output={image:null};
  const element={width:0,height:0,setAttribute(){},getContext(){return {
    createImageData(w,h){return {data:new Uint8ClampedArray(w*h*4)};},
    putImageData(image){output.image=image;},
  };}};
  return {element,output};
}
for(const [system,kind,path] of [
  ['gearsystem-gg',1,'/tmp/game.gg'],['gearsystem-sms',2,'/tmp/game.sms'],
  ['gearsystem-sg',3,'/tmp/game.sg'],['blastem',4,'/tmp/game.gen'],
]){
  test(`${system} uses local WASM bridge, draws frame and persists RAM`,async()=>{
    const {mod,statuses}=fakeModule(),{element,output}=canvas();
    const player=await SegaPlayer.create(element,system,async()=>({default:async()=>mod}),{node:null,destroy(){},pause(){},resume(){}});
    const rom=new Uint8Array(1024).fill(17);player.load(rom);
    assert.equal(statuses.kind,kind);assert.equal(statuses.path,path);
    assert.deepEqual(statuses.rom,rom);assert.equal(player.fps,59.92);
    player.key('a',true);
    assert.deepEqual(statuses.buttons.at(-1),[system==='blastem'?0:0,1]);
    player.frame();assert.deepEqual([...output.image.data],[12,34,56,255]);
    assert.deepEqual([...player.battery()],[1,2,3,4,5,6,7,8]);
    assert.equal(player.restore(new Uint8Array(8).fill(7)),true);
    assert.equal(statuses.saved[0],7);
    player.destroy();assert.equal(statuses.destroyed,true);
  });
}
test('missing WASM fails closed and never downloads a runtime core',async()=>{
  const {element}=canvas();
  await assert.rejects(SegaPlayer.create(element,'gearsystem-gg',async()=>{throw Error('no core');}),/로컬에서 빌드/);
  await assert.rejects(SegaPlayer.create(element,'unknown'),/지원하지 않는/);
});

test('BlastEm uses six-button libretro mapping from upstream input descriptors', async()=>{
  const {mod,statuses}=fakeModule(),{element}=canvas();
  const player=await SegaPlayer.create(element,'blastem',async()=>({default:async()=>mod}),{node:null,destroy(){}});
  player.load(new Uint8Array(1024));
  for(const [key,id] of Object.entries({a:0,b:8,c:11,x:9,y:1,z:10,mode:2,start:3})){
    player.key(key,true);
    assert.deepEqual(statuses.buttons.at(-1),[id,1],key);
    player.key(key,false);
    assert.deepEqual(statuses.buttons.at(-1),[id,0],key);
  }
  player.destroy();
});
test('Sega audio output accounts for the actual browser sample rate',async()=>{
  const {mod}=fakeModule(),{element}=canvas();
  const samples=[];
  mod._ssh_retro_audio_rate=()=>24000;
  let first=true;
  mod._ssh_retro_audio=(max,out)=>{mod.HEAP16.set([16384,-16384],256);mod.HEAPU32[out>>2]=first?1:0;first=false;return 512;};
  const player=await SegaPlayer.create(element,'blastem',async()=>({default:async()=>mod}),
    {node:{},sampleRate:48000,push(...sample){samples.push(sample);},destroy(){}});
  player.load(new Uint8Array(1024));
  player.frame();
  // The 24 kHz input frame becomes two 48 kHz output frames.
  assert.deepEqual(samples,[[0.5,-0.5],[0.5,-0.5]]);
  player.destroy();
});
