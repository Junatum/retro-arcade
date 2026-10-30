"""Keep the ROM-free Chromium smoke wired to the actual bundled MAME runtime."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MameCiContract(unittest.TestCase):
    def test_ci_requires_real_mame_assets_and_executes_browser_smoke(self):
        workflow = (ROOT / '.github/workflows/verify.yml').read_text(encoding='utf-8')
        self.assertIn('python3 scripts/mame_registry.py --check', workflow)
        self.assertIn('python3 scripts/release_audit.py --release', workflow)
        self.assertNotIn('MAME WASM not yet locally built;', workflow)
        self.assertIn('python3 tests/browser_e2e.py -v', workflow)
        self.assertIn('python3 -m playwright install --with-deps chromium', workflow)

    def test_mame_smoke_uses_real_wasm_and_own_data_not_game_roms(self):
        source = (ROOT / 'tests/browser_e2e.py').read_text(encoding='utf-8')
        self.assertIn('def test_mame_real_wasm_initializes_without_copyrighted_rom', source)
        self.assertIn("archive.writestr('ci-diagnostic.txt'", source)
        self.assertIn("arguments: ['-listfull']", source)
        self.assertIn("installRom(window.Module, 'galaxian'", source)
        self.assertIn("script.src = './mame.js'", source)
        self.assertIn("name.endsWith('.wasm') ? './mame.wasm'", source)
        self.assertIn("#mame-ci-result[data-result=", source)
        self.assertIn('forbidden_requests', source)
        self.assertTrue((ROOT / 'web/mame/mame.js').is_file())
        wasm = ROOT / 'web/mame/mame.wasm'
        self.assertEqual(wasm.read_bytes()[:8], b'\x00asm\x01\x00\x00\x00')
        self.assertIn(b'listfull', wasm.read_bytes())
        self.assertIn('MAME native ROM-free CLI boot', (ROOT / 'tests/mame-wasm.test.mjs').read_text())
        self.assertIn("arguments: ['-listfull']", (ROOT / 'tests/mame-node-probe.cjs').read_text())


if __name__ == '__main__':
    unittest.main()
