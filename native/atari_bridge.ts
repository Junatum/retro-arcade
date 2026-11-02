/* Retro Arcade integration; Copyright 2026 SmartSafeHub contributors; GPL-3.0-or-later.
 * Built together with the locally reviewed MIT mohrt/atari2600 core; no upstream
 * web frontend, telemetry, game catalog, sample ROMs or runtime fetches. */
import { Emulator } from './emulator';
import { Screen } from './render/screen';
import { WINDOW_LINES } from './render/frame-window';
import { ControllerPorts } from './io/controllers/ports';
import { Dir } from './io/controllers/types';
import { createCartridge, detectScheme } from './cart/detect';

const DIRECTIONS: Record<string, number> = {up:Dir.Up, down:Dir.Down, left:Dir.Left, right:Dir.Right};
const TYPE_NAMES: Record<string, any> = {Uint8Array, Int8Array, Uint16Array, Int16Array, Uint32Array, Int32Array, Float32Array, Float64Array};
function serialize(_k: string, value: unknown): unknown {
  if(ArrayBuffer.isView(value) && !(value instanceof DataView)) {
    const typed = value as unknown as {constructor:{name:string};length:number;[key:number]:number};
    return {$typed:typed.constructor.name, values:Array.from({length:typed.length},(_,i)=>typed[i])};
  }
  return value;
}
function deserialize(_k:string, value:any):any {
  if(value && typeof value==='object' && '$typed' in value) {
    const Ctor=TYPE_NAMES[value.$typed];
    if(!Ctor || !Array.isArray(value.values)) throw Error('Invalid save data');
    return new Ctor(value.values);
  }
  return value;
}
export class RetroAtariCore {
  readonly screen: Screen;
  readonly emulator: Emulator;
  readonly ports: ControllerPorts;
  private readonly held = new Set<string>();
  constructor(canvas:HTMLCanvasElement) {
    this.screen=new Screen(canvas, WINDOW_LINES.ntsc);
    this.emulator=new Emulator(this.screen);
    this.ports=new ControllerPorts(this.emulator.machine);
    this.ports.setType(0,'joystick');
    this.ports.setType(1,'joystick');
  }
  load(bytes:Uint8Array):void {
    if(!(bytes instanceof Uint8Array) || bytes.length < 2048 || bytes.length > 65536)
      throw Error('Atari 2600 ROM 크기가 올바르지 않습니다 (2KiB ~ 64KiB).');
    this.emulator.insertCartridge(createCartridge(bytes, detectScheme(bytes)));
    this.held.clear();this.updateKeys();
  }
  key(key:string, pressed:boolean):void {
    if(!['up','down','left','right','a','b','start','select'].includes(key))return;
    if(pressed)this.held.add(key);else this.held.delete(key);
    this.updateKeys();
  }
  private updateKeys():void {
    let dirs=0;
    for(const [name,mask] of Object.entries(DIRECTIONS))if(this.held.has(name))dirs|=mask;
    this.ports.players[0].set('arcade',{dirs,fire:this.held.has('a')||this.held.has('b')});
    this.ports.switches.buttons.set('arcade',this.held.has('start'),this.held.has('select'));
  }
  frame(ms:number):Float32Array {
    // Browser Gamepad API is read without any network activity or extra permissions.
    const pad=typeof navigator!=='undefined'&&navigator.getGamepads?.()?.[0];
    if(pad){
      const d=pad.buttons;
      const x=pad.axes?.[0]||0,y=pad.axes?.[1]||0;
      const dirs=(d[12]?.pressed||y<-0.4?Dir.Up:0)|(d[13]?.pressed||y>0.4?Dir.Down:0)|
        (d[14]?.pressed||x<-0.4?Dir.Left:0)|(d[15]?.pressed||x>0.4?Dir.Right:0);
      this.ports.players[0].set('gamepad',{dirs,fire:!!(d[0]?.pressed||d[1]?.pressed)});
      this.ports.switches.buttons.set('gamepad',!!d[9]?.pressed,!!d[8]?.pressed);
    }else{
      this.ports.players[0].clear('gamepad');
      this.ports.switches.buttons.set('gamepad',false,false);
    }
    this.ports.update(ms);
    this.emulator.run(ms);
    this.screen.present();
    return this.emulator.takeAudioSamples();
  }
  setAudioRate(rate:number):void {this.emulator.setAudioRate(rate);}
  save():Uint8Array {
    return new TextEncoder().encode(JSON.stringify({format:1, machine:this.emulator.machine.saveState()},serialize));
  }
  restore(bytes:Uint8Array):boolean {
    try{
      if(bytes.length>4*1024*1024)return false;
      const snapshot=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes),deserialize);
      if(snapshot.format!==1||!snapshot.machine||!['ntsc','pal','secam'].includes(snapshot.machine.tv))return false;
      this.emulator.machine.loadState(snapshot.machine);
      this.emulator.restoredTv(snapshot.machine.tv);
      return true;
    }catch{return false;}
  }
  resetTiming():void {this.emulator.resetTiming();}
  clearInputs():void {this.held.clear();this.ports.players[0].clear('gamepad');this.updateKeys();}
}
