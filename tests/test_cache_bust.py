"""Regression tests for browser cache hashes on canonical and aliased paths."""
import pathlib
import shutil
import tempfile
import unittest

from scripts import cache_bust

ROOT = pathlib.Path(__file__).resolve().parents[1]


class CacheBustPathTests(unittest.TestCase):
    def test_macos_var_private_var_alias(self):
        # On macOS /var is a symlink to /private/var; both must be treated
        # as the same directory when resolving local ES module imports.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            real = root / 'private' / 'var' / 'repo' / 'web'
            real.parent.mkdir(parents=True)
            shutil.copytree(ROOT / 'web', real)
            (root / 'var').symlink_to(root / 'private' / 'var', target_is_directory=True)
            alias = root / 'var' / 'repo' / 'web'

            self.assertEqual(cache_bust.check(web=alias), [])
            demo = real / 'demo.js'
            demo.write_text(demo.read_text(encoding='utf-8') + '\n// changed\n', encoding='utf-8')
            self.assertIn('app.js', cache_bust.check(web=alias))
            cache_bust.check(update=True, web=alias)
            self.assertEqual(cache_bust.check(web=alias), [])

    def test_symlink_import_cannot_escape_web_root(self):
        # Canonicalizing the web root must not weaken dependency confinement.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            web = root / 'web'
            shutil.copytree(ROOT / 'web', web)
            (root / 'outside.js').write_text('export const leak = true;\n', encoding='utf-8')
            (web / 'outside.js').symlink_to(root / 'outside.js')
            app = web / 'app.js'
            app.write_text(app.read_text(encoding='utf-8') + '\nimport { leak } from "./outside.js";\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'invalid local JS dependency'):
                cache_bust.check(web=web)


if __name__ == '__main__':
    unittest.main()
