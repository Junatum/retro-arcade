"""mGBA packaging contracts (do not claim an actual WASM build)."""
import pathlib
import unittest
from scripts import build_mgba

ROOT = pathlib.Path(__file__).resolve().parents[1]

class MgbaBuildTests(unittest.TestCase):
    def test_pinned_release_and_offline_build(self):
        source = (ROOT/'scripts/build_mgba.py').read_text()
        self.assertEqual(build_mgba.VERSION, '0.10.5')
        self.assertEqual(build_mgba.UPSTREAM, 'https://github.com/mgba-emu/mgba')
        self.assertIn('emcmake', source)
        self.assertIn('DISABLE_FRONTENDS=ON', source)
        self.assertIn('DISABLE_DEPS=ON', source)
        self.assertIn("'-DBUILD_SHARED=OFF'", source)
        # CMake 4 cannot configure mGBA 0.10.5 without a >=3.5 policy floor.
        self.assertIn("'-DCMAKE_POLICY_VERSION_MINIMUM=3.5'", source)
        # mGBA's C11 build on Emscripten needs feature-test macros.
        self.assertIn("'-DCMAKE_C_FLAGS=-D_GNU_SOURCE'", source)
        self.assertIn("'-D_GNU_SOURCE','-DBUILD_STATIC'", source)
        # The 0.10.5 CMake variables must actually select a static
        # library without GL backends or debugger ABI differences.
        for flag in ('-DBUILD_STATIC=ON', '-DBUILD_SHARED=OFF',
                     '-DBUILD_GL=OFF', '-DBUILD_GLES2=OFF',
                     '-DBUILD_GLES3=OFF', '-DUSE_DEBUGGERS=OFF',
                     '-DENABLE_SCRIPTING=OFF'):
            with self.subTest(flag=flag):
                self.assertIn(repr(flag), source)
        self.assertNotIn("'-DUSE_GL=OFF'", source)
        self.assertNotIn("'-DUSE_GLES2=OFF'", source)
        self.assertNotIn("(source/'CMakeLists.txt').write_text", source)
        self.assertNotIn('git clone', source.split('def main():', 1)[1])
        self.assertNotIn('curl ', source)
        self.assertNotIn('wget ', source)

    def test_bridge_api_is_bounded_and_bios_free(self):
        code = (ROOT/'native/mgba_bridge.c').read_text()
        self.assertIn('mPLATFORM_GB : mPLATFORM_GBA', code)
        self.assertIn('GBA_W 240u', code)
        self.assertIn('GBA_H 160u', code)
        self.assertIn('32 << 20', code)
        self.assertIn('savedataClone', code)
        self.assertIn('savedataRestore', code)
        self.assertIn('skipBios = true', code)
        self.assertIn('ssh_mgba_destroy', code)
        # mGBA 0.10.5 exposes color_t in mgba/core/interface.h
        # (transitively included from core.h); mgba-util/image.h does not exist.
        self.assertNotIn('#include <mgba-util/image.h>', code)
        self.assertNotIn('mColor ', code)
        self.assertIn('static color_t video[GBA_W * GBA_H]', code)
        self.assertIn('desiredVideoDimensions', code)
        self.assertIn('ssh_mgba_width', code)
        self.assertIn('ssh_mgba_height', code)
        self.assertIn('video[(size_t)y * GBA_W + x]', code)
        self.assertIn('_Static_assert(sizeof(color_t) == 4', code)

    def test_gb_and_gba_share_mgba_core(self):
        system = (ROOT/'web/systems.mjs').read_text()
        bridge = (ROOT/'native/mgba_bridge.c').read_text()
        self.assertIn("id:'mgba-gb'", system)
        self.assertIn("id:'mgba'", system)
        self.assertIn('mPLATFORM_GB', bridge)
        self.assertIn('mPLATFORM_GBA', bridge)
        self.assertIn("'_ssh_mgba_width'", (ROOT/'scripts/build_mgba.py').read_text())
        self.assertIn("'_ssh_mgba_height'", (ROOT/'scripts/build_mgba.py').read_text())
