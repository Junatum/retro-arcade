"""BlastEm browser-only debugger/oscilloscope link shims.

No upstream checkout, Emscripten or ROM files are required. Test an ordinary
C compiler against equivalent upstream function declarations when available.
"""
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_sega, release_audit


class BlastEmHeadlessTests(unittest.TestCase):
    def test_only_blastem_injects_headless_stubs(self):
        for engine in ('gearsystem', 'blastem'):
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as name:
                tmp = Path(name)
                core = tmp / 'core.a'
                with patch.object(build_sega, 'invoke') as invoke:
                    build_sega.link_web_core(engine, tmp / 'source', core, tmp)
                self.assertEqual(invoke.call_count, 2)
                compile_command = invoke.call_args_list[0].args
                link_command = invoke.call_args_list[1].args
                self.assertEqual(compile_command[0], 'emcc')
                self.assertEqual(link_command[0], 'em++')
                self.assertIn(str(core), link_command)
                self.assertIn(str(tmp / 'sega_libretro_bridge.o'), link_command)
                self.assertNotIn('-sERROR_ON_UNDEFINED_SYMBOLS=0', link_command)
                if engine == 'blastem':
                    self.assertIn('-DIS_LIB', compile_command)
                    self.assertIn('-include', compile_command)
                    i = compile_command.index('-include')
                    self.assertEqual(compile_command[i + 1], str(build_sega.BLASTEM_HEADLESS))
                else:
                    self.assertNotIn('-include', compile_command)
                    self.assertNotIn('-DIS_LIB', compile_command)

    @unittest.skipUnless(shutil.which('cc'), 'C compiler required')
    def test_noop_ui_symbols_match_blastem_headers_and_link(self):
        with tempfile.TemporaryDirectory(prefix='blastem-stub-') as name:
            root = Path(name)
            (root / 'nuklear_ui').mkdir()
            (root / 'oscilloscope.h').write_text(
                '#include <stdint.h>\ntypedef struct { unsigned n; } oscilloscope;\n'
                'void scope_add_sample(oscilloscope*, uint8_t, int16_t, uint8_t);\n'
            )
            (root / 'nuklear_ui/debug_ui.h').write_text(
                '#include <stdint.h>\n'
                'typedef void (*window_close_handler)(uint8_t);\n'
                'uint8_t debug_create_window(uint8_t, char *, uint32_t, uint32_t, window_close_handler);\n'
            )
            (root / 'main.c').write_text(
                '#include <stdint.h>\n'
                'int main(void) {\n'
                '    if (debug_create_window(1, "unused", 320, 240, 0) != 0) return 1;\n'
                '    scope_add_sample(0, 0, 0, 0);\n'
                '    return 0;\n'
                '}\n'
            )
            target = root / 'stubtest'
            args = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-I', str(root), '-include', str(build_sega.BLASTEM_HEADLESS),
                    str(root / 'main.c'), '-o', str(target)]
            compiled = subprocess.run(args, text=True, capture_output=True, check=False)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(target)], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_blastem_manifest_rejects_stale_headless_stubs(self):
        """A modified shim after WASM generation must invalidate the release."""
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as name:
            fake = Path(name) / 'retro'
            shutil.copytree(root, fake, ignore=shutil.ignore_patterns('__pycache__', '.git'))
            output = fake / 'web' / 'blastem'
            output.mkdir(parents=True, exist_ok=True)
            (output / 'blastem.js').write_text('/* fixture only */\n')
            (output / 'blastem.wasm').write_bytes(b'\x00asm\x01\x00\x00\x00' + b'fixture')
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = {
                'engine': 'blastem', 'tag': 'v1.0.0',
                'pin': 'upstream-post-tag-libretro-fix', 'revision': '625fa5a85505',
                'upstream': 'https://www.retrodev.com/repos/blastem',
                'license': 'GPL-3.0-or-later',
                'license_sha256': sha(fake / 'LICENSES/BlastEm.txt'),
                'bridge_sha256': sha(fake / 'native/sega_libretro_bridge.c'),
                'headless_stubs_sha256': sha(fake / 'native/blastem_headless.h'),
                'artifacts': {
                    'blastem.js': sha(output / 'blastem.js'),
                    'blastem.wasm': sha(output / 'blastem.wasm'),
                },
            }
            (output / 'manifest.json').write_text(json.dumps(manifest))
            with (patch.object(release_audit, 'ROOT', fake),
                  patch.object(release_audit, 'WEB', fake / 'web')):
                errors = release_audit.audit(release=False)
                self.assertFalse([err for err in errors if err.startswith('blastem:')], errors)
                (fake / 'native/blastem_headless.h').write_text('/* changed after build */')
                errors = release_audit.audit(release=False)
                self.assertIn('blastem: headless stubs changed since build; rebuild WASM', errors)
                (fake / 'native/blastem_headless.h').write_text(
                    (root / 'native/blastem_headless.h').read_text()
                )
                del manifest['headless_stubs_sha256']
                (output / 'manifest.json').write_text(json.dumps(manifest))
                errors = release_audit.audit(release=False)
                self.assertIn('blastem: headless stubs changed since build; rebuild WASM', errors)


if __name__ == '__main__':
    unittest.main()
