"""MAME must serve its canvas stylesheet under the strict local CSP."""
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch
from scripts import release_audit

ROOT = Path(__file__).resolve().parents[1]


class MameCspTests(unittest.TestCase):
    def test_mame_runner_css_is_local_and_not_inline(self):
        page = (ROOT / 'web/mame/runner.html').read_text(encoding='utf-8')
        self.assertIn("style-src 'self'", page)
        self.assertIn('href="./runner.css"', page)
        self.assertNotRegex(page, r'<style(?:\s|>)|\sstyle\s*=')
        self.assertIn('object-fit:contain', (ROOT / 'web/mame/runner.css').read_text())
        self.assertIn('mame/runner.css', release_audit.EXPECTED_WEB)

    def test_csp_inline_style_and_missing_stylesheet_fail_release(self):
        with tempfile.TemporaryDirectory() as temp:
            fake = Path(temp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            with (patch.object(release_audit, 'ROOT', fake),
                  patch.object(release_audit, 'WEB', fake / 'web')):
                self.assertEqual(release_audit.audit(release=True), [])
                page = fake / 'web/mame/runner.html'
                page.write_text(page.read_text().replace('</head>', '<style>body{color:red}</style></head>'))
                self.assertTrue(any('runner CSP' in e for e in release_audit.audit(release=True)))
                page.write_text((ROOT / 'web/mame/runner.html').read_text())
                (fake / 'web/mame/runner.css').unlink()
                self.assertTrue(any('web inventory' in e for e in release_audit.audit(release=True)))

    def test_pinned_generated_mame_js_has_rom_export_functions(self):
        source = (ROOT / 'web/mame/mame.js').read_text(encoding='utf-8')
        self.assertIn('Module["FS_createDataFile"]', source)
        self.assertIn('Module["FS_createPath"]', source)
        self.assertNotIn('Module["FS"]', source)


if __name__ == '__main__':
    unittest.main()
