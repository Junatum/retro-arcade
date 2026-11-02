/* SmartSafeHub first-party Atari bridge; browser-only ROM input. */
export class AtariPlayer {
  static async create(canvas, audio) {
    // This local module is generated from an independently reviewed, pinned
    // upstream source checkout by scripts/build_atari.py. Never fetch an engine.
    const {RetroAtariCore} = await import(new URL('./atari2600/engine.js', import.meta.url).href);
    return new AtariPlayer(new RetroAtariCore(canvas), audio);
  }
  constructor(core, audio) {
    this.core=core;this.audio=audio;
    this.fps=60;
    this.muted=false;
    if(audio)this.core.setAudioRate(audio.sampleRate);
  }
  load(bytes) {this.core.load(bytes);}
  key(key,pressed) {this.core.key(key,pressed);}
  frame() {
    const samples=this.core.frame(1000/60);
    if(this.audio&&!this.muted)for(let i=0;i<samples.length;i++)this.audio.push(samples[i],samples[i]);
  }
  battery() {return this.core.save();}
  restore(bytes) {return this.core.restore(bytes);}
  pause() {this.audio?.pause();}
  resume() {this.audio?.resume();}
  async enableAudio() {this.muted=false;await this.audio?.enable();this.resume();}
  destroy() {this.core.clearInputs();this.audio?.destroy();}
}
