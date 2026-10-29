"""MAME -Oz must be a fresh, verifiable build, not a relabeled -Os binary."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_mame, release_audit

ROOT = Path(__file__).resolve().parents[1]


class MameOzTests(unittest.TestCase):
    def test_clean_build_uses_size_optimization_and_new_intermediates(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            js = source / 'ssharcade.js'
            wasm = source / 'ssharcade.wasm'
            js.write_text('Module[\"FS_createPath\"] Module[\"FS_createDataFile\"] ' + 'x' * 2500)
            wasm.write_bytes(b'\x00asm\x01\x00\x00\x00' + b'fake test body')
            with (patch('sys.argv', ['build_mame.py', '--source', str(source)]),
                  patch.object(build_mame, 'verify_source', return_value='a' * 40),
                  patch.object(build_mame, 'run', return_value=''),
                  patch.object(build_mame, 'package') as package):
                self.assertEqual(build_mame.main(), 0)
                calls = build_mame.run.call_args_list
            args = calls[-1].args
            self.assertEqual(args[:2], ('emmake', 'make'))
            self.assertIn('OPTIMIZE=z', args)
            self.assertIn('BUILDDIR=build-ssharcade-oz', args)
            self.assertIn('REGENIE=1', args)
            self.assertIn('SOURCES=' + build_mame.SOURCES, args)
            self.assertNotIn('OPTIMIZE=s', args)
            self.assertEqual(package.call_count, 1)
            receipt = json.loads((source / build_mame.RECEIPT_NAME).read_text())
            self.assertEqual(receipt['optimization'], 'z')
            self.assertEqual(receipt['build_dir'], 'build-ssharcade-oz')
            self.assertEqual(receipt['artifacts']['wasm'], hashlib.sha256(wasm.read_bytes()).hexdigest())
            build_mame.verify_receipt(source, 'a' * 40, js, wasm)

    def test_package_only_requires_matching_local_build(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            js, wasm = source / 'ssharcade.js', source / 'ssharcade.wasm'
            js.write_bytes(b'js')
            wasm.write_bytes(b'wasm')
            with self.assertRaisesRegex(ValueError, 'receipt missing'):
                build_mame.verify_receipt(source, 'a' * 40, js, wasm)
            build_mame.write_receipt(source, 'a' * 40, js, wasm)
            build_mame.verify_receipt(source, 'a' * 40, js, wasm)
            wasm.write_bytes(b'old-Os-binary')
            with self.assertRaisesRegex(ValueError, 'does not match'):
                build_mame.verify_receipt(source, 'a' * 40, js, wasm)
            wasm.write_bytes(b'wasm')
            receipt = source / build_mame.RECEIPT_NAME
            data = json.loads(receipt.read_text())
            data['optimization'] = 's'
            receipt.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'does not match'):
                build_mame.verify_receipt(source, 'a' * 40, js, wasm)

    def test_package_only_does_not_relabel_old_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            js, wasm = source / 'ssharcade.js', source / 'ssharcade.wasm'
            js.write_text('Module[\"FS_createPath\"] Module[\"FS_createDataFile\"] ' + 'x' * 2500)
            wasm.write_bytes(b'\x00asm\x01\x00\x00\x00')
            with (patch('sys.argv', ['build_mame.py', '--source', str(source), '--package-only']),
                  patch.object(build_mame, 'verify_source', return_value='a' * 40),
                  patch.object(build_mame, 'package') as package,
                  self.assertRaises(SystemExit)):
                build_mame.main()
            package.assert_not_called()
            build_mame.write_receipt(source, 'a' * 40, js, wasm)
            with (patch('sys.argv', ['build_mame.py', '--source', str(source), '--package-only']),
                  patch.object(build_mame, 'verify_source', return_value='a' * 40),
                  patch.object(build_mame, 'package') as package):
                self.assertEqual(build_mame.main(), 0)
            package.assert_called_once()

    def test_failed_build_invalidates_receipt_before_link(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            (source / build_mame.RECEIPT_NAME).write_text('{}')
            with (patch('sys.argv', ['build_mame.py', '--source', str(source)]),
                  patch.object(build_mame, 'verify_source', return_value='a' * 40),
                  patch.object(build_mame, 'run', side_effect=ValueError('build failure')),
                  patch.object(build_mame, 'package') as package,
                  self.assertRaises(SystemExit)):
                build_mame.main()
            self.assertFalse((source / build_mame.RECEIPT_NAME).exists())
            package.assert_not_called()

    def test_release_rejects_old_or_relabelled_mame_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            engine = fake / 'web/mame'
            engine.mkdir(exist_ok=True)
            js, wasm = engine / 'mame.js', engine / 'mame.wasm'
            js.write_text('Module[\"FS_createPath\"] Module[\"FS_createDataFile\"] ' + 'x' * 2500)
            wasm.write_bytes(b'\x00asm\x01\x00\x00\x00')
            manifest = {
                'engine': 'mame', 'version': '0.289', 'tag': 'mame0289',
                'upstream': 'https://github.com/mamedev/mame',
                'revision': 'a' * 40, 'license': 'GPL-2.0-or-later',
                'drivers': ['pacman', 'galaxian'], 'optimization': 'z',
                'build_dir': build_mame.BUILD_DIRECTORY,
                'runtime_exports': ['FS'], 'sources': build_mame.SOURCES.split(','),
                'license_sha256': release_audit.sha256(fake / 'LICENSES/MAME-GPL2.txt'),
                'build_script_sha256': release_audit.sha256(fake / 'scripts/build_mame.py'),
                'artifacts': {'mame.js': release_audit.sha256(js),
                              'mame.wasm': release_audit.sha256(wasm)},
            }
            path = engine / 'manifest.json'
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                path.write_text(json.dumps(manifest))
                self.assertEqual(release_audit.audit(release=True), [])
                manifest['optimization'] = 's'
                path.write_text(json.dumps(manifest))
                self.assertIn('mame: unapproved release, driver set, or license',
                              release_audit.audit(release=True))
                manifest['optimization'] = 'z'
                manifest['build_dir'] = 'build'
                path.write_text(json.dumps(manifest))
                self.assertIn('mame: unapproved release, driver set, or license',
                              release_audit.audit(release=True))


if __name__ == '__main__':
    unittest.main()
