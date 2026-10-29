/* Local, isolated arcade loader. ROM bytes arrive from the same-origin parent only.
 * The pinned MAME 0.289 runtime exports FS_createPath / FS_createDataFile,
 * not Module.FS.  Keep the fallback for other compatible FS exports.
 * No ROMs are fetched from a server; only mame.js/mame.wasm are loaded locally. */
const SYSTEMS = Object.freeze({ 'pacman.zip': 'pacman', 'galaxian.zip': 'galaxian' });
let started = false;
let moduleRef = null;
const notify = (type, message = '') => window.parent.postMessage({mame:type,message}, location.origin);
export function driverName(filename) {
  return Object.hasOwn(SYSTEMS, String(filename).toLowerCase()) ? SYSTEMS[filename.toLowerCase()] : null;
}
/** Store the explicitly selected local ROM before the MAME main() call.
 * MAME 0.289 exposes legacy file helpers, not necessarily Module.FS. */
export function installRom(module, driver, contents) {
  if (!['pacman', 'galaxian'].includes(driver) || !(contents instanceof Uint8Array))
    throw new Error('지원하지 않는 아케이드 ROM입니다.');
  if (typeof module?.FS_createPath === 'function' &&
      typeof module?.FS_createDataFile === 'function') {
    module.FS_createPath('/', 'roms', true, true);
    module.FS_createDataFile('/roms', driver + '.zip', contents, true, false, true);
    return;
  }
  const fs = module?.FS;
  if (fs && typeof fs.mkdir === 'function' && typeof fs.writeFile === 'function') {
    try { fs.mkdir('/roms'); }
    catch (error) { if (error?.code !== 'EEXIST' && error?.errno !== 20) throw error; }
    fs.writeFile('/roms/' + driver + '.zip', contents);
    return;
  }
  throw new Error('아케이드 ROM 메모리 파일시스템 API가 없습니다. MAME 빌드 출력을 확인하세요.');
}
export function makeConfiguration(filename, contents, canvas, onReady, onError) {
  const driver = driverName(filename);
  if (!driver || !(contents instanceof Uint8Array) || contents.length < 22 || contents.length > 12*1024*1024 || contents[0]!==0x50 || contents[1]!==0x4b || contents[2]!==3 || contents[3]!==4)
    throw new Error('허용되지 않은 아케이드 ROM 파일입니다.');
  return {
    canvas,
    arguments:[driver,'-rompath','/roms','-skip_gameinfo','-noreadconfig','-nowriteconfig'],
    locateFile: name => new URL(name.endsWith('.wasm')?'./mame.wasm':'./'+name, import.meta.url).href,
    preRun:[function() {
      installRom(moduleRef, driver, contents);
    }],
    onRuntimeInitialized:onReady,
    onAbort:reason=>onError('아케이드 엔진 실행 실패: '+reason),
    printErr:line=>{ if (/error|fatal|missing|not found/i.test(String(line))) onError(String(line).slice(0,280)); },
    setStatus:()=>{},
  };
}
function injectScript() {
  const tag = document.createElement('script');
  tag.src = './mame.js';
  tag.onerror = () => notify('error', 'MAME 실행 파일이 없습니다. 로컬 빌드 후 설치해야 합니다.');
  document.head.appendChild(tag);
}
function keyEvent(code, pressed) {
  const keys = {up:'ArrowUp',down:'ArrowDown',left:'ArrowLeft',right:'ArrowRight',a:'Control',b:'Alt',coin:'5',start:'1',pause:'p'};
  const key = keys[code];
  if (!key) return;
  const event = new KeyboardEvent(pressed?'keydown':'keyup', {key,code:key==='Control'?'ControlLeft':key==='Alt'?'AltLeft':key.length===1?/^[0-9]$/.test(key)?'Digit'+key:'Key'+key.toUpperCase():key,bubbles:true,cancelable:true});
  window.dispatchEvent(event);
}
window.addEventListener('message', event=>{
  if (event.source !== window.parent || event.origin !== location.origin) return;
  const data=event.data;
  if (data?.mame==='key') { if (started) keyEvent(data.key, Boolean(data.pressed)); return; }
  if (data?.mame!=='boot' || started) return;
  started=true;
  try {
    const contents = new Uint8Array(data.bytes);
    const canvas = document.getElementById('screen');
    moduleRef = makeConfiguration(data.filename, contents, canvas,
      ()=>{notify('running');canvas.focus();},message=>notify('error',message));
    window.Module = moduleRef;
    injectScript();
  } catch(error) {notify('error',error.message);}
});
notify('ready');
