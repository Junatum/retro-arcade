"""MAME 0.289 provenance and fail-closed release checks (no WASM build needed)."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import release_audit, build_mame

ROOT = Path(__file__).resolve().parents[1]

class MameBuildTests(unittest.TestCase):
    def test_tag_driver_and_build_configuration_are_frozen(self):
        self.assertEqual(build_mame.TAG, 'mame0289')
        self.assertEqual(build_mame.VERSION, '0.289')
        self.assertEqual(build_mame.SOURCES, release_audit.MAME_SOURCES)
        self.assertEqual(build_mame.TAG, release_audit.MAME_TAG)
        self.assertEqual(build_mame.SUBTARGET, 'ssharcade')
        builder=(ROOT/'scripts/build_mame.py').read_text()
        self.assertIn("'OPTIMIZE=' + OPTIMIZATION", builder)
        self.assertEqual(build_mame.OPTIMIZATION, 'z')
        self.assertEqual(build_mame.BUILD_DIRECTORY, 'build-ssharcade-oz')
        self.assertIn('LDOPTS=-sEXPORTED_RUNTIME_METHODS=FS',builder)
        self.assertNotIn('src/mame/sega', build_mame.SOURCES)

    def test_source_checkout_must_match_pinned_tag(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)
            for item in ('makefile', 'src/mame/pacman/pacman.cpp', 'src/mame/galaxian/galaxian.cpp'):
                path=source/item;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('')
            rev='c'*40
            with patch.object(build_mame, 'run', side_effect=[rev,rev,'']):
                self.assertEqual(build_mame.verify_source(source),rev)
            with patch.object(build_mame, 'run', side_effect=[rev,'d'*40]):
                with self.assertRaisesRegex(ValueError, 'tag'):
                    build_mame.verify_source(source)

    def test_nonwasm_or_partial_mame_bundle_never_passes_release(self):
        # The test must be valid both before and after locally building MAME.
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            for name in ('mame.js', 'mame.wasm', 'manifest.json'):
                (fake / 'web/mame' / name).unlink(missing_ok=True)
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                errors = release_audit.audit(release=True)
                self.assertIn('mame: JS/WASM/manifest required before 1.2.0 APK release', errors)
                self.assertEqual(release_audit.audit(release=False), [])
        with tempfile.TemporaryDirectory() as folder:
            bad=Path(folder)/'bad.js';bad.write_text('var Module = {};')
            wasm=Path(folder)/'bad.wasm';wasm.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'header'):
                build_mame.verify_artifacts(bad,wasm)

    def test_docs_and_package_include_mame_license_and_runner(self):
        package=(ROOT/'Makefile').read_text()
        page=(ROOT/'web/index.html').read_text()
        readme=(ROOT/'README.md').read_text()
        self.assertIn('LICENSES/MAME-GPL2.txt',package)
        self.assertIn("frame-src 'self'",page)
        self.assertIn('MAME 0.289',readme)
        self.assertIn('GPL-2.0-or-later',package)
        self.assertIn('pacman.zip', (ROOT/'web/mame/runner.js').read_text())
        self.assertTrue((ROOT/'web/mame/runner.js').is_file())

if __name__=='__main__':
    unittest.main()
