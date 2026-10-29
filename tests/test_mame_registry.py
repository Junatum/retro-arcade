"""MAME's supported machine IDs come only from the shipped WASM registry."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import mame_registry, release_audit

ROOT = Path(__file__).resolve().parents[1]


class MachineRegistryTests(unittest.TestCase):
    def test_exact_bundled_wasm_registration_list(self):
        ids = mame_registry.embedded_machines(mame_registry.WASM.read_bytes())
        self.assertEqual(len(ids), 454)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({'pacman', 'galaxian', 'puckman', 'mooncrst', 'mspacman'}.issubset(ids))
        self.assertNotIn('tetris', ids)
        self.assertTrue(mame_registry.check())

    def test_damaged_binary_and_changed_registry_are_rejected(self):
        with tempfile.TemporaryDirectory() as dirname:
            wasm = Path(dirname) / 'mame.wasm'
            names = Path(dirname) / 'machines.js'
            wasm.write_bytes(mame_registry.WASM.read_bytes())
            names.write_text(mame_registry.REGISTRY.read_text())
            self.assertTrue(mame_registry.check(wasm, names))
            names.write_text(names.read_text().replace("'mooncrst'", "'notbuilt'"))
            self.assertFalse(mame_registry.check(wasm, names))
            wasm.write_bytes(b'\x00asm\x01\x00\x00\x00' + b'\x00' * 128)
            with self.assertRaisesRegex(ValueError, 'registration table'):
                mame_registry.check(wasm, names)

    def test_release_catches_tampered_machine_list(self):
        with tempfile.TemporaryDirectory() as dirname:
            fake = Path(dirname) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            target = fake / 'web/mame/machines.js'
            target.write_text(target.read_text().replace("'mooncrst'", "'notbuilt'"))
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertTrue(any('machine list does not match' in e
                                    for e in release_audit.audit(release=True)))


if __name__ == '__main__':
    unittest.main()
