import hashlib
import json
import pathlib
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch
from scripts import release_audit
from scripts.release_audit import audit

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_source_inventory_contains_only_approved_engines(self):
        self.assertEqual(audit(), [])
        for directory, expected in release_audit.EXPECTED_SOURCE_COMPONENTS.items():
            actual = {file.relative_to(ROOT / directory).as_posix()
                      for file in (ROOT / directory).rglob('*')
                      if file.is_file() and '__pycache__' not in file.parts}
            self.assertEqual(actual, expected, directory)
        self.assertFalse((ROOT / 'web/vendor').exists())

    def test_unapproved_extra_emulation_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            extra = fake / 'native/obsolete_bridge.c'
            extra.write_text('// unreviewed core')
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertTrue(any('unexpected source inventory in native' in e
                                    for e in release_audit.audit(release=True)))

    def test_revision_platforms_and_licenses(self):
        info = json.loads((ROOT / 'app-info.json').read_text())
        make = (ROOT / 'Makefile').read_text()
        self.assertEqual(info['version'], '0.1.0-r2')
        self.assertIn('PKG_RELEASE:=2', make)
        self.assertEqual(info['license'], 'GPL-3.0-or-later AND MPL-2.0')
        self.assertEqual(info['included_systems'], ['CHIP-8', 'Game Boy', 'Game Boy Color', 'Game Boy Advance'])
        self.assertNotIn('GL-MT300N-V2', info['supported_models'])
        self.assertIn('Browser-based CHIP-8 and mGBA', make)
        self.assertIn('LICENSES/mGBA.txt', make)

    def test_license_and_browser_contract(self):
        readme = (ROOT / 'README.md').read_text()
        html = (ROOT / 'web/index.html').read_text()
        third_party = (ROOT / 'docs/THIRD_PARTY.md').read_text()
        self.assertIn('mGBA', readme)
        self.assertIn('하나의 mGBA 엔진', readme)
        self.assertIn("connect-src 'self'", html)
        self.assertIn("'wasm-unsafe-eval'", html)
        for source in (readme, html, third_party, (ROOT / 'docs/ARCHITECTURE.md').read_text()):
            self.assertIn('mGBA', source)

    def test_docs_linked_and_packaged(self):
        mk = (ROOT / 'Makefile').read_text()
        notice = (ROOT / 'web/open-source.html').read_text()
        readme = (ROOT / 'README.md').read_text()
        arch = (ROOT / 'docs/ARCHITECTURE.md').read_text()
        for name in ('INSTALLATION_INFO.md', 'RELEASE_CHECKLIST.md', 'SOURCE_OFFER.md'):
            self.assertFalse((ROOT / name).exists())
            self.assertTrue((ROOT / 'docs' / name).is_file())
            self.assertIn(f'docs/{name}', readme)
        self.assertIn('docs/ARCHITECTURE.md', readme)
        self.assertIn('IndexedDB', arch)
        for name in ('INSTALLATION_INFO.md', 'SOURCE_OFFER.md'):
            self.assertIn(f'./docs/{name}', mk)
            self.assertIn(f'./docs/{name}', notice)
        self.assertIn('$(INSTALL_DIR) $(1)/www/retro-arcade/docs', mk)

    def test_release_gate_requires_rebuild_when_abi_changes(self):
        # Source check works before local emcc rebuild; release check never accepts stale ABI.
        self.assertEqual(audit(), [])
        current = audit(release=True)
        if current:
            self.assertTrue(any('bridge changed since binary build' in error for error in current))

    def test_release_gate_and_hash_integrity_with_isolated_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            manifest_file = fake / 'web/mgba/manifest.json'
            manifest = json.loads(manifest_file.read_text())
            # Simulate a matching completed local build: manifest and artifacts stay isolated.
            manifest['bridge_sha256'] = hashlib.sha256((fake / 'native/mgba_bridge.c').read_bytes()).hexdigest()
            manifest_file.write_text(json.dumps(manifest))
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertEqual(release_audit.audit(release=True), [])
                wasm = fake / 'web/mgba/mgba.wasm'
                wasm.write_bytes(b'bad bytes')
                self.assertTrue(any('invalid mGBA binary hash' in e for e in release_audit.audit(release=True)))
                wasm.unlink()
                self.assertTrue(any('mGBA 0.10.5' in e for e in release_audit.audit(release=True)))

    def test_bridge_change_requires_matching_binary_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            mf = fake / 'web/mgba/manifest.json'
            info = json.loads(mf.read_text())
            info['bridge_sha256'] = hashlib.sha256((fake/'native/mgba_bridge.c').read_bytes()).hexdigest()
            mf.write_text(json.dumps(info))
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertEqual(release_audit.audit(release=True), [])
                (fake / 'native/mgba_bridge.c').write_text('// modified')
                self.assertTrue(any('mGBA bridge changed' in e for e in release_audit.audit(release=True)))

    def test_fullscreen_controls_are_packaged(self):
        html = (ROOT / 'web/index.html').read_text()
        script = (ROOT / 'web/app.mjs').read_text()
        fullscreen = (ROOT / 'web/fullscreen.mjs').read_text()
        style = (ROOT / 'web/styles.css').read_text()
        self.assertIn('id="fullscreen"', html)
        self.assertIn('aria-controls="player-section"', html)
        self.assertIn("import { setupFullscreen } from './fullscreen.mjs'", script)
        self.assertIn("'fullscreen.mjs'", (ROOT / 'scripts/release_audit.py').read_text())
        self.assertIn('fullscreenchange', fullscreen)
        self.assertIn("event.key === 'Escape'", fullscreen)
        self.assertIn('requestFullscreen()', fullscreen)
        self.assertIn('object-fit:contain', style)
        self.assertIn('.theater-mode', style)
        self.assertIn('@media (pointer:fine) and (min-width:900px)', style)

    def test_system_selection_hides_only_after_player_starts(self):
        html = (ROOT / 'web/index.html').read_text()
        script = (ROOT / 'web/app.mjs').read_text()
        self.assertIn('class="library" id="system-library"', html)
        show_player = script.split('function showPlayer(system,label){', 1)[1].split('\n}', 1)[0]
        self.assertIn("$('system-library').classList.add('hidden')", show_player)
        self.assertIn("$('player-section').classList.remove('hidden')", show_player)
        # Pausing keeps the playing layout; returning home reloads the default selection view.
        self.assertNotIn("$('system-library').classList", script.split("$('toggle').onclick=", 1)[1].split('\n};', 1)[0])
        self.assertIn('window.location.reload()', script.split('async function exitGame()', 1)[1])

    def test_platform_touch_controller_bundle_and_css(self):
        app = (ROOT / 'web/app.mjs').read_text()
        script = (ROOT / 'web/controller.mjs').read_text()
        css = (ROOT / 'web/styles.css').read_text()
        audit_source = (ROOT / 'scripts/release_audit.py').read_text()
        workflow = (ROOT / '.github/workflows/verify.yml').read_text()
        self.assertIn("import { renderController", app)
        self.assertIn('activeController?.releaseAll()', app)
        self.assertIn("'controller.mjs'", audit_source)
        self.assertIn('node --check web/controller.mjs', workflow)
        for selector in ('.controller-dpad', '.controller-face', '.controller-shoulders',
                         '.controller-meta', '.keypad--chip8', '.keypad--handheld'):
            self.assertIn(selector, css)
        self.assertIn("const SHOULDERS", script)
        self.assertIn("if (isGba)", script)

    def test_stylesheet_urls_track_css_content_to_avoid_stale_controller_layout(self):
        # After APK upgrades, cached old CSS rendered new controller groups as
        # 4-column grid cells instead of the intended handheld D-pad layout.
        stylesheet = (ROOT / 'web/styles.css').read_bytes()
        expected = hashlib.sha256(stylesheet).hexdigest()[:12]
        old_css = stylesheet.split(b'/* Platform-aware handheld controls.', 1)[0]
        self.assertNotEqual(expected, hashlib.sha256(old_css).hexdigest()[:12])
        for page in ('index.html', 'open-source.html'):
            html = (ROOT / 'web' / page).read_text()
            matches = re.findall(r'href="\./styles\.css\?v=([0-9a-f]{12})"', html)
            self.assertEqual(matches, [expected], page)

    def test_packaging_only_verifies_binaries(self):
        make = (ROOT / 'Makefile').read_text()
        compile_section = make.split('define Build/Compile\n', 1)[1].split('\nendef', 1)[0]
        self.assertIn('scripts/release_audit.py --release', compile_section)
        for disallowed in ('build_mgba.py', 'emcc', 'curl', 'wget'):
            self.assertNotIn(disallowed, compile_section)
        self.assertIn('python3 scripts/release_audit.py --check', (ROOT/'.github/workflows/verify.yml').read_text())

    def test_unexpected_rom_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            (fake / 'web/game.gb').write_bytes(b'ROM')
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertTrue(any('ROM/compiled package' in e for e in release_audit.audit()))

    def test_consolidated_release_history_and_document_versions(self):
        history = (ROOT / 'CHANGELOG.md').read_text()
        self.assertEqual(re.findall(r'^## (0\.1\.0-r\d+)\b', history, re.M),
                         ['0.1.0-r2', '0.1.0-r1'])
        for heading in ('### 추가', '### 개선', '### 수정', '### 호환성', '### 테스트'):
            self.assertIn(heading, history)
        for path in ('README.md', 'docs/ARCHITECTURE.md', 'docs/RELEASE_CHECKLIST.md',
                     'docs/SOURCE_OFFER.md', 'docs/THIRD_PARTY.md', 'web/index.html',
                     'web/open-source.html'):
            source = (ROOT / path).read_text()
            self.assertIn('0.1.0-r2', source, path)
            for rev in range(3, 9):
                self.assertNotIn(f'0.1.0-r{rev}', source, path)


if __name__ == '__main__':
    unittest.main()
