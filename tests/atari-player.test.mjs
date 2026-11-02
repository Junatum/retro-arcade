import test from 'node:test';
import assert from 'node:assert/strict';
import {AtariPlayer} from '../web/atari-player.js';

// No ROM or precompiled third-party file is required to test the first-party adapter.
test('Atari adapter delegates execution, audio, saving and teardown to local core', async()=>{
  const calls=[];
  const core={
    setAudioRate(n){calls.push(['rate',n]);},
    load(data){calls.push(['load',data.byteLength]);},
    key(k,p){calls.push(['key',k,p]);},
    frame(ms){calls.push(['frame',ms]);return Float32Array.of(0.25,-0.5);},
    save(){calls.push(['save']);return Uint8Array.of(4,5);},
    restore(data){calls.push(['restore',data.length]);return true;},
    clearInputs(){calls.push(['clear']);},
  };
  const audio={sampleRate:44100,push(l,r){calls.push(['audio',l,r]);},
    pause(){calls.push(['pause']);},resume(){calls.push(['resume']);},
    enable(){calls.push(['enable']);return Promise.resolve(true);},destroy(){calls.push(['destroy']);}};
  const player=new AtariPlayer(core,audio);
  assert.equal(player.fps,60);
  player.load(new Uint8Array(2048));
  player.key('up',true);
  player.frame();
  assert.deepEqual([...player.battery()],[4,5]);
  assert.equal(player.restore(Uint8Array.of(1,2,3)),true);
  player.pause();player.resume();await player.enableAudio();player.destroy();
  assert.deepEqual(calls,[['rate',44100],['load',2048],['key','up',true],['frame',1000/60],
    ['audio',0.25,0.25],['audio',-0.5,-0.5],['save'],['restore',3],
    ['pause'],['resume'],['enable'],['resume'],['clear'],['destroy']]);
});
