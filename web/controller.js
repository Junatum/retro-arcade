/* Local-only touch controller layouts; GPL-3.0-or-later. */
// The CHIP-8 hex keypad has a physical 4×4 arrangement, not a directional pad.
export const CHIP8_KEYBOARD = '1234qwerasdfzxcv';
export const CHIP8_MATRIX = Object.freeze([1, 2, 3, 12, 4, 5, 6, 13, 7, 8, 9, 14, 10, 0, 11, 15]);
export const HANDHELD_KEYS = Object.freeze(['up', 'left', 'down', 'right', 'b', 'a', 'select', 'start', 'l', 'r']);
export const SEGA_KEYS = Object.freeze([...HANDHELD_KEYS, 'c', 'x', 'y', 'z', 'mode']);

const DIRECTIONS = Object.freeze([
  {key:'up', label:'↑', position:'up', name:'위'},
  {key:'left', label:'←', position:'left', name:'왼쪽'},
  {key:'down', label:'↓', position:'down', name:'아래'},
  {key:'right', label:'→', position:'right', name:'오른쪽'},
]);
const FACE = Object.freeze([
  {key:'b', label:'B', position:'b', name:'B 버튼'},
  {key:'a', label:'A', position:'a', name:'A 버튼'},
]);
const SYSTEM = Object.freeze([
  {key:'select', label:'SELECT', position:'select', name:'SELECT 버튼'},
  {key:'start', label:'START', position:'start', name:'START 버튼'},
]);
const MEGA_FACE = Object.freeze([
  {key:'x',label:'X',position:'x',name:'X 버튼'},
  {key:'y',label:'Y',position:'y',name:'Y 버튼'},
  {key:'z',label:'Z',position:'z',name:'Z 버튼'},
  {key:'a',label:'A',position:'a',name:'A 버튼'},
  {key:'b',label:'B',position:'b',name:'B 버튼'},
  {key:'c',label:'C',position:'c',name:'C 버튼'},
]);
const SHOULDERS = Object.freeze([
  {key:'l', label:'L', position:'l', name:'L 어깨 버튼'},
  {key:'r', label:'R', position:'r', name:'R 어깨 버튼'},
]);

/** Build buttons with no dependencies or external assets; releaseAll prevents stuck inputs. */
export function renderController(root, systemId, press) {
  const doc = root.ownerDocument;
  const isChip8 = systemId === 'chip8';
  const isGba = systemId === 'mgba';
  const isNes = systemId === 'nes';
  const isMega = systemId === 'blastem';
  const isSega8 = systemId.startsWith('gearsystem-');
  const held = new Set();
  const releaseAll = () => {
    for (const release of [...held]) release();
  };
  root.replaceChildren();
  root.className = `keypad ${isChip8 ? 'keypad--chip8' : isMega ? 'keypad--handheld keypad--megadrive' : 'keypad--handheld'}`;
  root.setAttribute('aria-label', isChip8 ? 'CHIP-8 16키 터치 키패드' : `${isGba ? 'Game Boy Advance' : isNes ? 'NES / Famicom' : isMega ? 'Mega Drive / Genesis' : isSega8 ? 'Sega 8-bit' : 'Game Boy / Color'} 터치 컨트롤러`);

  function makeButton(item, groupClass) {
    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.className = `chip-key controller-key ${groupClass}`;
    btn.textContent = item.label;
    btn.setAttribute('aria-label', item.name);
    btn.dataset.position = item.position;
    const pointers = new Set();
    const release = () => {
      if (!pointers.size) return;
      pointers.clear();
      btn.classList.remove('is-pressed');
      held.delete(release);
      press(item.key, false);
    };
    const pointerEnd = event => {
      if (!pointers.delete(event.pointerId)) return;
      if (pointers.size === 0) {
        held.delete(release);
        btn.classList.remove('is-pressed');
        press(item.key, false);
      }
    };
    btn.addEventListener('pointerdown', event => {
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      event.preventDefault();
      if (pointers.has(event.pointerId)) return;
      if (pointers.size === 0) {
        press(item.key, true);
        btn.classList.add('is-pressed');
        held.add(release);
      }
      pointers.add(event.pointerId);
      try { btn.setPointerCapture(event.pointerId); } catch { /* synthetic/older browser */ }
    });
    for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) {
      btn.addEventListener(type, pointerEnd);
    }
    return btn;
  }
  function makeGroup(groupClass, items) {
    const group = doc.createElement('div');
    group.className = groupClass;
    for (const item of items) group.appendChild(makeButton(item, groupClass + '-key'));
    return group;
  }
  if (isChip8) {
    const items = CHIP8_MATRIX.map((key, i) => ({
      key, label:key.toString(16).toUpperCase(), name:`CHIP-8 ${key.toString(16).toUpperCase()} 키 (키보드 ${CHIP8_KEYBOARD[i].toUpperCase()})`, position:`key-${i}`,
    }));
    for (const item of items) root.appendChild(makeButton(item, 'chip8-key'));
    return {releaseAll};
  }
  if (isGba) root.appendChild(makeGroup('controller-shoulders', SHOULDERS));
  const main = doc.createElement('div');
  main.className = 'controller-main';
  const dpad = makeGroup('controller-dpad', DIRECTIONS);
  const center = doc.createElement('span');
  center.className = 'controller-dpad-center';
  center.setAttribute('aria-hidden', 'true');
  dpad.appendChild(center);
  main.appendChild(dpad);
  main.appendChild(makeGroup('controller-face', isMega ? MEGA_FACE : FACE));
  root.appendChild(main);
  root.appendChild(makeGroup('controller-meta', isMega ? [{key:'mode', label:'MODE', position:'mode', name:'MODE 버튼'}, SYSTEM[1]] : SYSTEM));
  return {releaseAll};
}
