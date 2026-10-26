// SmartSafeHub Retro Arcade platform registry — only included/functional runtimes.
export const SYSTEMS = Object.freeze([
  { id: 'chip8', label: 'CHIP-8', extensions: ['ch8', 'c8'], icon: '8BIT', description: '초경량 8비트 가상 콘솔' },
]);
export function extension(name) { return String(name || '').trim().toLowerCase().split('.').pop(); }
export function detectSystem(name) { return SYSTEMS.find(s => s.extensions.includes(extension(name))) || null; }
export function validateRom(file, system) {
  if (!SYSTEMS.includes(system)) return '플랫폼을 먼저 선택해 주세요.';
  if (!file || !file.size) return '게임 파일을 선택해 주세요.';
  if (file.size > 3584) return 'CHIP-8 ROM은 3,584바이트 이하만 지원합니다.';
  if (!system.extensions.includes(extension(file.name))) return '.ch8 또는 .c8 게임 파일만 사용할 수 있습니다.';
  return null;
}
