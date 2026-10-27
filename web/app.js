/* SmartSafeHub Retro Arcade — GPL-3.0-or-later; entirely local browser playback. */
import { Chip8, DISPLAY_WIDTH, DISPLAY_HEIGHT } from './chip8.js';
import { DEMO_ROM, DEMO_TITLE, DEMO_CONTROLS, DEMO_FINISHED_PC, DEMO_WIN_SCORE } from './demo.js?v=0.1.0-r5-p4';
import { SYSTEMS, detectSystem, validateRom } from './systems.js?v=0.1.0-r5';
import { romStorageKey, batteryRead, batteryWrite } from './battery-store.js?v=0.1.0-r5';
import { MgbaPlayer } from './mgba-player.js';
import { JsnesPlayer } from './jsnes-player.js';
import { setupFullscreen } from './fullscreen.js';
import { renderController, CHIP8_KEYBOARD, CHIP8_MATRIX, HANDHELD_KEYS } from './controller.js?v=0.1.0-r5';
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
let saveKey=null,framesSinceSave=0,loading=false,activeController=null,demoActive=false;
function announce(message,ok=false){notice.textContent=message;notice.classList.toggle('ok',ok);notice.classList.remove('hidden');}
function paintChip8(){
  if(canvas.width!==DISPLAY_WIDTH||canvas.height!==DISPLAY_HEIGHT){canvas.width=DISPLAY_WIDTH;canvas.height=DISPLAY_HEIGHT;}
  const image=ctx.createImageData(DISPLAY_WIDTH,DISPLAY_HEIGHT);
  for(let i=0;i<chip8.pixels.length;i++){
    const j=i*4,lit=Boolean(chip8.pixels[i]);
    const x=i%DISPLAY_WIDTH, y=Math.floor(i/DISPLAY_WIDTH);
    // Only the bundled demo uses a right-side player accent. External CHIP-8
    // ROMs retain the standard monochrome palette.
    const playerPixel=demoActive && lit && x>=58 && x<=60 && y>=chip8.v[2] && y<chip8.v[2]+6;
    // Decorative court walls: browser-only overlay, never modifies ROM pixels.
    const wallPixel=demoActive && (y===6 || y===30 || ((x===0 || x===63) && y>=7 && y<=29));
    image.data[j]=wallPixel?107:playerPixel?255:lit?185:10;
    image.data[j+1]=wallPixel?162:playerPixel?186:lit?251:14;
    image.data[j+2]=wallPixel?232:playerPixel?110:lit?194:26;
    image.data[j+3]=255;
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
      if(demoActive && chip8.v[14] && chip8.pc===DEMO_FINISHED_PC){finishDemo();return;}
    } else if(game){
      let count=0;
      while(clock>=1000/59.7275 && count++<5){clock-=1000/59.7275;game.frame();framesSinceSave++;}
      if(framesSinceSave>=1800){framesSinceSave=0;void persistBattery();}
    }
  }catch(error){stop(`실행 중 오류: ${error.message}`);return;}
  frame=requestAnimationFrame(drawLoop);
}
function stop(reason){running=false;cancelAnimationFrame(frame);game?.pause?.();$('toggle').textContent='▶ 계속';if(reason)announce(reason);}
function finishDemo(){
  activeController?.releaseAll();
  stop();
  const won=chip8.v[14]===1;
  $('demo-result-title').textContent=won?'승리!':'패배!';
  $('demo-result-score').textContent=`컴퓨터 ${chip8.v[9]} : ${chip8.v[8]} 플레이어 · ${DEMO_WIN_SCORE}점 선승`;
  $('demo-result').classList.remove('hidden');
  $('demo-result').classList.toggle('demo-result--win',won);
  $('toggle').disabled=true;
  $('toggle').textContent='경기 종료';
}
function showPlayer(system,label){
  loaded=true;running=true;last=0;clock=0;framesSinceSave=0;
  $('intro').classList.add('hidden');$('system-library').classList.add('hidden');$('load-area').classList.add('hidden');
  $('player-section').classList.remove('hidden');
  $('player-title').textContent=`${system.label} · ${label}`;
  $('toggle').textContent='Ⅱ 일시정지';$('toggle').disabled=false;notice.classList.add('hidden');
  $('demo-result').classList.add('hidden');$('demo-result').classList.remove('demo-result--win');
  $('sound').classList.toggle('hidden', system.id!=='nes');
  const demoControls=$('demo-controls');
  demoControls.textContent=`${DEMO_CONTROLS} · 오른쪽 주황색 패들이 플레이어입니다. 왼쪽은 컴퓨터이며, 위쪽은 양쪽 점수입니다.`;
  demoControls.classList.toggle('hidden',!demoActive);
  $('demo-roles').classList.toggle('hidden',!demoActive);
  renderKeypad();
  frame=requestAnimationFrame(drawLoop);
  $('player-section').scrollIntoView({block:'start',behavior:'smooth'});
}
async function persistBattery(){if(game&&saveKey){const bytes=game.battery();if(bytes)await batteryWrite(saveKey,bytes);}}
function playChip8(bytes,label,isDemo=false){
  cancelAnimationFrame(frame);chip8.load(bytes);game=null;saveKey=null;demoActive=isDemo;
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
  $('control-help').textContent=system.id==='chip8' ? DEMO_CONTROLS + ' · 외부 CHIP-8 ROM은 게임마다 조작이 다릅니다.' : '방향키 이동 · X(A) / Z(B) · Enter(START) / Shift(SELECT)' + (system.id==='mgba' ? ' · A(L) / S(R)' : '') + ' · 모바일 터치 지원';
  const hasDemo=system.id==='chip8';
  $('demo').disabled=!hasDemo;
  $('demo').classList.toggle('hidden',!hasDemo);
  $('load-buttons').classList.toggle('buttons--single',!hasDemo);
  notice.classList.add('hidden');
}
// Original inline SVG silhouettes: no external requests, trademark assets or icon dependencies.
// The system labels remain visible and SVGs are decorative only.
const PLATFORM_ICONS = Object.freeze({
  chip8: '<svg viewBox="0 0 48 48" aria-hidden="true" focusable="false"><rect x="12" y="12" width="24" height="24" rx="5"/><path d="M17 7v5m7-5v5m7-5v5M17 36v5m7-5v5m7-5v5M7 17h5m-5 7h5m-5 7h5m24-14h5m-5 7h5m-5 7h5"/><path d="M19 20h10m-10 5h10m-10 5h6"/></svg>',
  'mgba-gb': '<svg viewBox="0 0 48 48" aria-hidden="true" focusable="false"><rect x="14" y="4" width="20" height="40" rx="6"/><rect x="18" y="10" width="12" height="14" rx="2"/><path d="M19 31h8m-4-4v8"/><circle cx="29" cy="30" r="1.5"/><circle cx="31" cy="34" r="1.5"/><path d="M21 39h6"/></svg>',
  mgba: '<svg viewBox="0 0 48 48" aria-hidden="true" focusable="false"><path d="M11 15h26c4 0 6 4 6 8v9c0 5-3 7-8 7H13c-5 0-8-2-8-7v-9c0-4 2-8 6-8Z"/><rect x="17" y="17" width="14" height="12" rx="2"/><path d="M10 12h10m8 0h10M13 31h7m-3.5-3.5v7"/><circle cx="34" cy="30" r="1.6"/><circle cx="37" cy="33.5" r="1.6"/></svg>',
  nes: '<svg viewBox="0 0 48 48" aria-hidden="true" focusable="false"><rect x="5" y="17" width="38" height="17" rx="6"/><path d="M13 25h9m-4.5-4.5v9"/><circle cx="32" cy="23.5" r="2"/><circle cx="36" cy="27.5" r="2"/><path d="M22 29h3m2-2h3"/></svg>',
});

for(const system of SYSTEMS){
  const btn=document.createElement('button');btn.type='button';btn.className='system';btn.dataset.system=system.id;
  const icon=document.createElement('div');icon.className='system-icon';icon.innerHTML=PLATFORM_ICONS[system.id];
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
$('demo').onclick=()=>{if(selected.id==='chip8')playChip8(DEMO_ROM,DEMO_TITLE,true);};
$('demo-replay').onclick=()=>{if(demoActive)playChip8(DEMO_ROM,DEMO_TITLE,true);};
$('sound').onclick=async()=>{
  if(selected.id!=='nes'||!game)return;
  try{await game.enableAudio();$('sound').textContent='♫ 사운드 켜짐';$('sound').disabled=true;}
  catch(error){announce(error.message);}
};
$('toggle').onclick=()=>{
  if(!loaded||(demoActive && chip8.v[14]))return;
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
