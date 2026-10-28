/* Offline GPLv3 libretro/WASM adapter for Gearsystem and BlastEm. */
import { NesAudio } from './nes-audio.js?v=51743d8da793';
const ROM_KINDS=Object.freeze({'gearsystem-gg':1,'gearsystem-sms':2,'gearsystem-sg':3,blastem:4});
export const SEGA_BUTTONS=Object.freeze({
  up:4,down:5,left:6,right:7,start:3,select:2,
  a:0,b:8,c:11,x:9,y:1,z:10,mode:2,
});
const MEGADRIVE_BUTTONS = Object.freeze({a:0,b:8,c:11,x:9,y:1,z:10});
export class SegaPlayer {
  constructor(mod,canvas,systemId,audio){
    this.mod=mod;this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});
    this.systemId=systemId;this.audio=audio;this.active=false;
    this.keys=new Set();this.image=null;this.fps=60;this.audioCarry=0;
  }
  static async create(canvas,systemId,importer=path=>import(path),audio=new NesAudio()){
    if(!Object.hasOwn(ROM_KINDS,systemId))throw new Error('지원하지 않는 Sega 게임 플랫폼입니다.');
    const name=systemId==='blastem'?'blastem':'gearsystem';
    let factory;
    try{({default:factory}=await importer(`./${name}/${name}.js`));}
    catch{throw new Error(`${name} WASM이 없습니다. scripts/build_sega.py로 해당 엔진을 로컬에서 빌드해 주세요.`);}
    if(typeof factory!=='function')throw new Error(`${name} 모듈 형식이 잘못되었습니다.`);
    const mod=await factory({locateFile:file=>new URL(`./${name}/${file}`,import.meta.url).href});
    for(const fn of ['_ssh_retro_init','_ssh_retro_load','_ssh_retro_run','_ssh_retro_key','_ssh_retro_width','_ssh_retro_height','_ssh_retro_pixels','_ssh_retro_fps_milli','_ssh_retro_audio','_ssh_retro_audio_rate','_ssh_retro_save_size','_ssh_retro_save','_ssh_retro_restore','_ssh_retro_destroy','_malloc','_free']){
      if(typeof mod[fn]!=='function'){
        mod._ssh_retro_destroy?.();throw new Error(`${name} WASM API 누락: ${fn}`);
      }
    }
    return new SegaPlayer(mod,canvas,systemId,audio);
  }
  load(bytes){
    if(!(bytes instanceof Uint8Array)||bytes.length<64||bytes.length>8*1024*1024)throw new Error('유효하지 않은 Sega ROM입니다.');
    const ptr=this.mod._malloc(bytes.length);
    if(!ptr)throw new Error('ROM 메모리를 할당하지 못했습니다.');
    try{
      this.mod.HEAPU8.set(bytes,ptr);
      // Some libretro cores require path-based loading; keep a private in-memory
      // file for them, never uploading the ROM to OpenWrt or a remote endpoint.
      const filename=['','game.gg','game.sms','game.sg','game.gen'][ROM_KINDS[this.systemId]];
      if(this.mod.FS){try{this.mod.FS.mkdir('/tmp');}catch{/* existing directory */}
        this.mod.FS.writeFile('/tmp/'+filename,bytes);}
      if(!this.mod._ssh_retro_init()||!this.mod._ssh_retro_load(ptr,bytes.length,ROM_KINDS[this.systemId]))
        throw new Error('Sega 에뮬레이터가 게임을 열지 못했습니다.');
      this.active=true;
      const rate=this.mod._ssh_retro_fps_milli()/1000;
      if(rate>=30&&rate<=120)this.fps=rate;
      this.canvas.setAttribute?.('aria-label','Sega 게임 화면');
    }catch(error){this.mod._ssh_retro_destroy();throw error;}
    finally{this.mod._free(ptr);}
  }
  frame(){
    if(!this.active)return;
    this.mod._ssh_retro_run();
    const w=this.mod._ssh_retro_width(),h=this.mod._ssh_retro_height();
    if(w>0&&h>0&&w<=1024&&h<=512){
      if(this.canvas.width!==w||this.canvas.height!==h){
        this.canvas.width=w;this.canvas.height=h;this.image=this.ctx.createImageData(w,h);
      }
      const ptr=this.mod._ssh_retro_pixels(),size=w*h*4;
      if(!ptr||ptr+size>this.mod.HEAPU8.length)throw new Error('Sega 영상 버퍼 접근 오류');
      this.image.data.set(this.mod.HEAPU8.subarray(ptr,ptr+size));
      this.ctx.putImageData(this.image,0,0);
    }
    if(this.audio.node&&typeof this.mod._ssh_retro_audio==='function'){
      const framesPtr=this.mod._malloc(4);
      if(framesPtr){
        try{
          for(let i=0;i<8;i++){
            const ptr=this.mod._ssh_retro_audio(2048,framesPtr),n=this.mod.HEAPU32[framesPtr>>2];
            if(!ptr||!n)break;
            const data=this.mod.HEAP16.subarray(ptr>>1,(ptr>>1)+n*2);
            // Libretro cores expose rates other than WebAudio's actual output
            // sample rate (notably BlastEm). Convert frame counts so audio
            // does not play at a different pitch or run away from video.
            const inputRate=this.mod._ssh_retro_audio_rate()||44100;
            const outputRate=this.audio.sampleRate||48000;
            for(let j=0;j<n;j++){
              this.audioCarry+=outputRate;
              while(this.audioCarry>=inputRate){
                this.audio.push(data[j*2]/32768,data[j*2+1]/32768);
                this.audioCarry-=inputRate;
              }
            }
          }
        }finally{this.mod._free(framesPtr);}
      }
    }
  }
  key(name,down){
    if(!this.active)return;
    const key=this.systemId==='blastem'?MEGADRIVE_BUTTONS[name]:SEGA_BUTTONS[name];
    const id=key===undefined?SEGA_BUTTONS[name]:key;
    if(id===undefined)return;
    if(down)this.keys.add(name);else this.keys.delete(name);
    this.mod._ssh_retro_key(id,down?1:0);
  }
  battery(){
    if(!this.active)return null;
    const size=this.mod._ssh_retro_save_size();if(!size||size>256*1024)return null;
    const ptr=this.mod._malloc(size);if(!ptr)return null;
    try{return this.mod._ssh_retro_save(ptr,size)===size?this.mod.HEAPU8.slice(ptr,ptr+size):null;}
    finally{this.mod._free(ptr);}
  }
  restore(bytes){
    if(!this.active||!(bytes instanceof Uint8Array)||bytes.length!==this.mod._ssh_retro_save_size())return false;
    const ptr=this.mod._malloc(bytes.length);if(!ptr)return false;
    try{this.mod.HEAPU8.set(bytes,ptr);return !!this.mod._ssh_retro_restore(ptr,bytes.length);}
    finally{this.mod._free(ptr);}
  }
  enableAudio(){return this.audio.enable();}
  pause(){this.audio.pause();}
  resume(){this.audio.resume();}
  destroy(){this.audio.destroy();this.mod._ssh_retro_destroy();this.active=false;}
}
