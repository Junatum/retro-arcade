"""Regression tests for compiling Sega's Libretro bridge as C.

These tests need neither Emscripten nor the upstream Gearsystem/BlastEm trees.
They intentionally live in a separate file to avoid merge conflicts with
previous Sega build tests or locally added test cases.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_sega


class SegaBridgeCompilerTests(unittest.TestCase):
    def test_compiles_bridge_as_c_then_links_both_engines(self):
        for engine in ('gearsystem', 'blastem'):
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as path:
                temp = Path(path)
                header = temp / 'upstream'
                core = temp / 'core.a'
                bridge_object = temp / 'sega_libretro_bridge.o'
                with patch.object(build_sega, 'invoke') as command:
                    js = build_sega.link_web_core(engine, header, core, temp)
                self.assertEqual(js, temp / f'{engine}.js')
                self.assertEqual(command.call_count, 2)
                cc = command.call_args_list[0].args
                linker = command.call_args_list[1].args
                self.assertEqual(cc[0], 'emcc')
                self.assertIn('-std=c11', cc)
                self.assertIn('-c', cc)
                self.assertIn(str(build_sega.BRIDGE), cc)
                self.assertIn('-I' + str(header), cc)
                self.assertEqual(cc[-2:], ('-o', str(bridge_object)))
                self.assertEqual(linker[0], 'em++')
                self.assertIn(str(bridge_object), linker)
                self.assertIn(str(core), linker)
                self.assertNotIn(str(build_sega.BRIDGE), linker)
                self.assertNotIn('-std=c++11', linker)
                self.assertIn(f'-sEXPORT_NAME=create{engine.title()}', linker)
                self.assertIn('-sEXPORTED_FUNCTIONS=' + json.dumps(
                    build_sega.EXPORTS, separators=(',', ':')), linker)

    def test_compiler_failure_prevents_linking(self):
        with tempfile.TemporaryDirectory() as path:
            temp = Path(path)
            with patch.object(build_sega, 'invoke', side_effect=ValueError('C error')) as command:
                with self.assertRaisesRegex(ValueError, 'C error'):
                    build_sega.link_web_core('gearsystem', temp, temp / 'core.a', temp)
            self.assertEqual(command.call_count, 1)
            self.assertEqual(command.call_args.args[0], 'emcc')


if __name__ == '__main__':
    unittest.main()
