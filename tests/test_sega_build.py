"""Gearsystem/BlastEm offline linking guardrails (no Emscripten required)."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_sega


class SegaBuildTests(unittest.TestCase):
    def test_renames_gear_archive_for_linking_without_editing_upstream(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            archive = root / 'gearsystem_libretro_emscripten.bc'
            original = b'!<arch>\n' + b'placeholder archive for link contract'
            archive.write_bytes(original)
            link = build_sega.core_for_link('gearsystem', archive, root)
            self.assertEqual(link.name, 'gearsystem_libretro.a')
            self.assertEqual(link.read_bytes(), original)
            self.assertEqual(archive.read_bytes(), original)
            self.assertNotEqual(link, archive)

    def test_accepts_real_bitcode_but_rejects_unrecognized_core(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            core = root / 'gearsystem_libretro_emscripten.bc'
            core.write_bytes(b'BC\xc0\xde' + b'bitcode')
            self.assertEqual(build_sega.core_for_link('gearsystem', core, root), core)
            core.write_bytes(b'not-core')
            with self.assertRaisesRegex(ValueError, 'unsupported libretro core binary format'):
                build_sega.core_for_link('gearsystem', core, root)
            with self.assertRaisesRegex(ValueError, 'unsupported libretro core binary format'):
                build_sega.core_for_link('blastem', core, root)

    def test_upstream_archive_left_by_failed_link_does_not_block_rebuild(self):
        with tempfile.TemporaryDirectory() as dirname:
            source = Path(dirname)
            (source / 'platforms/libretro').mkdir(parents=True)
            (source / 'platforms/libretro/Makefile').write_text('all:')
            (source / 'platforms/libretro/libretro.h').write_text('// api')
            (source / 'LICENSE').write_text('GNU GENERAL PUBLIC LICENSE')
            git = ['a' * 40, '3.9.21', '?? platforms/libretro/gearsystem_libretro_emscripten.bc\n']
            with patch.object(build_sega, 'invoke', side_effect=git):
                revision, _license, _header = build_sega.check_source('gearsystem', source)
            self.assertEqual(revision, 'a' * 40)
            git[-1] += ' M src/core.cpp\n'
            with patch.object(build_sega, 'invoke', side_effect=git):
                with self.assertRaisesRegex(ValueError, 'local modifications'):
                    build_sega.check_source('gearsystem', source)

    def test_gear_rebuild_cleans_before_recompiling(self):
        with tempfile.TemporaryDirectory() as dirname:
            source = Path(dirname)
            out = source / 'platforms/libretro'
            out.mkdir(parents=True)
            core = out / 'gearsystem_libretro_emscripten.bc'
            core.write_bytes(b'!<arch>\n' + b'0' * 5000)
            with patch.object(build_sega, 'invoke') as invoked:
                self.assertEqual(build_sega.build_core('gearsystem', source, source), core)
            self.assertEqual(invoked.call_count, 2)
            self.assertIn('clean', invoked.call_args_list[0].args)
            self.assertNotIn('clean', invoked.call_args_list[1].args)

    def test_link_error_prints_stderr_stdout_and_exit_code(self):
        err = subprocess.CalledProcessError(
            1, ['em++', 'broken.a'], output='wasm-ld: error: undefined symbol: retro_run\n'
        )
        with patch.object(build_sega.subprocess, 'check_output', side_effect=err):
            with self.assertRaises(ValueError) as failure:
                build_sega.invoke('em++', 'broken.a')
        self.assertIn('wasm-ld: error: undefined symbol: retro_run', str(failure.exception))
        self.assertIn('exit 1', str(failure.exception))
        self.assertIn('em++ broken.a', str(failure.exception))

    def test_truncates_very_long_linker_log_but_keeps_last_error(self):
        error = subprocess.CalledProcessError(
            1, ['em++'], output='start marker\n' + 'x' * 31000 + '\nfinal error'
        )
        with patch.object(build_sega.subprocess, 'check_output', side_effect=error):
            with self.assertRaises(ValueError) as failure:
                build_sega.invoke('em++')
        self.assertIn('start marker', str(failure.exception))
        self.assertIn('final error', str(failure.exception))
        self.assertIn('truncated', str(failure.exception))


if __name__ == '__main__':
    unittest.main()
