"""BlastEm size-first build guardrails without an Emscripten installation."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_sega, release_audit


ROOT = Path(__file__).resolve().parents[1]


class BlastEmSizeBuildTests(unittest.TestCase):
    def test_core_build_forces_fresh_oz_lto_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'blastem'
            source.mkdir()
            core = source / 'ssh-blastem.a'
            core.write_bytes(b'!<arch>\n' + b'0' * 5000)
            tmp = Path(directory) / 'work'
            tmp.mkdir()
            with patch.object(build_sega, 'invoke') as command:
                self.assertEqual(build_sega.build_core('blastem', source, tmp), core)
            self.assertEqual(command.call_count, 1)
            args = command.call_args.args
            self.assertEqual(args[:3], ('emmake', 'make', '-C'))
            self.assertIn('-B', args)
            self.assertIn('OPT=-Oz -flto', args)
            self.assertIn('CPU=wasm', args)
            self.assertIn('Z80_DISPATCH=call', args)
            self.assertEqual((tmp / 'Makefile.libretro-ssh').read_text(),
                             build_sega.blastem_makefile_overlay())

    def test_size_optimization_applies_to_bridge_and_link_only_for_blastem(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            for engine in ('blastem', 'gearsystem'):
                with self.subTest(engine=engine), patch.object(build_sega, 'invoke') as command:
                    build_sega.link_web_core(engine, tmp, tmp / 'libretro.a', tmp)
                self.assertEqual(command.call_count, 2)
                compile_args, link_args = [call.args for call in command.call_args_list]
                self.assertEqual(compile_args[0], 'emcc')
                self.assertEqual(link_args[0], 'em++')
                if engine == 'blastem':
                    self.assertIn('-Oz', compile_args)
                    self.assertIn('-Oz', link_args)
                    self.assertIn('-flto', link_args)
                    self.assertNotIn('-O2', compile_args + link_args)
                    self.assertIn('-include', compile_args)
                else:
                    self.assertIn('-O2', compile_args)
                    self.assertIn('-O2', link_args)
                    self.assertNotIn('-Oz', compile_args + link_args)
                    self.assertNotIn('-flto', link_args)
                    self.assertNotIn('-include', compile_args)

    def test_old_optimization_manifest_blocks_release_but_not_source_check(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            manifest_file = fake / 'web/blastem/manifest.json'
            manifest = json.loads(manifest_file.read_text())
            # Force the pre-optimization condition even after developers later
            # commit freshly built -Oz WASM and a new manifest to the repo.
            manifest.pop('optimization', None)
            manifest.pop('build_script_sha256', None)
            manifest_file.write_text(json.dumps(manifest))
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertEqual(release_audit.audit(release=False), [])
                self.assertIn('blastem: -Oz/-flto build required; rebuild JS/WASM and manifest',
                              release_audit.audit(release=True, require_mame=False))
                # Locally rebuilt output receives both fields. Do not weaken
                # ordinary hash/source checks to accommodate old artifacts.
                manifest['optimization'] = ['-Oz', '-flto']
                manifest['build_script_sha256'] = hashlib.sha256(
                    (fake / 'scripts/build_sega.py').read_bytes()
                ).hexdigest()
                manifest_file.write_text(json.dumps(manifest))
                self.assertEqual(release_audit.audit(release=True, require_mame=False), [])
                manifest['optimization'] = ['-O2', '-flto']
                manifest_file.write_text(json.dumps(manifest))
                self.assertIn('blastem: -Oz/-flto build required; rebuild JS/WASM and manifest',
                              release_audit.audit(release=True, require_mame=False))
                manifest['optimization'] = ['-Oz', '-flto']
                manifest['build_script_sha256'] = '0' * 64
                manifest_file.write_text(json.dumps(manifest))
                self.assertIn('blastem: -Oz/-flto build required; rebuild JS/WASM and manifest',
                              release_audit.audit(release=True, require_mame=False))


if __name__ == '__main__':
    unittest.main()
