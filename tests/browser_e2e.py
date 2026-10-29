#!/usr/bin/env python3
"""Real HTTP+Chromium smoke test; requires Playwright only in developer/CI tests.

No copyrighted game assets, no frontend build, and no access to external hosts.
"""
from __future__ import annotations
import functools
import http.server
import os
from pathlib import Path
import shutil
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'


class SilentHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.js': 'text/javascript', '.wasm': 'application/wasm'}

    def log_message(self, *_args):
        pass


def synthetic_nes_rom():
    # Original no-op ROM, created in memory. JMP $8000 with reset vector $8000.
    header = bytearray(b'NES\x1a') + bytearray([1, 1, 2, 0]) + bytearray(8)
    prg = bytearray(16384)
    prg[:3] = b'\x4c\x00\x80'
    prg[0x3FFA:0x4000] = b'\x00\x80\x00\x80\x00\x80'
    return bytes(header + prg + bytearray(8192))


class BrowserSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError('Install playwright to run real browser E2E') from exc
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SilentHandler, directory=str(WEB)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/'
        cls.pl = sync_playwright().start()
        executable = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('chromium-browser')
        kwargs = {'headless': True, 'args': ['--no-sandbox']}
        if executable:
            kwargs['executable_path'] = executable
        cls.browser = cls.pl.chromium.launch(**kwargs)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pl.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def test_initialization_and_demo_in_desktop_and_mobile(self):
        for width in (1280, 390, 320):
            with self.subTest(width=width):
                page = self.browser.new_page(viewport={'width': width, 'height': 840})
                failures = []
                page.on('pageerror', lambda error: failures.append(str(error)))
                page.on('request', lambda req: failures.append(f'external request: {req.url}') if not req.url.startswith(self.url) else None)
                try:
                    page.goto(self.url, wait_until='networkidle')
                    self.assertEqual(page.locator('#systems button').count(), 9)
                    self.assertEqual(page.locator('#demo').is_visible(), True)
                    page.locator('#systems button').nth(3).click()
                    self.assertEqual(page.locator('#demo').is_visible(), False)
                    page.locator('#systems button').first.click()
                    page.locator('#demo').click()
                    self.assertTrue(page.locator('#player-section').is_visible())
                    self.assertEqual(page.locator('#game canvas').count(), 1)
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth > window.innerWidth + 2'))
                    self.assertEqual(failures, [], f'{width}px console/network failures')
                finally:
                    page.close()

    def test_arcade_only_accepts_selected_rom_names_before_loading(self):
        # No game assets, emulator JS or WASM are required for this UI contract.
        page = self.browser.new_page(viewport={'width': 390, 'height': 844})
        try:
            page.goto(self.url, wait_until='networkidle')
            page.locator('#systems button').last.click()
            self.assertIn('pacman.zip', page.locator('#rom-help').inner_text())
            page.locator('#rom-file').set_input_files({
                'name': 'tetris.zip', 'mimeType': 'application/zip',
                'buffer': b'PK\x03\x04' + bytes(64),
            })
            self.assertFalse(page.locator('#play').is_enabled())
            self.assertIn('pacman.zip', page.locator('#notice').inner_text())
            self.assertEqual(page.locator('iframe').count(), 0)
        finally:
            page.close()

    def test_blocked_browser_storage_displays_warning(self):
        context = self.browser.new_context()
        context.add_init_script("Object.defineProperty(window, 'indexedDB', {get(){throw new Error('blocked')}})")
        page = context.new_page()
        try:
            page.goto(self.url, wait_until='networkidle')
            page.locator('#systems button').nth(3).click()
            page.locator('#rom-file').set_input_files({'name':'blocked.nes','mimeType':'application/octet-stream','buffer':synthetic_nes_rom()})
            page.locator('#play').click()
            page.locator('#save-status.save-status--error').wait_for(timeout=12000)
            self.assertTrue(page.locator('#save-status').is_visible())
        finally:
            context.close()

    def test_nes_audio_is_visible_and_browser_blocking_is_actionable(self):
        # A blocked AudioContext must not prevent the game from launching.
        # The user must see a retry button next to the game title.
        context = self.browser.new_context()
        context.add_init_script("""
          Object.defineProperty(window, 'AudioContext', {value: undefined, configurable: true});
          Object.defineProperty(window, 'webkitAudioContext', {value: undefined, configurable: true});
        """)
        page = context.new_page()
        try:
            page.goto(self.url, wait_until='networkidle')
            page.locator('#systems button').nth(3).click()
            page.locator('#rom-file').set_input_files({
                'name': 'silent.nes', 'mimeType': 'application/octet-stream',
                'buffer': synthetic_nes_rom(),
            })
            page.locator('#play').click()
            page.locator('#player-section').wait_for(state='visible', timeout=12000)
            page.locator('#sound.sound-button--attention').wait_for(state='visible', timeout=12000)
            self.assertIn('소리 켜기', page.locator('#sound').inner_text())
            self.assertIn('브라우저가', page.locator('#sound-status').text_content())
            self.assertIn('브라우저가', page.locator('#sound').get_attribute('title'))
            # Descriptive status is still announced to assistive technology,
            # but never consumes a row between the header and canvas.
            self.assertLessEqual(page.locator('#sound-status').evaluate('(el) => el.getBoundingClientRect().height'), 1)
            self.assertEqual(page.locator('#game canvas').evaluate('(c)=>[c.width,c.height]'), [256, 240])
        finally:
            context.close()

    def test_http_nes_rom_and_local_runtime(self):
        page = self.browser.new_page(viewport={'width': 1280, 'height': 850})
        failures = []
        page.on('pageerror', lambda error: failures.append(str(error)))
        try:
            page.goto(self.url, wait_until='networkidle')
            page.locator('#systems button').nth(3).click()
            page.locator('#rom-file').set_input_files({'name': 'smoke.nes', 'mimeType': 'application/octet-stream', 'buffer': synthetic_nes_rom()})
            self.assertTrue(page.locator('#play').is_enabled())
            page.locator('#play').click()
            # A locator waits for a real DOM visibility transition without
            # evaluating JavaScript strings blocked by the app's strict CSP.
            page.locator('#player-section').wait_for(state='visible', timeout=12000)
            self.assertEqual(page.locator('#game canvas').evaluate('(c) => [c.width, c.height]'), [256, 240])
            page.locator('#toggle').click()
            self.assertIn('계속', page.locator('#toggle').inner_text())
            # Browser must also be able to initialize the existing mGBA WASM runtime.
            self.assertTrue(page.evaluate("""async () => {
              const {MgbaPlayer} = await import('./mgba-player.js');
              const canvas = document.createElement('canvas');
              const player = await MgbaPlayer.create(canvas);
              player.destroy();
              return true;
            }"""))
            self.assertEqual(failures, [])
        finally:
            page.close()


if __name__ == '__main__':
    unittest.main()
