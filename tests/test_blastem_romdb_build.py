"""BlastEm ROM database generation on BSD/macOS and GNU sed.

This suite does not require the upstream checkout or the Emscripten SDK.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

from scripts import build_sega


class BlastEmRomDatabaseBuildTests(unittest.TestCase):
    def test_makefile_overlay_overrides_only_rom_database_rule(self):
        overlay = build_sega.blastem_makefile_overlay()
        self.assertIn('include Makefile\n', overlay)
        self.assertIn('rom.db.c: rom.db\n', overlay)
        self.assertIn("\tsed -e ", overlay)
        self.assertIn("< $< > $@", overlay)
        self.assertIn('ssh-blastem.a: $(LIBOBJS:%.o=$(LIBOBJDIR)/%.o)', overlay)
        self.assertIn('\t$(AR) rcs $@ $^', overlay)

    @unittest.skipUnless(shutil.which('make') and shutil.which('sed'), 'make and sed required')
    def test_rom_database_generation_passes_bsd_sed_argument_order(self):
        """Simulate BSD sed rejecting upstream's `sed rom.db -e ...` order."""
        with tempfile.TemporaryDirectory(prefix='blastem-romdb-') as directory:
            root = Path(directory)
            (root / 'Makefile').write_text(
                "%.db.c: %.db\n\t@echo 'upstream implicit rule should not execute' >&2; exit 1\n",
                encoding='utf-8',
            )
            (root / 'Makefile.libretro-ssh').write_text(
                build_sega.blastem_makefile_overlay(), encoding='utf-8'
            )
            (root / 'rom.db').write_text('A "quoted" game\nB\n', encoding='utf-8')
            shim_dir = root / 'bin'
            shim_dir.mkdir()
            sed = shim_dir / 'sed'
            sed.write_text(
                '#!/bin/sh\n'
                '[ "$1" = "-e" ] || { echo "BSD sed option order" >&2; exit 99; }\n'
                'exec "$REAL_SED" "$@"\n', encoding='utf-8'
            )
            sed.chmod(0o755)
            environment = os.environ.copy()
            environment['REAL_SED'] = shutil.which('sed')
            environment['PATH'] = str(shim_dir) + os.pathsep + environment.get('PATH', '')
            result = subprocess.run(
                ['make', '-f', 'Makefile.libretro-ssh', 'rom.db.c'],
                cwd=root, env=environment, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(
                (root / 'rom.db.c').read_bytes(),
                b'const char rom_db_data[] = "A \\"quoted\\" game\\n"\n"B\\n";\n',
            )


if __name__ == '__main__':
    unittest.main()
