// Original demo written for Retro Arcade. Draws CHIP-8 glyphs '2026' and holds the screen.
// CHIP-8 font is built into this project's interpreter; no third-party ROM is included.
const words = [
  0x00e0,0x6008,0x610e,0x6202,0xf229,0xd015, // '2'
  0x6018,0x6200,0xf229,0xd015,               // '0'
  0x6028,0x6202,0xf229,0xd015,               // '2'
  0x6038,0x6206,0xf229,0xd015,               // '6'
  0x1224,                                    // infinite loop at 0x224
];
export const DEMO_ROM = Uint8Array.from(words.flatMap(w => [w >>> 8, w & 255]));
