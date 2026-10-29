import test from 'node:test';
import assert from 'node:assert/strict';

const originalWindow = globalThis.window;
const originalLocation = globalThis.location;
const listeners = [];
globalThis.location = { origin: 'http://router.local' };
globalThis.window = {parent:{postMessage() {}},addEventListener:(event, callback) => listeners.push({event,callback})};
const {installRom,makeConfiguration} = await import('../web/mame/runner.js');
globalThis.window = originalWindow;
globalThis.location = originalLocation;

const content = Uint8Array.from([0x50,0x4b,0x03,0x04, ...new Uint8Array(30)]);

test('bundled MAME legacy FS exports create exactly one local ROM ZIP', () => {
  const calls = [];
  const mod = {
    FS_createPath: (...args) => calls.push(['path', ...args]),
    FS_createDataFile: (...args) => calls.push(['file', ...args]),
  };
  installRom(mod, 'pacman', content);
  assert.deepEqual(calls[0], ['path','/', 'roms', true, true]);
  assert.deepEqual(calls[1], ['file','/roms','pacman.zip',content,true,false,true]);
  assert.equal(calls.length,2);
});

test('other compatible MAME builds may export Module.FS', () => {
  const ops=[];
  const mod={FS:{mkdir:p=>ops.push(['mkdir',p]), writeFile:(p,contents)=>ops.push(['write',p,contents])}};
  installRom(mod,'galaxian',content);
  assert.deepEqual(ops,[['mkdir','/roms'],['write','/roms/galaxian.zip',content]]);
});

test('rejects missing FS, wrong driver and non-ROM data; never downloads ROM', () => {
  assert.throws(()=>installRom({},'pacman',content),/파일시스템/);
  assert.throws(()=>installRom({},'../../pacman',content),/지원하지 않는/);
  assert.throws(()=>installRom({},'pacman',null),/지원하지 않는/);
  assert.throws(()=>makeConfiguration('other.zip',content,{},()=>{},()=>{}),/허용되지 않은/);
  const source = makeConfiguration('pacman.zip', content, {}, ()=>{}, ()=>{});
  assert.deepEqual(source.arguments.slice(0,3),['pacman','-rompath','/roms']);
  assert.equal(source.preRun.length,1);
});

test('boot message wires preRun to the actual filesystem exports', () => {
  const oldWindow = globalThis.window;
  const oldLocation = globalThis.location;
  const oldDocument = globalThis.document;
  const ops=[];
  const parent={postMessage:()=>{}};
  const canvas={focus:()=>{}};
  globalThis.location = {origin:'http://router.local'};
  globalThis.document={
    getElementById:()=>canvas,
    createElement:()=>({}),
    head:{appendChild:()=>{}},
  };
  globalThis.window={parent,Module:null};
  try {
    const receive = listeners.find(it=>it.event==='message').callback;
    receive({source:parent,origin:globalThis.location.origin,
      data:{mame:'boot',filename:'galaxian.zip',bytes:content.buffer}});
    const mod=globalThis.window.Module;
    assert.equal(mod.arguments[0],'galaxian');
    mod.FS_createPath=(...args)=>ops.push(['path',...args]);
    mod.FS_createDataFile=(...args)=>ops.push(['file',...args]);
    mod.preRun[0]();
    assert.equal(ops[0][0],'path');
    assert.deepEqual(ops[1].slice(0,3), ['file','/roms','galaxian.zip']);
    assert.deepEqual(ops[1][3],content);
  } finally {
    globalThis.window=oldWindow;
    globalThis.location=oldLocation;
    globalThis.document=oldDocument;
  }
});
