import json
import pathlib
import unittest
from scripts.release_audit import audit

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_single_full_release(self):
        self.assertEqual(audit(), [])
        self.assertFalse((ROOT / 'web/vendor').exists())
        self.assertFalse((ROOT / '.source-only').exists())
        self.assertFalse((ROOT / 'COMMIT_MESSAGE.txt').exists())

    def test_version(self):
        info = json.loads((ROOT / 'app-info.json').read_text(encoding='utf-8'))
        mk = (ROOT / 'Makefile').read_text(encoding='utf-8')
        self.assertEqual(info['version'], '0.1.0-r1')
        self.assertIn('PKG_RELEASE:=1', mk)
        self.assertEqual(info['included_systems'], ['CHIP-8'])
        self.assertNotIn('GL-MT300N-V2', info['supported_models'])
        self.assertIn('GL-MT300N-V2', info['excluded_models'])

    def test_no_incorrect_emulatorjs_attribution(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('EmulatorJS', readme)
        self.assertIn('현재 릴리스는 EmulatorJS를 사용하거나 번들하지 않습니다', readme)
        self.assertTrue((ROOT / 'web/chip8.mjs').is_file())

    def test_no_external_runtime(self):
        markup = (ROOT / 'web/index.html').read_text(encoding='utf-8')
        self.assertIn('connect-src &#39;none&#39;', markup.replace("'none'", '&#39;none&#39;'))
        self.assertNotIn('https://cdn.', markup)
        self.assertIn('내장 데모 실행', markup)

    def test_release_gate_rejects_new_vendor_files(self):
        path = ROOT / 'web' / 'unverified.wasm'
        self.addCleanup(path.unlink, missing_ok=True)
        path.write_bytes(b'not licensed')
        self.assertTrue(any('unreviewed' in issue or 'unexpected' in issue for issue in audit()))

    def test_changelog_has_only_r1(self):
        content = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
        self.assertEqual(content.count('## 0.1.0-r1'), 1)
        self.assertNotIn('## 0.1.0-r2', content)

if __name__ == '__main__':
    unittest.main()
