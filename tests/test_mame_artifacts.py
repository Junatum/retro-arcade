"""Regression tests for MAME SOURCES= target names on macOS/Linux."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import build_mame


class MameArtifactDiscoveryTests(unittest.TestCase):
    def test_sources_build_uses_subtarget_name_not_mame_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            js = source / 'ssharcade.js'
            wasm = source / 'ssharcade.wasm'
            js.write_text('mock js (discovery only)')
            wasm.write_bytes(b'\x00asm\x01\x00\x00\x00')
            # Another MAME build may be present; it is not our selected drivers.
            (source / 'mameother.js').write_text('wrong target')
            (source / 'mameother.wasm').write_bytes(b'not our target')
            self.assertEqual(build_mame.find_mame_artifacts(source), (js, wasm))

    def test_partial_output_reports_precise_missing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source / 'ssharcade.js').write_text('mock')
            with self.assertRaisesRegex(ValueError, r'ssharcade\.wasm') as exc:
                build_mame.find_mame_artifacts(source)
            self.assertIn('--js PATH --wasm PATH', str(exc.exception))

    def test_other_build_or_missing_output_is_never_selected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source / 'mameother.js').write_text('unrelated')
            (source / 'mameother.wasm').write_bytes(b'\x00asm')
            with self.assertRaisesRegex(ValueError, 'Expected matching Emscripten artifacts') as exc:
                build_mame.find_mame_artifacts(source)
            self.assertIn('mameother.js', str(exc.exception))
            self.assertIn('ssharcade.js', str(exc.exception))

    def test_main_auto_packages_subtarget_pair(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source / 'ssharcade.js').write_text('test')
            (source / 'ssharcade.wasm').write_bytes(b'\x00asm')
            args = ['build_mame.py', '--source', str(source), '--jobs', '2']
            with (patch('sys.argv', args),
                  patch.object(build_mame, 'verify_source', return_value='a'*40),
                  patch.object(build_mame, 'run', return_value=''),
                  patch.object(build_mame, 'verify_artifacts'),
                  patch.object(build_mame, 'write_receipt'),
                  patch.object(build_mame, 'package') as package):
                self.assertEqual(build_mame.main(), 0)
            # main() resolves --source: macOS may spell the same directory
            # /var/... or /private/var/..., depending on the caller.
            self.assertEqual(package.call_args.args[2:],
                             ((source / 'ssharcade.js').resolve(),
                              (source / 'ssharcade.wasm').resolve()))

    def test_main_auto_packages_symlinked_source_alias(self):
        # Reproduce /var -> /private/var on any host (including Linux CI).
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            original = base / 'original'
            original.mkdir()
            (original / 'ssharcade.js').write_text('test')
            (original / 'ssharcade.wasm').write_bytes(b'\x00asm')
            alias = base / 'alias'
            alias.symlink_to(original, target_is_directory=True)
            args = ['build_mame.py', '--source', str(alias), '--jobs', '2']
            with (patch('sys.argv', args),
                  patch.object(build_mame, 'verify_source', return_value='a'*40),
                  patch.object(build_mame, 'run', return_value=''),
                  patch.object(build_mame, 'verify_artifacts'),
                  patch.object(build_mame, 'write_receipt'),
                  patch.object(build_mame, 'package') as package):
                self.assertEqual(build_mame.main(), 0)
            self.assertEqual(package.call_args.args[2:],
                             ((original / 'ssharcade.js').resolve(),
                              (original / 'ssharcade.wasm').resolve()))


if __name__ == '__main__':
    unittest.main()
