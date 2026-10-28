import test from 'node:test';
import assert from 'node:assert/strict';
import {supportsGameAudio,paintAudioState} from '../web/audio-controls.js';
import {NesAudio} from '../web/nes-audio.js';

function fakeElement(){
  const classes=new Set();
  return {textContent:'',attributes:{},classList:{
    toggle(key,yes){if(yes)classes.add(key);else classes.delete(key);},
    contains(key){return classes.has(key);},
  },setAttribute(key,value){this.attributes[key]=value;}};
}

test('only bundled NES/Sega emulators show a prominent audio status',()=>{
  for(const id of ['nes','gearsystem-gg','gearsystem-sms','gearsystem-sg','blastem'])
    assert.equal(supportsGameAudio(id),true,id);
  for(const id of ['chip8','mgba-gb','mgba'])assert.equal(supportsGameAudio(id),false,id);
});

test('speaker status distinguishes default enabled, muted, pending and browser-blocked',()=>{
  const button=fakeElement(),hint=fakeElement();
  paintAudioState(button,hint,'starting');
  assert.match(button.textContent,/연결 중/);
  paintAudioState(button,hint,'on');
  assert.match(button.textContent,/소리 켜짐/);
  assert.match(button.title,/음소거/); // small button tooltip replaces full-width banner
  assert.equal(button.attributes['aria-pressed'],'true');
  assert.equal(button.classList.contains('sound-button--on'),true);
  paintAudioState(button,hint,'off');
  assert.match(button.textContent,/소리 꺼짐/);
  assert.equal(button.attributes['aria-pressed'],'false');
  paintAudioState(button,hint,'blocked');
  assert.match(hint.textContent,/브라우저가 자동 사운드를 제한/);
  assert.equal(button.title,hint.textContent); // same instructions for mouse and screen reader
  assert.equal(button.classList.contains('sound-button--attention'),true);
});

test('initial game gesture can start audio, and pause/resume preserves the browser context',async()=>{
  const calls=[];
  class Context{
    sampleRate=48000;
    destination={};
    constructor(){calls.push('created');}
    createScriptProcessor(){calls.push('processor');return {connect(){},disconnect(){}};}
    resume(){calls.push('resumed');return Promise.resolve();}
    suspend(){calls.push('suspended');return Promise.resolve();}
    close(){calls.push('closed');return Promise.resolve();}
  }
  const audio=new NesAudio({AudioContext:Context});
  const started=audio.enable();
  assert.deepEqual(calls,['created','processor','resumed']); // no async loading first
  assert.equal(await started,true);
  audio.pause();audio.resume();audio.destroy();
  assert.deepEqual(calls.slice(-3),['suspended','resumed','closed']);
});

test('audio is gracefully rejected when Web Audio is unavailable',async()=>{
  const audio=new NesAudio({});
  await assert.rejects(audio.enable(),/지원하지 않습니다/);
  assert.equal(audio.node,null);
});

test('failed browser resume releases its context so retry can turn sound on',async()=>{
  let first=true;
  const calls=[];
  class Context {
    destination={};
    createScriptProcessor(){return {connect(){},disconnect(){calls.push('disconnect');}};}
    resume(){if(first){first=false;return Promise.reject(new Error('blocked'));}return Promise.resolve();}
    close(){calls.push('close');return Promise.resolve();}
  }
  const audio=new NesAudio({AudioContext:Context});
  await assert.rejects(audio.enable(),/blocked/);
  assert.equal(audio.node,null);
  assert.equal(audio.context,null);
  assert.equal(calls.includes('disconnect'),true);
  assert.equal(await audio.enable(),true);
  audio.destroy();
});
