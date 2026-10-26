/* Offline NES audio via the standard Web Audio API. No AudioWorklet/HTTPS requirement. */
export class NesAudio {
  constructor(scope = globalThis) {
    this.scope = scope;
    this.capacity = 32768;
    this.left = new Float32Array(this.capacity);
    this.right = new Float32Array(this.capacity);
    this.read = 0;
    this.write = 0;
    this.context = null;
    this.node = null;
  }
  get sampleRate() { return this.context?.sampleRate || 48000; }
  push(left, right) {
    if (!this.node) return;
    const next = (this.write + 1) % this.capacity;
    if (next === this.read) this.read = (this.read + 1) % this.capacity;
    this.left[this.write] = left;
    this.right[this.write] = right;
    this.write = next;
  }
  async enable() {
    if (this.node) { await this.context.resume(); return true; }
    const AudioContext = this.scope.AudioContext || this.scope.webkitAudioContext;
    if (!AudioContext) throw new Error('이 브라우저에서는 NES 오디오를 지원하지 않습니다.');
    const context = new AudioContext();
    try {
      if (typeof context.createScriptProcessor !== 'function') {
        throw new Error('이 브라우저는 HTTP 호환 NES 오디오 출력을 지원하지 않습니다.');
      }
      const node = context.createScriptProcessor(2048, 0, 2);
      node.onaudioprocess = event => {
        const left = event.outputBuffer.getChannelData(0);
        const right = event.outputBuffer.getChannelData(1);
        for (let i = 0; i < left.length; i++) {
          if (this.read === this.write) { left[i] = right[i] = 0; continue; }
          left[i] = this.left[this.read]; right[i] = this.right[this.read];
          this.read = (this.read + 1) % this.capacity;
        }
      };
      node.connect(context.destination);
      this.context = context;
      this.node = node;
      await context.resume();
      return true;
    } catch (error) {
      await context.close();
      throw error;
    }
  }
  pause() { this.read = this.write; if (this.context) void this.context.suspend(); }
  resume() { if (this.context) void this.context.resume(); }
  destroy() {
    if (this.node) { this.node.disconnect(); this.node.onaudioprocess = null; }
    this.node = null;
    if (this.context) void this.context.close();
    this.context = null;
    this.read = this.write = 0;
  }
}
