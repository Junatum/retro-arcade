/* Browser-only per-ROM battery storage; no network access. */
// Stable per-ROM key without transmitting filenames or ROM bytes to the server.
export function romStorageKey(bytes, engine = 'mgba') {
  let hash=2166136261;
  for(const b of bytes){hash^=b;hash=Math.imul(hash,16777619);}
  return `${engine}:${bytes.length}:${(hash>>>0).toString(16)}`;
}
export async function batteryRead(key) {
  if (!('indexedDB' in globalThis)) return null;
  try {
    const db=await openDB();
    return await new Promise((resolve,reject)=>{
      const tx=db.transaction('battery','readonly');
      const req=tx.objectStore('battery').get(key);
      req.onsuccess=()=>resolve(req.result ? new Uint8Array(req.result) : null);
      req.onerror=()=>reject(req.error);
      tx.oncomplete=()=>db.close();
    });
  } catch (_) {return null;}
}
export async function batteryWrite(key,bytes) {
  if (!key || !bytes?.length || !('indexedDB' in globalThis)) return false;
  try {
    const db=await openDB();
    return await new Promise((resolve)=>{
      const tx=db.transaction('battery','readwrite');
      tx.objectStore('battery').put(bytes.slice(),key);
      tx.oncomplete=()=>{db.close();resolve(true);};
      tx.onerror=()=>{db.close();resolve(false);};
      tx.onabort=()=>{db.close();resolve(false);};
    });
  } catch (_) {return false;}
}
function openDB() {
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open('smartsafehub-retro-arcade',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('battery');
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(request.error);
  });
}
