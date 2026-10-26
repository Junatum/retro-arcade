import test from 'node:test';
import assert from 'node:assert/strict';

// Stock OpenWrt uhttpd recognizes .js, not .mjs. Check that the browser
// entrypoint can initialize the four platform cards without an HTTP server.
test('Retro Arcade browser entrypoint creates four selectable platforms', async () => {
  class ClassList {
    constructor() { this.names = new Set(); }
    add(name) { this.names.add(name); }
    remove(name) { this.names.delete(name); }
    toggle(name, force) {
      const add = force === undefined ? !this.names.has(name) : force;
      if (add) this.names.add(name); else this.names.delete(name);
      return add;
    }
  }
  class Element {
    constructor(tag) {
      this.tagName = tag;
      this.classList = new ClassList();
      this.dataset = {};
      this.children = [];
      this.attrs = {};
    }
    appendChild(child) { this.children.push(child); return child; }
    append(...children) { this.children.push(...children); }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    addEventListener() {}
    getContext() {
      return {
        createImageData(width, height) { return {data: new Uint8ClampedArray(width * height * 4)}; },
        putImageData() {},
      };
    }
  }
  const elements = new Map();
  const doc = {
    body: new Element('body'),
    addEventListener() {},
    getElementById(id) { if (!elements.has(id)) elements.set(id, new Element('div')); return elements.get(id); },
    createElement(tag) { return new Element(tag); },
  };
  const previousDocument = globalThis.document;
  const previousWindow = globalThis.window;
  globalThis.document = doc;
  globalThis.window = {addEventListener() {}};
  try {
    await import('../web/app.js?startup-test');
    assert.equal(doc.getElementById('systems').children.length, 4);
    assert.deepEqual(doc.getElementById('systems').children.map(b => b.dataset.system), ['chip8','mgba-gb','mgba','nes']);
    const nes = doc.getElementById('systems').children[3];
    nes.onclick();
    assert.equal(doc.getElementById('rom-file').accept, '.nes');
    assert.equal(nes.attrs['aria-pressed'], 'true');
  } finally {
    globalThis.document = previousDocument;
    globalThis.window = previousWindow;
  }
});
