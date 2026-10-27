import test from 'node:test';
import assert from 'node:assert/strict';
import {SaveSession} from '../web/save-session.js';

test('save failure is visible and false; a retry can recover', async () => {
  const events=[];
  let succeeds=false;
  const saves = new SaveSession({
    supported:()=>true,
    write:async()=>succeeds,
    status:(state,text)=>events.push([state,text]),
  });
  const game={battery:()=>new Uint8Array([1,2])};
  assert.equal(await saves.persist(game,'one'),false);
  assert.equal(events.at(-1)[0],'warning');
  assert.match(events.at(-1)[1],/저장 실패/);
  succeeds=true;
  assert.equal(await saves.persist(game,'one'),true);
  assert.equal(events.at(-1)[0],'saved');
});

test('writes are serialized and each call snapshots the bytes',async()=>{
  let finish;
  const calls=[];
  const saves=new SaveSession({supported:()=>true,write:async(_key,bytes)=>{
    calls.push([...bytes]);
    if(calls.length===1)await new Promise(resolve=>{finish=resolve;});
    return true;
  }});
  const current=new Uint8Array([1]);
  const game={battery:()=>current};
  const first=saves.persist(game,'key');
  current[0]=2;
  const second=saves.persist(game,'key');
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls,[[1]]);
  finish();
  await Promise.all([first,second]);
  assert.deepEqual(calls,[[1],[2]]);
});

test('unavailable storage, read exceptions and invalid saved data warn users',async()=>{
  const events=[];
  const game={restore:()=>false};
  const unavailable=new SaveSession({supported:()=>false,status:(type,text)=>events.push([type,text])});
  assert.equal(await unavailable.restore(game,'key'),false);
  assert.match(events.at(-1)[1],/지원하지/);
  const broken=new SaveSession({supported:()=>true,read:async()=>{throw Error('blocked')},status:(type,text)=>events.push([type,text])});
  assert.equal(await broken.restore(game,'key'),false);
  assert.match(events.at(-1)[1],/읽지 못/);
  const bad=new SaveSession({supported:()=>true,read:async()=>new Uint8Array([9]),status:(type,text)=>events.push([type,text])});
  assert.equal(await bad.restore(game,'key'),false);
  assert.match(events.at(-1)[1],/복원하지 못/);
});
