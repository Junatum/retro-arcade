import test from 'node:test';
import assert from 'node:assert/strict';
import { setupFullscreen } from '../web/fullscreen.mjs';
class FakeElement {
  constructor() {
    this.names = new Set();
    this.classList = { toggle: (name, enabled) => enabled ? this.names.add(name) : this.names.delete(name) };
    this.attributes = {};
    this.textContent = '';
  }
  setAttribute(name, value) { this.attributes[name] = value; }
}
function harness() {
  const doc = new EventTarget();
  doc.fullscreenElement = null;
  const section = new FakeElement();
  const button = new FakeElement();
  const body = new FakeElement();
  const controller = setupFullscreen(section, button, doc, body);
  return {doc, section, button, body, controller};
}
function escape(doc) {
  const event = new Event('keydown', { cancelable: true });
  Object.defineProperty(event, 'key', {value: 'Escape'});
  doc.dispatchEvent(event);
  return event;
}
test('native fullscreen activates, updates its button and exits', async () => {
  const { doc, section, button, body, controller } = harness();
  section.requestFullscreen = async () => {
    doc.fullscreenElement = section;
    doc.dispatchEvent(new Event('fullscreenchange'));
  };
  doc.exitFullscreen = async () => {
    doc.fullscreenElement = null;
    doc.dispatchEvent(new Event('fullscreenchange'));
  };
  assert.equal(button.attributes['aria-pressed'], 'false');
  await controller.toggle();
  assert.equal(controller.active(), true);
  assert.equal(button.attributes['aria-pressed'], 'true');
  assert.equal(body.names.has('theater-open'), true);
  assert.equal(section.names.has('theater-mode'), false);
  await controller.toggle();
  assert.equal(controller.active(), false);
  assert.equal(body.names.has('theater-open'), false);
});
test('unsupported fullscreen uses theater mode and Escape closes it', async () => {
  const { doc, section, button, body, controller } = harness();
  await controller.toggle();
  assert.equal(section.names.has('theater-mode'), true);
  assert.equal(button.attributes['aria-pressed'], 'true');
  assert.equal(body.names.has('theater-open'), true);
  assert.equal(escape(doc).defaultPrevented, true);
  assert.equal(controller.active(), false);
  assert.equal(section.names.has('theater-mode'), false);
  assert.equal(button.attributes['aria-pressed'], 'false');
});
test('rejected fullscreen request falls back, button exits, other keys do not', async () => {
  const { doc, section, controller } = harness();
  section.requestFullscreen = async () => { throw new Error('fullscreen not allowed'); };
  await controller.toggle();
  const event = new Event('keydown', { cancelable: true });
  Object.defineProperty(event, 'key', { value: 'ArrowUp' });
  doc.dispatchEvent(event);
  assert.equal(controller.active(), true);
  assert.equal(event.defaultPrevented, false);
  await controller.exit();
  assert.equal(controller.active(), false);
});
test('native Escape-driven exit synchronizes browser controls', async () => {
  const { doc, section, button, controller } = harness();
  section.requestFullscreen = async () => { doc.fullscreenElement = section; };
  await controller.toggle();
  doc.fullscreenElement = null;
  doc.dispatchEvent(new Event('fullscreenchange'));
  assert.equal(controller.active(), false);
  assert.equal(button.attributes['aria-pressed'], 'false');
});
