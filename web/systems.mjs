// Offline CHIP-8, JSNES (NES/Famicom), and mGBA (GB/GBC/GBA).
export const SYSTEMS = Object.freeze([
  Object.freeze({id:'chip8', label:'CHIP-8', extensions:['ch8','c8'], icon:'8BIT', description:'내장 가상 콘솔', maxSize:3584}),
  Object.freeze({id:'mgba-gb', label:'Game Boy / Color', extensions:['gb','gbc'], icon:'GB', description:'mGBA · 로컬 WASM', maxSize:8*1024*1024}),
  Object.freeze({id:'mgba', label:'Game Boy Advance', extensions:['gba'], icon:'GBA', description:'mGBA · 로컬 WASM', maxSize:32*1024*1024}),
  Object.freeze({id:'nes', label:'NES / Famicom', extensions:['nes'], icon:'NES', description:'JSNES 2.1.0 · 로컬 JavaScript', maxSize:8*1024*1024}),
]);
export function extension(name) { return String(name || '').trim().toLowerCase().split('.').pop(); }
export function detectSystem(name) { return SYSTEMS.find(s => s.extensions.includes(extension(name))) || null; }
export function validateRom(file, system) {
  if (!SYSTEMS.includes(system)) return '플랫폼을 먼저 선택해 주세요.';
  if (!file || !file.size) return '게임 파일을 선택해 주세요.';
  if (!system.extensions.includes(extension(file.name))) return `${system.label} 파일(${system.extensions.map(x=>'.'+x).join(', ')})을 선택해 주세요.`;
  if (system.id==='mgba-gb' && file.size < 0x150) return 'GB/GBC ROM 파일이 너무 작거나 잘못되었습니다.';
  if (system.id==='mgba' && file.size < 0xC0) return 'GBA ROM 파일이 너무 작거나 잘못되었습니다.';
  if (system.id==='nes' && file.size < 16+16384) return 'NES ROM 파일이 너무 작거나 잘못되었습니다.';
  if (file.size > system.maxSize) return system.id === 'chip8' ? 'CHIP-8 ROM은 3,584바이트 이하만 지원합니다.' : system.id === 'mgba-gb' ? 'GB/GBC ROM은 8MiB 이하만 지원합니다.' : system.id === 'nes' ? 'NES ROM은 8MiB 이하만 지원합니다.' : 'GBA ROM은 32MiB 이하만 지원합니다.';
  return null;
}
