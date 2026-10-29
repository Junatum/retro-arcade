import test from 'node:test';
import assert from 'node:assert/strict';
import { renderController, CHIP8_KEYBOARD, CHIP8_MATRIX, HANDHELD_KEYS } from '../web/controller.js';

class FakeElement extends EventTarget {
  constructor(tag, doc) {
    super(); this.tagName=tag;this.ownerDocument=doc;this.children=[];this.attributes={};this.dataset={};this.textContent='';this.className='';
    const classes=new Set();
    this.classList={add:key=>classes.add(key),remove:key=>classes.delete(key),contains:key=>classes.has(key)};
  }
  setAttribute(name,value){this.attributes[name]=value;}
  appendChild(child){this.children.push(child);return child;}
  replaceChildren(...children){this.children=children;}
  setPointerCapture(){}
}
function root(){const doc={createElement(tag){return new FakeElement(tag,doc);}};return new FakeElement('div',doc);}
function flatten(element){return [element,...element.children.flatMap(flatten)];}
function buttons(element){return flatten(element).filter(item=>item.tagName==='button');}
function hit(button, type, pointerId=1){
  const event=new Event(type,{cancelable:true});
  Object.defineProperties(event,{pointerId:{value:pointerId},pointerType:{value:'touch'},button:{value:0}});
  button.dispatchEvent(event);
  return event;
}
test('GB/GBC has a cross-shaped D-pad, diagonally placed B/A and central SELECT/START',()=>{
  const el=root(), records=[];
  renderController(el,'mgba-gb',(key,down)=>records.push([key,down]));
  assert.match(el.className,/keypad--handheld/);
  const list=buttons(el);
  assert.deepEqual(list.map(b=>b.dataset.position),['up','left','down','right','b','a','select','start']);
  assert.deepEqual(list.map(b=>b.textContent),['↑','←','↓','→','B','A','SELECT','START']);
  const grid=flatten(el).find(b=>b.className==='controller-dpad');
  assert.ok(grid.children.some(child=>child.className==='controller-dpad-center'));
  assert.ok(!list.some(b=>b.dataset.position==='l'||b.dataset.position==='r'));
  hit(list[0],'pointerdown'); hit(list[0],'pointerup');
  assert.deepEqual(records,[['up',true],['up',false]]);
});
test('GBA adds L and R shoulder buttons, no difference to base gameplay keys',()=>{
  const el=root();renderController(el,'mgba',()=>{});
  assert.deepEqual(buttons(el).map(b=>b.dataset.position),['l','r','up','left','down','right','b','a','select','start']);
  assert.deepEqual(HANDHELD_KEYS,['up','left','down','right','b','a','select','start','l','r']);
});
test('CHIP-8 keeps the authentic 1 2 3 C / 4 5 6 D / 7 8 9 E / A 0 B F keypad',()=>{
  const el=root(), records=[];
  renderController(el,'chip8',(key,down)=>records.push([key,down]));
  assert.match(el.className,/keypad--chip8/);
  assert.equal(CHIP8_KEYBOARD.length,16);
  assert.equal(CHIP8_MATRIX.length,16);
  assert.deepEqual(buttons(el).map(b=>b.textContent), '123C456D789EA0BF'.split(''));
  assert.equal(buttons(el)[3].attributes['aria-label'],'CHIP-8 C 키 (키보드 4)');
  hit(buttons(el)[3],'pointerdown');hit(buttons(el)[3],'pointerup');
  assert.deepEqual(records,[[12,true],[12,false]]);
});
test('two fingers can hold different directions, release independently and cancel cleanly',()=>{
  const el=root(),records=[];
  const ctl=renderController(el,'mgba',(key,down)=>records.push([key,down]));
  const list=buttons(el);
  const left=list.find(b=>b.dataset.position==='left');
  const a=list.find(b=>b.dataset.position==='a');
  hit(left,'pointerdown',11);hit(a,'pointerdown',22);
  assert.deepEqual(records,[['left',true],['a',true]]);
  hit(left,'pointercancel',11);hit(a,'lostpointercapture',22);
  assert.deepEqual(records,[['left',true],['a',true],['left',false],['a',false]]);
  hit(a,'pointerup',22);
  assert.equal(records.length,4);
  hit(left,'pointerdown',17);hit(a,'pointerdown',18);
  ctl.releaseAll();ctl.releaseAll();
  assert.deepEqual(records.slice(-4),[['left',true],['a',true],['left',false],['a',false]]);
});
test('one key remains pressed until both touches are released',()=>{
  const el=root(),records=[];
  renderController(el,'mgba-gb',(key,down)=>records.push([key,down]));
  const a=buttons(el).find(b=>b.dataset.position==='a');
  hit(a,'pointerdown',1);hit(a,'pointerdown',2);
  hit(a,'pointerup',1);
  assert.deepEqual(records,[['a',true]]);
  hit(a,'pointerup',2);
  assert.deepEqual(records,[['a',true],['a',false]]);
});
test('NES controller matches original Famicom/NES layout with no L/R',()=>{
  const el=root(),records=[];
  renderController(el,'nes',(key,down)=>records.push([key,down]));
  assert.match(el.attributes['aria-label'],/NES \/ Famicom/);
  assert.deepEqual(buttons(el).map(b=>b.dataset.position),['up','left','down','right','b','a','select','start']);
  const a=buttons(el).find(b=>b.dataset.position==='a');
  hit(a,'pointerdown');hit(a,'pointerup');
  assert.deepEqual(records,[['a',true],['a',false]]);
});
test('Sega 8-bit uses two buttons; Mega Drive has six buttons and MODE',()=>{
  const el=root();renderController(el,'gearsystem-gg',()=>{});
  assert.deepEqual(buttons(el).map(b=>b.dataset.position),['up','left','down','right','b','a','select','start']);
  const events=[];renderController(el,'blastem',(k,v)=>events.push([k,v]));
  assert.match(el.className,/keypad--megadrive/);
  assert.deepEqual(buttons(el).map(b=>b.dataset.position),
    ['up','left','down','right','x','y','z','a','b','c','mode','start']);
  hit(buttons(el).find(b=>b.dataset.position==='c'),'pointerdown');
  hit(buttons(el).find(b=>b.dataset.position==='c'),'pointerup');
  assert.deepEqual(events,[['c',true],['c',false]]);
});

test('Arcade controller includes coins and one-player start without other BIOS keys',()=>{
  const el=root(),events=[];
  renderController(el,'mame',(key,on)=>events.push([key,on]));
  assert.deepEqual(buttons(el).map(b=>b.textContent),['↑','←','↓','→','B','A','COIN','1P START']);
  const coin=buttons(el).find(b=>b.textContent==='COIN');
  hit(coin,'pointerdown');hit(coin,'pointerup');
  assert.deepEqual(events,[['coin',true],['coin',false]]);
});
