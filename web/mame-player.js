import { arcadeMachine } from './mame/machines.js?v=fe66260ee1a4';
/* Browser-local MAME arcade iframe adapter, isolated from mGBA/Sega canvases. */
const ARCADE_URL = new URL('./mame/runner.html', import.meta.url);
const IDLE_TIMEOUT = 45000;
export class MamePlayer {
  constructor(frame) { this.iframe=frame; this.active=false; this.fps=60; this.paused=false; }
  static create(stage, bytes, filename, {timeout=IDLE_TIMEOUT}={}) {
    if (!(bytes instanceof Uint8Array) || bytes.length<22 || bytes[0]!==0x50 || bytes[1]!==0x4b || bytes[2]!==3 || bytes[3]!==4 || !arcadeMachine(filename))
      return Promise.reject(new Error('지원하지 않는 아케이드 ROM입니다.'));
    const iframe=document.createElement('iframe');
    iframe.src=ARCADE_URL.href;
    iframe.title='아케이드 게임 화면';
    iframe.className='mame-frame';
    iframe.setAttribute('allow','autoplay');
    iframe.setAttribute('referrerpolicy','no-referrer');
    // A separate frame owns SDL canvas and runtime. It never sees the parent app's DOM.
    stage.appendChild(iframe);
    const player=new MamePlayer(iframe);
    return new Promise((resolve,reject)=>{
      let done=false;
      const cleanup=()=>{clearTimeout(timer);window.removeEventListener('message',receive);};
      const fail=message=>{if(done)return;done=true;cleanup();iframe.remove();reject(new Error(message));};
      const timer=setTimeout(()=>fail('아케이드 엔진 초기화 시간이 초과되었습니다.'),timeout);
      function receive(event){
        if(event.origin!==location.origin||event.source!==iframe.contentWindow)return;
        const data=event.data||{};
        if(data.mame==='ready'){
          const copy=bytes.slice().buffer; // do not transfer the caller's original bytes
          iframe.contentWindow.postMessage({mame:'boot',filename,bytes:copy},location.origin,[copy]);
        } else if(data.mame==='running'){
          if(done)return;done=true;cleanup();player.active=true;resolve(player);
        } else if(data.mame==='error') fail('아케이드 실행 오류: '+String(data.message).slice(0,250));
      }
      window.addEventListener('message',receive);
      iframe.addEventListener('error',()=>fail('아케이드 화면을 불러오지 못했습니다.'),{once:true});
    });
  }
  frame() {} // MAME/Emscripten runs its own SDL main loop.
  key(name,pressed){if(this.active)this.iframe.contentWindow?.postMessage({mame:'key',key:name,pressed},location.origin);}
  pause(){if(!this.paused){this.key('pause',true);this.key('pause',false);this.paused=true;}}
  resume(){if(this.paused){this.key('pause',true);this.key('pause',false);this.paused=false;}}
  destroy(){this.active=false;this.iframe.remove();}
}
