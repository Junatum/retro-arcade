/* mGBA 0.10.5 WASM bridge for GB/GBC/GBA; silent HTTP-compatible frontend. */
export const GBA_WIDTH=240, GBA_HEIGHT=160, GB_WIDTH=160, GB_HEIGHT=144;
// mGBA GBA keypad enum: A B Select Start Right Left Up Down R L
export const GBA_BUTTONS=Object.freeze({a:0,b:1,select:2,start:3,right:4,left:5,up:6,down:7,r:8,l:9});
export class MgbaPlayer {
  constructor(mod,canvas){
    this.mod=mod;this.canvas=canvas;
    canvas.width=GBA_WIDTH;canvas.height=GBA_HEIGHT;
    this.ctx=canvas.getContext('2d',{alpha:false});
    this.image=this.ctx.createImageData(GBA_WIDTH,GBA_HEIGHT);
    this.active=false;
    this.width=GBA_WIDTH;this.height=GBA_HEIGHT;
  }
  static async create(canvas, importer=()=>import('./mgba/mgba.js')){
    let factory;
    try {({default:factory}=await importer());}
    catch {throw new Error('mGBA WASM 파일이 없습니다. docs/ARCHITECTURE.md의 로컬 빌드 절차를 확인해 주세요.');}
    if(typeof factory!=='function')throw new Error('mGBA 모듈 형식이 잘못되었습니다.');
    const mod=await factory({locateFile:name=>new URL(`./mgba/${name}`,import.meta.url).href});
    for(const fn of ['_ssh_mgba_load','_ssh_mgba_frame','_ssh_mgba_framebuffer','_ssh_mgba_width','_ssh_mgba_height','_ssh_mgba_key','_ssh_mgba_save_size','_ssh_mgba_save','_ssh_mgba_restore','_ssh_mgba_destroy','_malloc','_free']){
      if(typeof mod[fn]!=='function')throw new Error(`mGBA API 누락: ${fn} (scripts/build_mgba.py로 WASM을 다시 빌드해 주세요.)`);
    }
    return new MgbaPlayer(mod,canvas);
  }
  load(bytes,platform='gba'){
    if(platform!=='gba'&&platform!=='gb')throw new Error('지원하지 않는 게임 플랫폼입니다.');
    const gb=platform==='gb';
    if(!(bytes instanceof Uint8Array)||bytes.length<(gb?0x150:0xc0)||bytes.length>(gb?8:32)*1024*1024)
      throw new Error(gb?'유효한 GB/GBC ROM이 아닙니다.':'유효한 GBA ROM이 아닙니다.');
    const ptr=this.mod._malloc(bytes.length);
    if(!ptr)throw new Error('게임 ROM 메모리를 할당하지 못했습니다.');
    try{
      this.mod.HEAPU8.set(bytes,ptr);
      if(!this.mod._ssh_mgba_load(ptr,bytes.length,gb?1:0))throw new Error('mGBA가 ROM을 열지 못했습니다.');
    } finally{this.mod._free(ptr);}
    const width=this.mod._ssh_mgba_width(),height=this.mod._ssh_mgba_height();
    if((gb && (width!==GB_WIDTH||height!==GB_HEIGHT)) ||
       (!gb && (width!==GBA_WIDTH||height!==GBA_HEIGHT))) {
      this.mod._ssh_mgba_destroy();
      throw new Error('mGBA 화면 해상도가 올바르지 않습니다.');
    }
    this.width=width;this.height=height;
    this.canvas.setAttribute?.('aria-label',gb?'Game Boy 게임 화면':'Game Boy Advance 게임 화면');
    this.canvas.width=width;this.canvas.height=height;
    this.image=this.ctx.createImageData(width,height);
    this.active=true;
  }
  frame(){
    if(!this.active)return;
    this.mod._ssh_mgba_frame();
    const ptr=this.mod._ssh_mgba_framebuffer(), size=this.width*this.height*4;
    if(!ptr||ptr+size>this.mod.HEAPU8.length)throw new Error('mGBA 화면 버퍼 접근 오류');
    this.image.data.set(this.mod.HEAPU8.subarray(ptr,ptr+size));
    this.ctx.putImageData(this.image,0,0);
  }
  key(button,pressed){if(this.active&&Object.hasOwn(GBA_BUTTONS,button))this.mod._ssh_mgba_key(GBA_BUTTONS[button],pressed?1:0);}
  battery(){
    if(!this.active)return null;
    const size=this.mod._ssh_mgba_save_size();
    if(size<=0||size>256*1024)return null;
    const ptr=this.mod._malloc(size);if(!ptr)return null;
    try{const count=this.mod._ssh_mgba_save(ptr,size);return count>0&&count<=size?this.mod.HEAPU8.slice(ptr,ptr+count):null;}
    finally{this.mod._free(ptr);}
  }
  restore(bytes){
    if(!this.active||!(bytes instanceof Uint8Array)||!bytes.length||bytes.length>256*1024)return false;
    const ptr=this.mod._malloc(bytes.length);if(!ptr)return false;
    try{this.mod.HEAPU8.set(bytes,ptr);return Boolean(this.mod._ssh_mgba_restore(ptr,bytes.length));}
    finally{this.mod._free(ptr);}
  }
  destroy(){if(this.active){this.mod._ssh_mgba_destroy();this.active=false;}}
}
