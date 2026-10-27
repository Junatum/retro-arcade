/* Browser-only save lifecycle. Serialize writes and never silently report success. */
import { batteryReadStrict, batteryWrite } from './battery-store.js';

export class SaveSession {
  constructor({read = batteryReadStrict, write = batteryWrite, supported = () => 'indexedDB' in globalThis, status = () => {}} = {}) {
    this.read = read;
    this.write = write;
    this.supported = supported;
    this.status = status;
    this.pending = Promise.resolve(true);
  }

  async restore(game, key) {
    if (!key || !game) return true;
    if (!this.supported()) {
      this.status('warning', '이 브라우저는 게임 저장을 지원하지 않습니다. 진행 상황이 유지되지 않을 수 있습니다.');
      return false;
    }
    try {
      const bytes = await this.read(key);
      if (bytes && !game.restore(bytes)) {
        this.status('warning', '저장된 게임 데이터를 복원하지 못했습니다. 이전 저장 데이터를 확인해 주세요.');
        return false;
      }
      return true;
    } catch {
      this.status('warning', '게임 저장 데이터를 읽지 못했습니다. 브라우저 저장소 설정을 확인해 주세요.');
      return false;
    }
  }

  persist(game, key) {
    if (!game || !key) return this.pending;
    let bytes;
    try { bytes = game.battery(); }
    catch {
      this.status('warning', '게임 저장 데이터를 추출하지 못했습니다.');
      return Promise.resolve(false);
    }
    if (!bytes?.length) return this.pending; // Games without battery-backed RAM have nothing to save.
    // Snapshot before the asynchronous transaction and serialize future writes.
    const snapshot = bytes.slice();
    const task = this.pending.catch(() => false).then(async () => {
      this.status('saving', '게임 저장 중…');
      let ok = false;
      try { ok = Boolean(await this.write(key, snapshot)); }
      catch { /* A rejected IndexedDB transaction is still a failed write. */ }
      this.status(ok ? 'saved' : 'warning', ok ? '게임 저장 완료' : '저장 실패: 브라우저 저장 공간과 권한을 확인해 주세요.');
      return ok;
    });
    this.pending = task;
    return task;
  }

  flush() { return this.pending; }
}
