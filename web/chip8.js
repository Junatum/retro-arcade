/*
 * SmartSafeHub Retro Arcade — original CHIP-8 interpreter.
 * Copyright (C) 2026 SmartSafeHub contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 * CHIP-8 interpreter with automatic modern Super CHIP-8 (SCHIP) support.
 */
export const MEMORY_SIZE = 4096;
export const ROM_START = 0x200;
export const DISPLAY_WIDTH = 64;
export const DISPLAY_HEIGHT = 32;
export const SCHIP_WIDTH = 128;
export const SCHIP_HEIGHT = 64;
export const MAX_ROM_BYTES = MEMORY_SIZE - ROM_START;
export const FONT = new Uint8Array([
  0xf0,0x90,0x90,0x90,0xf0, 0x20,0x60,0x20,0x20,0x70,
  0xf0,0x10,0xf0,0x80,0xf0, 0xf0,0x10,0xf0,0x10,0xf0,
  0x90,0x90,0xf0,0x10,0x10, 0xf0,0x80,0xf0,0x10,0xf0,
  0xf0,0x80,0xf0,0x90,0xf0, 0xf0,0x10,0x20,0x40,0x40,
  0xf0,0x90,0xf0,0x90,0xf0, 0xf0,0x90,0xf0,0x10,0xf0,
  0xf0,0x90,0xf0,0x90,0x90, 0xe0,0x90,0xe0,0x90,0xe0,
  0xf0,0x80,0x80,0x80,0xf0, 0xe0,0x90,0x90,0x90,0xe0,
  0xf0,0x80,0xf0,0x80,0xf0, 0xf0,0x80,0xf0,0x80,0x80,
]);

// Original 8x10 large font, generated from the GPLv3-owned 4x5 glyphs above.
// Every glyph pixel is doubled horizontally and vertically (no vendor fonts).
export const LARGE_FONT = new Uint8Array(Array.from({length: 100}, (_, index) => {
  const digit = Math.floor(index / 10), sourceRow = Math.floor((index % 10) / 2);
  const bits = FONT[digit * 5 + sourceRow];
  let expanded = 0;
  for (let col = 0; col < 4; col++) if (bits & (0x80 >> col)) expanded |= 0xc0 >> (col * 2);
  return expanded;
}));
const LARGE_FONT_START = 0xa0;

export class Chip8 {
  constructor(random = Math.random, {superchip = false} = {}) {
    this.random = random; this.preferSuperchip = Boolean(superchip); this.reset();
  }
  reset() {
    this.memory = new Uint8Array(MEMORY_SIZE);
    this.memory.set(FONT, 0x50);
    this.superchip = this.preferSuperchip;
    if (this.superchip) this.memory.set(LARGE_FONT, LARGE_FONT_START);
    this.v = new Uint8Array(16);
    this.stack = new Uint16Array(16);
    this.keys = new Uint8Array(16);
    this.width = DISPLAY_WIDTH; this.height = DISPLAY_HEIGHT;
    this.pixels = new Uint8Array(this.width * this.height);
    // SCHIP RPL user flags are VM-local; they do not leak across ROM loads.
    this.rpl = new Uint8Array(8);
    this.i = 0; this.pc = ROM_START; this.sp = 0;
    this.delay = 0; this.sound = 0;
    this.waitingForKey = null;
    this.halted = false;
    this.changed = true;
  }
  load(bytes) {
    if (!(bytes instanceof Uint8Array) || bytes.length === 0 || bytes.length > MAX_ROM_BYTES) {
      throw new Error(`CHIP-8 ROM은 1~${MAX_ROM_BYTES}바이트여야 합니다.`);
    }
    this.reset(); this.memory.set(bytes, ROM_START);
  }
  key(index, down) {
    if (!Number.isInteger(index) || index < 0 || index > 15) return;
    const pressed = Boolean(down);
    const newlyPressed = pressed && !this.keys[index];
    this.keys[index] = Number(pressed);
    if (newlyPressed && this.waitingForKey !== null) {
      this.v[this.waitingForKey] = index;
      this.waitingForKey = null;
    }
  }
  tick() { if (this.delay) this.delay--; if (this.sound) this.sound--; }
  enableSuperchip() {
    if (this.superchip) return;
    this.superchip = true;
    this.memory.set(LARGE_FONT, LARGE_FONT_START);
  }
  setResolution(hires) {
    this.width = hires ? SCHIP_WIDTH : DISPLAY_WIDTH;
    this.height = hires ? SCHIP_HEIGHT : DISPLAY_HEIGHT;
    // Modern SCHIP mode: clear framebuffer on resolution switch.
    this.pixels = new Uint8Array(this.width * this.height);
    this.changed = true;
  }
  scroll(dx, dy) {
    // Clip at each edge, never wrap old pixels into the newly exposed area.
    const next = new Uint8Array(this.pixels.length);
    for (let y = 0; y < this.height; y++) {
      const sy = y - dy;
      if (sy < 0 || sy >= this.height) continue;
      for (let x = 0; x < this.width; x++) {
        const sx = x - dx;
        if (sx >= 0 && sx < this.width) next[y * this.width + x] = this.pixels[sy * this.width + sx];
      }
    }
    this.pixels = next;
    this.changed = true;
  }
  step() {
    if (this.halted || this.waitingForKey !== null) return;
    if (this.pc < ROM_START || this.pc + 1 >= MEMORY_SIZE) throw Error('명령어 주소가 메모리 범위를 벗어났습니다.');
    const op = (this.memory[this.pc] << 8) | this.memory[this.pc + 1];
    this.pc += 2;
    const x = (op >> 8) & 0xf, y = (op >> 4) & 0xf;
    const n = op & 0xf, nn = op & 0xff, nnn = op & 0xfff;
    const vx = this.v[x], vy = this.v[y];
    // Activate SCHIP only when a real extension instruction executes, not
    // by scanning the ROM for byte patterns which might actually be data.
    // Explicit .sc8/.sch8 files start with SCHIP quirks enabled.
    if ((op & 0xfff0) === 0x00c0 && n > 0 ||
        [0x00fb, 0x00fc, 0x00fd, 0x00fe, 0x00ff].includes(op) ||
        (op >>> 12) === 0xd && n === 0 ||
        (op >>> 12) === 0xf && [0x30, 0x75, 0x85].includes(nn)) {
      this.enableSuperchip();
    }
    switch (op >>> 12) {
      case 0:
        if (op === 0x00e0) { this.pixels.fill(0); this.changed = true; }
        else if (op === 0x00ee) {
          if (!this.sp) throw Error('CHIP-8 스택 언더플로');
          this.pc = this.stack[--this.sp];
        } else if (this.superchip && op === 0x00fd) {
          this.halted = true;
        } else if (this.superchip && (op === 0x00fe || op === 0x00ff)) {
          this.setResolution(op === 0x00ff);
        } else if (this.superchip && op === 0x00fb) {
          this.scroll(4, 0);
        } else if (this.superchip && op === 0x00fc) {
          this.scroll(-4, 0);
        } else if (this.superchip && (op & 0xfff0) === 0x00c0 && n > 0) {
          this.scroll(0, n);
        } else throw Error(`지원하지 않는 CHIP-8 명령어: ${op.toString(16)}`);
        break;
      case 1: this.pc = nnn; break;
      case 2:
        if (this.sp >= this.stack.length) throw Error('CHIP-8 스택 오버플로');
        this.stack[this.sp++] = this.pc; this.pc = nnn; break;
      case 3: if (vx === nn) this.pc += 2; break;
      case 4: if (vx !== nn) this.pc += 2; break;
      case 5: if (n !== 0) throw Error('지원하지 않는 5xy 명령어'); if (vx === vy) this.pc += 2; break;
      case 6: this.v[x] = nn; break;
      case 7: this.v[x] = (vx + nn) & 255; break;
      case 8:
        switch (n) {
          case 0: this.v[x] = vy; break;
          case 1: this.v[x] = vx | vy; if (!this.superchip) this.v[15] = 0; break;
          case 2: this.v[x] = vx & vy; if (!this.superchip) this.v[15] = 0; break;
          case 3: this.v[x] = vx ^ vy; if (!this.superchip) this.v[15] = 0; break;
          case 4: this.v[x] = (vx + vy) & 255; this.v[15] = Number(vx + vy > 255); break;
          case 5: this.v[x] = (vx - vy) & 255; this.v[15] = Number(vx >= vy); break;
          case 6: this.v[x] = vx >>> 1; this.v[15] = vx & 1; break;
          case 7: this.v[x] = (vy - vx) & 255; this.v[15] = Number(vy >= vx); break;
          case 0xe: this.v[x] = (vx << 1) & 255; this.v[15] = vx >>> 7; break;
          default: throw Error('지원하지 않는 8xy 명령어');
        } break;
      case 9: if (n !== 0) throw Error('지원하지 않는 9xy 명령어'); if (vx !== vy) this.pc += 2; break;
      case 0xa: this.i = nnn; break;
      case 0xb: this.pc = nnn + this.v[this.superchip ? x : 0]; break;
      case 0xc: this.v[x] = (Math.floor(this.random() * 256) & 255) & nn; break;
      case 0xd: {
        // Modern SCHIP extends DXY0 to 16x16 sprites in both resolutions.
        // SCHIP clips pixels past the edge; classic CHIP-8 keeps its wrap mode.
        const wide = this.superchip && n === 0;
        const rows = wide ? 16 : n;
        const bytesPerRow = wide ? 2 : 1;
        if (this.i + rows * bytesPerRow > MEMORY_SIZE) throw Error('스프라이트 주소 오류');
        this.v[15] = 0;
        for (let row = 0; row < rows; row++) {
          const py = this.superchip ? vy + row : (vy + row) % this.height;
          if (py >= this.height) continue;
          for (let bit = 0; bit < (wide ? 16 : 8); bit++) {
            const sprite = this.memory[this.i + row * bytesPerRow + (bit >> 3)];
            if (!(sprite & (0x80 >> (bit & 7)))) continue;
            const px = this.superchip ? vx + bit : (vx + bit) % this.width;
            if (px >= this.width) continue;
            const pos = py * this.width + px;
            if (this.pixels[pos]) this.v[15] = 1;
            this.pixels[pos] ^= 1;
          }
        }
        this.changed = true;
        break;
      }
      case 0xe:
        if (vx > 15) throw Error('CHIP-8 키 코드 오류');
        if (nn === 0x9e && this.keys[vx]) this.pc += 2;
        else if (nn === 0xa1 && !this.keys[vx]) this.pc += 2;
        else if (nn !== 0x9e && nn !== 0xa1) throw Error('지원하지 않는 Ex 명령어');
        break;
      case 0xf:
        switch (nn) {
          case 0x07: this.v[x] = this.delay; break;
          case 0x0a: this.waitingForKey = x; break;
          case 0x15: this.delay = vx; break;
          case 0x18: this.sound = vx; break;
          case 0x1e: this.i = (this.i + vx) & 0xfff; break;
          case 0x29: this.i = 0x50 + (vx & 15) * 5; break;
          case 0x30:
            if (!this.superchip) throw Error('지원하지 않는 Fx 명령어: 30');
            if (vx > 9) throw Error('SCHIP 큰 글꼴은 0~9만 지원합니다.');
            this.i = LARGE_FONT_START + vx * 10; break;
          case 0x75:
          case 0x85:
            if (!this.superchip) throw Error(`지원하지 않는 Fx 명령어: ${nn.toString(16)}`);
            if (x > 7) throw Error('SCHIP RPL 플래그 범위 오류 (V0~V7)');
            for (let j = 0; j <= x; j++) {
              if (nn === 0x75) this.rpl[j] = this.v[j];
              else this.v[j] = this.rpl[j];
            }
            break;
          case 0x33:
            if (this.i + 2 >= MEMORY_SIZE) throw Error('BCD 메모리 범위 오류');
            this.memory[this.i] = Math.floor(vx / 100);
            this.memory[this.i + 1] = Math.floor(vx / 10) % 10;
            this.memory[this.i + 2] = vx % 10;
            break;
          case 0x55:
          case 0x65:
            if (this.i + x >= MEMORY_SIZE) throw Error('레지스터 저장 범위 오류');
            for (let j=0;j<=x;j++) {
              if (nn === 0x55) this.memory[this.i + j] = this.v[j];
              else this.v[j] = this.memory[this.i + j];
            } break;
          default: throw Error(`지원하지 않는 Fx 명령어: ${nn.toString(16)}`);
        } break;
      default: throw Error(`지원하지 않는 명령어: ${op.toString(16)}`);
    }
  }
}
