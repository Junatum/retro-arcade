/* NES/Famicom JSNES 2.1.0 adapter — local ROM, canvas, gamepad and SRAM. */
import { NesAudio } from './nes-audio.mjs';

export const NES_WIDTH = 256;
export const NES_HEIGHT = 240;
export const NES_BUTTONS = Object.freeze({
  a: 'BUTTON_A', b: 'BUTTON_B', select: 'BUTTON_SELECT', start: 'BUTTON_START',
  up: 'BUTTON_UP', down: 'BUTTON_DOWN', left: 'BUTTON_LEFT', right: 'BUTTON_RIGHT',
});
export function validateNesBytes(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 16 + 16384 ||
      bytes[0] !== 0x4e || bytes[1] !== 0x45 || bytes[2] !== 0x53 || bytes[3] !== 0x1a) {
    throw new Error('유효한 NES/Famicom .nes ROM 파일을 선택해 주세요.');
  }
}

export class JsnesPlayer {
  static async create(canvas, loadCore = async () => {
    const [{default: NES}, {default: Controller}] = await Promise.all([
      import('./vendor/jsnes/src/nes.js'), import('./vendor/jsnes/src/controller.js'),
    ]);
    return {NES, Controller};
  }, audio = new NesAudio()) {
    const {NES, Controller} = await loadCore();
    return new JsnesPlayer(canvas, NES, Controller, audio);
  }
  constructor(canvas, NES, Controller, audio) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', {alpha: false});
    this.canvas.width = NES_WIDTH; this.canvas.height = NES_HEIGHT;
    this.image = this.ctx.createImageData(NES_WIDTH, NES_HEIGHT);
    this.buttons = Controller;
    this.audio = audio;
    this.sram = new Uint8Array(8192);
    this.dirty = false;
    this.core = new NES({
      emulateSound: true,
      sampleRate: 48000,
      onFrame: pixels => this.paint(pixels),
      onAudioSample: (l, r) => this.audio.push(l, r),
      onBatteryRamWrite: (address, value) => {
        if (address >= 0x6000 && address < 0x8000) {
          this.sram[address - 0x6000] = value;
          this.dirty = true;
        }
      },
    });
    this.active = false;
  }
  paint(pixels) {
    const out = this.image.data;
    for (let i = 0; i < NES_WIDTH * NES_HEIGHT; i++) {
      const color = pixels[i] >>> 0, p = i * 4;
      out[p] = (color >>> 16) & 255;
      out[p + 1] = (color >>> 8) & 255;
      out[p + 2] = color & 255;
      out[p + 3] = 255;
    }
    this.ctx.putImageData(this.image, 0, 0);
  }
  load(bytes) {
    validateNesBytes(bytes);
    this.core.loadROM(bytes);
    this.active = true;
    this.sram.fill(0); this.dirty = false;
    this.sram.set(this.core.cpu.mem.subarray(0x6000, 0x8000));
  }
  frame() { this.core.frame(); }
  key(key, pressed) {
    const code = this.buttons[NES_BUTTONS[key]];
    if (code === undefined) return;
    if (pressed) this.core.buttonDown(1, code);
    else this.core.buttonUp(1, code);
  }
  battery() {
    // Only persist cartridges that explicitly declare battery-backed RAM.
    if (!this.active || !this.core.rom?.batteryRam) return null;
    return this.core.cpu.mem.slice(0x6000, 0x8000);
  }
  restore(bytes) {
    if (!this.active || !this.core.rom?.batteryRam || !(bytes instanceof Uint8Array) || bytes.length !== 8192) return false;
    this.core.cpu.mem.set(bytes, 0x6000);
    this.sram.set(bytes);
    this.dirty = false;
    return true;
  }
  async enableAudio() {
    const enabled = await this.audio.enable();
    // The APU starts at 48kHz. In browsers with a different native audio
    // sample rate update JSNES to avoid long-term audio drift.
    if (enabled && this.core.papu && this.audio.sampleRate !== this.core.papu.sampleRate) {
      this.core.opts.sampleRate = this.audio.sampleRate;
      this.core.papu.sampleRate = this.audio.sampleRate;
      this.core.papu.sampleTimerMax = Math.floor(1024 * 1789772.5 / this.audio.sampleRate);
    }
    return enabled;
  }
  pause() { this.audio.pause(); }
  resume() { this.audio.resume(); }
  destroy() { this.audio.destroy(); this.active = false; this.core = null; }
}
