import test from 'node:test';
import assert from 'node:assert/strict';

// Stock OpenWrt uhttpd recognizes .js, not .mjs. Check that the browser
// entrypoint can initialize the four platform cards without an HTTP server.
test('Retro Arcade initializes platforms and highlights only the bundled demo player on the right', async () => {
  let lastImage = null;
  let nextFrame = null;
  class ClassList {
    constructor() { this.names = new Set(); }
    add(name) { this.names.add(name); }
    remove(name) { this.names.delete(name); }
    contains(name) { return this.names.has(name); }
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
    replaceChildren(...children) { this.children = children; }
    append(...children) { this.children.push(...children); }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    addEventListener() {}
    scrollIntoView() {}
    getContext() {
      return {
        createImageData(width, height) { return {data: new Uint8ClampedArray(width * height * 4)}; },
        putImageData(image) { lastImage = image; },
      };
    }
  }
  const elements = new Map();
  const doc = {
    body: new Element('body'),
    addEventListener() {},
    getElementById(id) { if (!elements.has(id)) { const el = new Element('div'); el.ownerDocument = doc; elements.set(id, el); } return elements.get(id); },
    createElement(tag) { const el = new Element(tag); el.ownerDocument = doc; return el; },
  };
  const previousDocument = globalThis.document;
  const previousWindow = globalThis.window;
  const previousRAF = globalThis.requestAnimationFrame;
  const previousCAF = globalThis.cancelAnimationFrame;
  globalThis.requestAnimationFrame = callback => { nextFrame = callback; return 1; };
  globalThis.cancelAnimationFrame = () => {};
  globalThis.document = doc;
  globalThis.window = {addEventListener() {}};
  try {
    await import('../web/app.js?startup-test');
    assert.equal(doc.getElementById('systems').children.length, 4);
    assert.deepEqual(doc.getElementById('systems').children.map(b => b.dataset.system), ['chip8','mgba-gb','mgba','nes']);
    const demo = doc.getElementById('demo');
    const actions = doc.getElementById('load-buttons');
    assert.equal(demo.disabled, false, 'CHIP-8 starts with a visible demo');
    assert.equal(demo.classList.contains('hidden'), false);
    assert.equal(actions.classList.contains('buttons--single'), false);
    for (const system of doc.getElementById('systems').children.slice(1)) {
      system.onclick();
      assert.equal(demo.disabled, true, `${system.dataset.system} must disable CHIP-8 demo`);
      assert.equal(demo.classList.contains('hidden'), true, `${system.dataset.system} must hide CHIP-8 demo`);
      assert.equal(actions.classList.contains('buttons--single'), true, 'ROM button should fill mobile row');
    }
    doc.getElementById('systems').children[0].onclick();
    assert.equal(demo.disabled, false, 'returning to CHIP-8 restores the demo');
    assert.equal(demo.classList.contains('hidden'), false);
    assert.equal(actions.classList.contains('buttons--single'), false);
    const platforms = doc.getElementById('systems').children;
    for (const platform of platforms) {
      assert.match(platform.children[0].innerHTML, /<svg[^>]+aria-hidden="true"/);
      assert.match(platform.children[0].innerHTML, /<path|<rect/);
      assert.equal(platform.children[1].tagName, 'strong');
    }
    assert.notEqual(platforms[1].children[0].innerHTML, platforms[2].children[0].innerHTML);
    const nes = doc.getElementById('systems').children[3];
    nes.onclick();
    assert.equal(doc.getElementById('rom-file').accept, '.nes');
    assert.equal(nes.attrs['aria-pressed'], 'true');

    // Start the CHIP-8 demo using the real interpreter and capture the canvas
    // image. Its left computer paddle remains mint; right player is amber.
    doc.getElementById('systems').children[0].onclick();
    doc.getElementById('demo').onclick();
    assert.equal(doc.getElementById('demo-result').classList.contains('hidden'), true);
    assert.equal(doc.getElementById('demo-roles').classList.contains('hidden'), false);
    assert.match(doc.getElementById('demo-controls').textContent, /오른쪽 주황색 패들/);
    const contains = (r, g, b, minX, maxX) => {
      if (!lastImage) return false;
      for (let y = 0; y < 32; y++) for (let x = minX; x <= maxX; x++) {
        const i = (y * 64 + x) * 4;
        if (lastImage.data[i] === r && lastImage.data[i+1] === g && lastImage.data[i+2] === b) return true;
      }
      return false;
    };
    for (let i = 1; i <= 180 && !(contains(255,186,110,58,60) && contains(185,251,194,3,5)); i++) {
      nextFrame(i * 17);
    }
    assert.ok(contains(185,251,194,3,5), 'left computer paddle remains mint');
    assert.ok(contains(255,186,110,58,60), 'right player paddle is amber');
    assert.ok(contains(107,162,232,0,63), 'court walls use an independent blue color');
    const px=(x,y)=>[...lastImage.data.slice((y*64+x)*4,(y*64+x+1)*4)];
    assert.deepEqual(px(10,6),[107,162,232,255], 'top wall is blue');
    assert.deepEqual(px(10,30),[107,162,232,255], 'bottom wall is blue');
    assert.equal(doc.getElementById('player-title').textContent, 'CHIP-8 · 패들 랠리');

    // Let the deterministic CPU finish a five-point match, then verify the
    // overlay is displayed in the game itself and can restart without reload.
    for(let i=181;i<=6000 && doc.getElementById('demo-result').classList.contains('hidden');i++) {
      if (typeof nextFrame !== 'function') break;
      nextFrame(i*17);
    }
    assert.equal(doc.getElementById('demo-result').classList.contains('hidden'),false,'match must finish');
    assert.match(doc.getElementById('demo-result-title').textContent,/^(승리|패배)!$/);
    assert.match(doc.getElementById('demo-result-score').textContent,/5점 선승/);
    assert.equal(doc.getElementById('toggle').disabled,true,'ended match cannot resume');
    doc.getElementById('demo-replay').onclick();
    assert.equal(doc.getElementById('demo-result').classList.contains('hidden'),true,'replay removes result');
    assert.equal(doc.getElementById('toggle').disabled,false,'replay re-enables pause');
  } finally {
    globalThis.document = previousDocument;
    globalThis.window = previousWindow;
    if (previousRAF === undefined) delete globalThis.requestAnimationFrame;
    else globalThis.requestAnimationFrame = previousRAF;
    if (previousCAF === undefined) delete globalThis.cancelAnimationFrame;
    else globalThis.cancelAnimationFrame = previousCAF;
  }
});
