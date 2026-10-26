/* SmartSafeHub Retro Arcade UI — GPL-3.0-or-later; all execution stays inside browser. */
import { Chip8, DISPLAY_WIDTH, DISPLAY_HEIGHT } from './chip8.mjs';
import { DEMO_ROM } from './demo.mjs';
import { SYSTEMS, detectSystem, validateRom } from './systems.mjs';
const $ = id => document.getElementById(id);
const input = $('rom-file');
const notice = $('notice');
const stage = $('game');
const canvas = document.createElement('canvas');
canvas.width = DISPLAY_WIDTH; canvas.height = DISPLAY_HEIGHT;
canvas.setAttribute('aria-label', 'CHIP-8 게임 화면');
stage.appendChild(canvas);
const ctx = canvas.getContext('2d', { alpha: false });
const machine = new Chip8();
const controls = '1234qwerasdfzxcv';
const layout = [0x1,0x2,0x3,0xc,0x4,0x5,0x6,0xd,0x7,0x8,0x9,0xe,0xa,0x0,0xb,0xf];
const KEYMAP = new Map([...controls].map((key,index)=>[key,layout[index]]));
let running=false, loaded=false, frame=0, last=0, clock=0, selected=SYSTEMS[0];
function announce(message, ok=false) {
  notice.textContent = message;
  notice.classList.toggle('ok', ok); notice.classList.remove('hidden');
}
function paint() {
  const img = ctx.createImageData(DISPLAY_WIDTH, DISPLAY_HEIGHT);
  for (let pixel=0;pixel<machine.pixels.length;pixel++) {
    const lit = Boolean(machine.pixels[pixel]);
    const index = pixel * 4;
    img.data[index] = lit?185:10;
    img.data[index+1] = lit?251:14;
    img.data[index+2] = lit?194:26;
    img.data[index+3] = 255;
  }
  ctx.putImageData(img,0,0);
  machine.changed = false;
}
function halt(reason) { running=false; $('toggle').textContent='▶ 계속'; if(reason) announce(reason); }
function tick(time) {
  if(!running) return;
  const delta = Math.min(100, time - (last || time)); last=time;
  clock += delta;
  // Timer/display updates are 60Hz; interpreter runs at about 720 instructions/second.
  let count=0;
  try {
    while(clock >= 1000/60 && count++ < 6) {
      clock -= 1000/60;
      for(let i=0;i<12;i++) machine.step();
      machine.tick();
    }
  } catch(error) { halt(`실행 중 오류: ${error.message}`); return; }
  if(machine.changed) paint();
  frame=requestAnimationFrame(tick);
}
function start(bytes, name) {
  cancelAnimationFrame(frame);
  machine.load(bytes);
  loaded=true; running=true; last=0; clock=0;
  $('intro').classList.add('hidden'); $('load-area').classList.add('hidden');
  $('player-section').classList.remove('hidden');
  $('player-title').textContent = `CHIP-8 · ${name}`;
  $('toggle').textContent = 'Ⅱ 일시정지';
  notice.classList.add('hidden'); paint();
  frame = requestAnimationFrame(tick);
  $('player-section').scrollIntoView({block:'start',behavior:'smooth'});
}
for (const system of SYSTEMS) {
  const btn=document.createElement('button'); btn.type='button';
  btn.className='system'; btn.dataset.system=system.id;
  btn.setAttribute('aria-pressed','true');
  const icon=document.createElement('div');icon.className='system-icon'; icon.textContent=system.icon;
  const title=document.createElement('strong'); title.textContent=system.label;
  const desc=document.createElement('small'); desc.textContent=system.description;
  btn.append(icon,title,desc); btn.onclick=()=>{selected=system;}; $('systems').appendChild(btn);
}
input.onchange=()=>{
  $('play').disabled=!input.files.length;
  if(input.files.length) {
    const system=detectSystem(input.files[0].name);
    const error=validateRom(input.files[0],system || selected);
    if(error)announce(error);
    else notice.classList.add('hidden');
  }
};
$('play').onclick=async()=>{
  const file=input.files[0];
  const error=validateRom(file,selected);
  if(error){ announce(error); return; }
  try { start(new Uint8Array(await file.arrayBuffer()),file.name); }
  catch(err){ announce(err.message); }
};
$('demo').onclick=()=>start(DEMO_ROM,'내장 데모 2026');
$('toggle').onclick=()=>{
  if(!loaded) return;
  if(running){cancelAnimationFrame(frame); halt();}
  else {running=true;last=0;clock=0;$('toggle').textContent='Ⅱ 일시정지';frame=requestAnimationFrame(tick);}
};
$('reset').onclick=()=>window.location.reload();
$('return').onclick=()=>window.location.reload();
function onKey(event, pressed) {
  if(event.target instanceof HTMLInputElement) return;
  const key=KEYMAP.get(event.key.toLowerCase());
  if(key===undefined)return;
  event.preventDefault(); machine.key(key,pressed);
}
window.addEventListener('keydown',event=>onKey(event,true));
window.addEventListener('keyup',event=>onKey(event,false));
window.addEventListener('blur',()=>{machine.keys.fill(0);});
for(let i=0;i<16;i++) {
  const code=layout[i]; const key=controls[i];
  const btn=document.createElement('button'); btn.type='button'; btn.className='chip-key';
  btn.textContent=`${code.toString(16).toUpperCase()} (${key.toUpperCase()})`;
  btn.setAttribute('aria-label',`CHIP-8 키 ${code.toString(16).toUpperCase()}`);
  btn.addEventListener('pointerdown',event=>{event.preventDefault();machine.key(code,true);btn.setPointerCapture(event.pointerId);});
  for (const kind of ['pointerup','pointercancel','lostpointercapture']) btn.addEventListener(kind,()=>machine.key(code,false));
  $('keypad').appendChild(btn);
}
paint();
