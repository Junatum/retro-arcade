/* SmartSafeHub Retro Arcade — GPL-3.0-or-later; entirely local browser playback. */
import { Chip8, DISPLAY_WIDTH, DISPLAY_HEIGHT } from './chip8.js';
import { DEMO_ROM } from './demo.js';
import { SYSTEMS, detectSystem, validateRom } from './systems.js?v=0.1.0-r3';
import { romStorageKey, batteryRead, batteryWrite } from './battery-store.js?v=0.1.0-r3';
import { MgbaPlayer } from './mgba-player.js';
import { JsnesPlayer } from './jsnes-player.js';
import { setupFullscreen } from './fullscreen.js';
import { renderController, CHIP8_KEYBOARD, CHIP8_MATRIX, HANDHELD_KEYS } from './controller.js?v=0.1.0-r3';
const $ = id => document.getElementById(id);
const input=$('rom-file'), notice=$('notice'), stage=$('game');
const fullscreen=setupFullscreen($('player-section'),$('fullscreen'),document,document.body);
$('fullscreen').onclick=()=>{if(loaded)void fullscreen.toggle();};
const canvas=document.createElement('canvas');
canvas.width=DISPLAY_WIDTH;canvas.height=DISPLAY_HEIGHT;
canvas.setAttribute('aria-label','에뮬레이터 게임 화면');
stage.appendChild(canvas);
const ctx=canvas.getContext('2d',{alpha:false});
const chip8=new Chip8();
const KEYMAP=new Map([...CHIP8_KEYBOARD].map((key,index)=>[key,CHIP8_MATRIX[index]]));
const GBKEY=new Map([['arrowup','up'],['arrowdown','down'],['arrowleft','left'],['arrowright','right'],['x','a'],['z','b'],['enter','start'],['shift','select'],['a','l'],['s','r']]);
let selected=SYSTEMS[0], game=null, running=false, loaded=false, frame=0, last=0,clock=0;
let saveKey=null,framesSinceSave=0,loading=false,activeController=null;
function announce(message,ok=false){notice.textContent=message;notice.classList.toggle('ok',ok);notice.classList.remove('hidden');}
function paintChip8(){
  if(canvas.width!==DISPLAY_WIDTH||canvas.height!==DISPLAY_HEIGHT){canvas.width=DISPLAY_WIDTH;canvas.height=DISPLAY_HEIGHT;}
  const image=ctx.createImageData(DISPLAY_WIDTH,DISPLAY_HEIGHT);
  for(let i=0;i<chip8.pixels.length;i++){
    let j=i*4,lit=Boolean(chip8.pixels[i]);
    image.data[j]=lit?185:10;image.data[j+1]=lit?251:14;image.data[j+2]=lit?194:26;image.data[j+3]=255;
  }
  ctx.putImageData(image,0,0);chip8.changed=false;
}
function drawLoop(time){
  if(!running)return;
  const elapsed=Math.min(100,Math.max(0,time-(last||time)));last=time;
  clock+=elapsed;
  try{
    if(selected.id==='chip8'){
      let count=0;
      while(clock>=1000/60 && count++<6){clock-=1000/60;for(let i=0;i<12;i++)chip8.step();chip8.tick();}
      if(chip8.changed)paintChip8();
    } else if(game){
      let count=0;
      while(clock>=1000/59.7275 && count++<5){clock-=1000/59.7275;game.frame();framesSinceSave++;}
      if(framesSinceSave>=1800){framesSinceSave=0;void persistBattery();}
    }
  }catch(error){stop(`실행 중 오류: ${error.message}`);return;}
  frame=requestAnimationFrame(drawLoop);
}
function stop(reason){running=false;cancelAnimationFrame(frame);game?.pause?.();$('toggle').textContent='▶ 계속';if(reason)announce(reason);}
function showPlayer(system,label){
  loaded=true;running=true;last=0;clock=0;framesSinceSave=0;
  $('intro').classList.add('hidden');$('system-library').classList.add('hidden');$('load-area').classList.add('hidden');
  $('player-section').classList.remove('hidden');
  $('player-title').textContent=`${system.label} · ${label}`;
  $('toggle').textContent='Ⅱ 일시정지';notice.classList.add('hidden');
  $('sound').classList.toggle('hidden', system.id!=='nes');
  renderKeypad();
  frame=requestAnimationFrame(drawLoop);
  $('player-section').scrollIntoView({block:'start',behavior:'smooth'});
}
async function persistBattery(){if(game&&saveKey){const bytes=game.battery();if(bytes)await batteryWrite(saveKey,bytes);}}
function playChip8(bytes,label){
  cancelAnimationFrame(frame);chip8.load(bytes);game=null;saveKey=null;
  paintChip8();showPlayer(SYSTEMS[0],label);
}
async function playMgba(bytes,label){
  const system=selected;
  const player=await MgbaPlayer.create(canvas);
  try {
    player.load(bytes,system.id==='mgba'?'gba':'gb');
    const key=romStorageKey(bytes);
    const saved=await batteryRead(key);
    if(saved)player.restore(saved);
    game=player;saveKey=key;showPlayer(system,label);
  }catch(error){player.destroy();throw error;}
}
async function playNes(bytes,label){
  const player=await JsnesPlayer.create(canvas);
  try {
    player.load(bytes);
    const key=romStorageKey(bytes,'jsnes');
    const saved=await batteryRead(key);
    if(saved)player.restore(saved);
    game=player;saveKey=key;showPlayer(selected,label);
  }catch(error){player.destroy();throw error;}
}
function renderKeypad(){
  activeController?.releaseAll();
  activeController=renderController($('keypad'),selected.id,(key,pressed)=>{
    if(selected.id==='chip8')chip8.key(key,pressed);else game?.key(key,pressed);
  });
}

function choose(system){
  if(loaded||loading)return;
  selected=system;
  for(const btn of $('systems').children) btn.setAttribute('aria-pressed',String(btn.dataset.system===system.id));
  input.value='';input.accept=system.extensions.map(x=>'.'+x).join(',');
  $('play').disabled=true;
  $('rom-label').textContent=`${system.label} ROM 파일`;
  $('rom-help').textContent= system.id==='chip8' ? '권리를 보유한 .ch8 / .c8 ROM을 선택하세요 (최대 3,584바이트).' : system.id==='mgba-gb' ? '권리를 보유한 .gb / .gbc ROM을 선택하세요 (최대 8MiB). 게임 데이터는 공유기로 전송되지 않습니다.' : system.id==='nes' ? '권리를 보유한 .nes 파일을 선택하세요 (최대 8MiB). 게임 데이터는 공유기로 전송되지 않습니다.' : '권리를 보유한 .gba ROM을 선택하세요 (최대 32MiB). BIOS는 필요하지 않으며 ROM은 전송되지 않습니다.';
  $('control-help').textContent=system.id==='chip8' ? '1234 / QWER / ASDF / ZXCV · 모바일 터치 키패드' : '방향키 이동 · X(A) / Z(B) · Enter(START) / Shift(SELECT)' + (system.id==='mgba' ? ' · A(L) / S(R)' : '') + ' · 모바일 터치 지원';
  $('demo').disabled=system.id!=='chip8';
  notice.classList.add('hidden');
}
for(const system of SYSTEMS){
  const btn=document.createElement('button');btn.type='button';btn.className='system';btn.dataset.system=system.id;
  const icon=document.createElement('div');icon.className='system-icon';icon.textContent=system.icon;
  const title=document.createElement('strong');title.textContent=system.label;
  const description=document.createElement('small');description.textContent=system.description;
  btn.append(icon,title,description);btn.onclick=()=>choose(system);$('systems').appendChild(btn);
}
choose(SYSTEMS[0]);
input.onchange=()=>{
  const file=input.files[0];if(!file){$('play').disabled=true;return;}
  const detected=detectSystem(file.name);
  if(detected&&detected!==selected){announce('선택한 플랫폼과 파일 형식이 다릅니다. 상단에서 게임 플랫폼을 변경해 주세요.');$('play').disabled=true;return;}
  const error=validateRom(file,selected);$('play').disabled=Boolean(error);
  if(error)announce(error);else notice.classList.add('hidden');
};
$('play').onclick=async()=>{
  if(loading)return;
  const file=input.files[0];const error=validateRom(file,selected);
  if(error){announce(error);return;}
  loading=true;$('play').disabled=true;
  try{
    const bytes=new Uint8Array(await file.arrayBuffer());
    if(selected.id==='chip8')playChip8(bytes,file.name);
    else if(selected.id==='nes')await playNes(bytes,file.name);
    else await playMgba(bytes,file.name);
  }catch(error){announce(error.message);}
  finally{loading=false;if(!loaded)$('play').disabled=false;}
};
$('demo').onclick=()=>{if(selected.id==='chip8')playChip8(DEMO_ROM,'내장 데모 2026');};
$('sound').onclick=async()=>{
  if(selected.id!=='nes'||!game)return;
  try{await game.enableAudio();$('sound').textContent='♫ 사운드 켜짐';$('sound').disabled=true;}
  catch(error){announce(error.message);}
};
$('toggle').onclick=()=>{
  if(!loaded)return;
  if(running){stop();void persistBattery();}
  else{running=true;last=0;clock=0;game?.resume?.();$('toggle').textContent='Ⅱ 일시정지';frame=requestAnimationFrame(drawLoop);}
};
async function exitGame(){activeController?.releaseAll();stop();await persistBattery();await fullscreen.exit();game?.destroy();window.location.reload();}
$('reset').onclick=exitGame;$('return').onclick=exitGame;
function onKey(event,pressed){
  if(event.target instanceof HTMLInputElement || !loaded)return;
  const name=event.key.toLowerCase();
  const key=selected.id==='chip8'?KEYMAP.get(name):GBKEY.get(name);
  if(key===undefined)return;
  event.preventDefault();
  if(selected.id==='chip8')chip8.key(key,pressed);else game?.key(key,pressed);
}
window.addEventListener('keydown',event=>onKey(event,true));
window.addEventListener('keyup',event=>onKey(event,false));
window.addEventListener('blur',()=>{activeController?.releaseAll();chip8.keys.fill(0);if(game)for(const key of HANDHELD_KEYS)game.key(key,false);});
document.addEventListener('visibilitychange',()=>{if(document.hidden){activeController?.releaseAll();stop();void persistBattery();}});
paintChip8();
