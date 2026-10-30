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

# Label-independent, but still verifies the real workflow image and target.
CI_WORKFLOW_URL = 'https://github.com/Junatum/retro-arcade/actions/workflows/verify.yml'
CI_STATUS_BADGE_RE = re.compile(
    r'\[!\[(?P<label>[^\]\n]+)\]\('
    + re.escape(CI_WORKFLOW_URL + '/badge.svg')
    + r'\)\]\('
    + re.escape(CI_WORKFLOW_URL)
    + r'\)'
)


class PackageTests(unittest.TestCase):
    def test_openwrt_static_js_modules_have_supported_mime_extension(self):
        # Stock uhttpd only maps .js to JavaScript MIME; .mjs fails ES module loading.
        import hashlib
        import json
        sources = list((ROOT / 'web').rglob('*'))
        self.assertFalse([p for p in sources if p.is_file() and p.suffix == '.mjs'])
        self.assertRegex((ROOT / 'web/index.html').read_text(), r'src="\./app\.js\?v=[0-9a-f]{12}"')
        self.assertEqual(json.loads((ROOT / 'package.json').read_text())['type'], 'module')
        manifest = json.loads((ROOT / 'web/mgba/manifest.json').read_text())
        self.assertEqual(
            hashlib.sha256((ROOT / 'web/mgba/mgba.js').read_bytes()).hexdigest(),
            manifest['artifacts']['mgba.js'],
        )
        self.assertEqual(audit(release=False), [])

    def test_release_ci_requires_all_assets_and_current_browser_cache(self):
        workflow = (ROOT / '.github/workflows/verify.yml').read_text()
        self.assertIn('python3 scripts/release_audit.py --release', workflow)
        self.assertIn('python3 scripts/cache_bust.py --check', workflow)
        self.assertIn('python3 tests/browser_e2e.py -v', workflow)
        self.assertNotIn('if [ -f web/vendor/jsnes/manifest.json ]', workflow)
        self.assertIn('python3 scripts/release_audit.py --existing', workflow)
        self.assertIn('scripts/release_audit.py --release', (ROOT/'Makefile').read_text())
        from scripts import cache_bust
        self.assertEqual(cache_bust.check(), [])
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            (fake / 'web/vendor/jsnes/manifest.json').unlink()
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertTrue(any('JSNES 2.1.0 vendor' in e for e in release_audit.audit(release=True, require_mame=False)))
            # Changed module content must invalidate the parent import hash.
            (fake / 'web/demo.js').write_text((fake / 'web/demo.js').read_text() + '\n// changed\n')
            self.assertIn('app.js', cache_bust.check(web=fake / 'web'))

    def test_sega_release_fails_closed_without_locally_built_wasm(self):
        # Released sources now include the locally built Sega cores. Test the
        # missing-WASM release gate in an isolated copy, not against a stale
        # assumption that the real checkout is still source-only.
        self.assertEqual(audit(), [])
        # The bundled BlastEm WASM is already the -Oz/-flto release build.
        # Never hide an optimization mismatch in the release gate.
        self.assertEqual(audit(release=True, require_mame=False), [])
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            for engine in release_audit.SEGA_ENGINES:
                wasm = fake / 'web' / engine / f'{engine}.wasm'
                self.assertTrue(wasm.is_file(), f'expected bundled WASM: {engine}')
                wasm.unlink()
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                errors = release_audit.audit(release=True, require_mame=False)
            for engine in release_audit.SEGA_ENGINES:
                self.assertTrue(any(f'{engine}: JS/WASM/manifest' in e for e in errors),
                                f'{engine} missing-WASM guard did not trigger: {errors}')
        builder = (ROOT / 'scripts/build_sega.py').read_text(encoding='utf-8')
        self.assertIn("GEARSYSTEM_TAG = '3.9.21'", builder)
        self.assertIn("BLASTEM_REV = '625fa5a85505'", builder)
        self.assertIn("'hg', 'id'", builder)
        self.assertIn('license_sha256', builder)

    def test_browser_e2e_waits_respect_strict_csp(self):
        page = (ROOT / 'web/index.html').read_text()
        e2e = (ROOT / 'tests/browser_e2e.py').read_text()
        self.assertIn("script-src 'self' 'wasm-unsafe-eval'", page)
        self.assertNotIn('.wait_for_function(', e2e)
        self.assertIn("page.locator('#player-section').wait_for(state='visible', timeout=12000)", e2e)

    def test_save_lifecycle_feedback_and_new_module_are_packaged(self):
        html = (ROOT / 'web/index.html').read_text()
        app = (ROOT / 'web/app.js').read_text()
        save_module = (ROOT / 'web/save-session.js').read_text()
        self.assertIn('id="save-status"', html)
        self.assertIn("window.confirm?.('게임을 저장하지 못했습니다.", app)
        self.assertIn('this.pending', save_module)
        self.assertIn('batteryReadStrict', save_module)

    def test_source_inventory_contains_only_approved_engines(self):
        self.assertEqual(audit(), [])
        for directory, expected in release_audit.EXPECTED_SOURCE_COMPONENTS.items():
            actual = {file.relative_to(ROOT / directory).as_posix()
                      for file in (ROOT / directory).rglob('*')
                      if file.is_file() and '__pycache__' not in file.parts}
            self.assertEqual(actual, expected, directory)
        # Both source-only checkout and completed one-time vendoring are valid.
        # audit() already checks the vendor manifest and each module hash if present.

    def test_unapproved_extra_emulation_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            extra = fake / 'native/obsolete_bridge.c'
            extra.write_text('// unreviewed core')
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertTrue(any('unexpected source inventory in native' in e
                                    for e in release_audit.audit(release=True, require_mame=False)))

    def test_revision_platforms_and_licenses(self):
        info = json.loads((ROOT / 'app-info.json').read_text())
        make = (ROOT / 'Makefile').read_text()
        self.assertEqual(info['version'], '1.2.0-r4')
        self.assertIn('PKG_VERSION:=1.2.0', make)
        self.assertIn('PKG_RELEASE:=4', make)
        self.assertEqual(info['license'], 'GPL-3.0-or-later AND GPL-2.0-or-later AND MPL-2.0 AND Apache-2.0 AND MIT')
        self.assertEqual(info['included_systems'], ['CHIP-8', 'Game Boy', 'Game Boy Color', 'Game Boy Advance', 'NES', 'Famicom', 'Game Gear', 'Master System', 'SG-1000', 'Mega Drive', 'Genesis', 'Arcade (MAME 0.289 selected drivers)'])
        self.assertNotIn('GL-MT300N-V2', info['supported_models'])
        self.assertIn('Browser-based CHIP-8, GB/GBC/GBA, NES, Sega', make)
        self.assertIn('LICENSES/mGBA.txt', make)
        self.assertIn('LICENSES/JSNES.txt', make)

    def test_readme_badges_reference_actual_project_metadata(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        workflow = ROOT / '.github/workflows/verify.yml'
        license_file = ROOT / 'LICENSE'
        self.assertTrue(workflow.is_file())
        self.assertTrue(license_file.is_file())
        # The visible CI badge label is editorial (e.g. "CI" or "Verify").
        # Verify the image and action URL instead of pinning the label.
        status_badge = CI_STATUS_BADGE_RE.search(readme)
        self.assertIsNotNone(status_badge, 'README CI badge must link to verify.yml')
        self.assertTrue(status_badge.group('label').strip())
        self.assertIn('![OpenWrt](https://img.shields.io/badge/OpenWrt-Compatible-blue)', readme)
        self.assertIn('![Offline](https://img.shields.io/badge/Offline-Ready-brightgreen)', readme)
        self.assertIn(
            '[![License](https://img.shields.io/github/license/Junatum/retro-arcade?label=License)](LICENSE)',
            readme,
        )
        self.assertLess(status_badge.start(), readme.index('## 지원 게임기'))

    def test_ci_badge_label_can_be_changed_without_weakening_link_validation(self):
        for label in ('CI', 'Verify', 'Build Status'):
            with self.subTest(label=label):
                badge = f'[![{label}]({CI_WORKFLOW_URL}/badge.svg)]({CI_WORKFLOW_URL})'
                self.assertIsNotNone(CI_STATUS_BADGE_RE.fullmatch(badge))
        # Changing the destination or image path must still fail verification.
        wrong_target = f'[![CI]({CI_WORKFLOW_URL}/badge.svg)](https://example.com)'
        wrong_image = f'[![CI]({CI_WORKFLOW_URL}/wrong.svg)]({CI_WORKFLOW_URL})'
        self.assertIsNone(CI_STATUS_BADGE_RE.fullmatch(wrong_target))
        self.assertIsNone(CI_STATUS_BADGE_RE.fullmatch(wrong_image))

    def test_license_and_browser_contract(self):
        readme = (ROOT / 'README.md').read_text()
        html = (ROOT / 'web/index.html').read_text()
        third_party = (ROOT / 'docs/THIRD_PARTY.md').read_text()
        self.assertIn('mGBA', readme)
        self.assertIn('하나의 mGBA 엔진', readme)
        self.assertIn("connect-src 'self'", html)
        self.assertRegex(html, r'app\.js\?v=[0-9a-f]{12}')
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
        current = audit(release=True, require_mame=False)
        if current:
            self.assertTrue(any('bridge changed since binary build' in error or 'JSNES 2.1.0 vendor' in error or 'JS/WASM/manifest' in error or 'blastem: -Oz/-flto build required' in error for error in current))

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
                self.assertFalse(any('invalid mGBA binary hash' in e
                                     for e in release_audit.audit(release=True, require_mame=False)))
                wasm = fake / 'web/mgba/mgba.wasm'
                wasm.write_bytes(b'bad bytes')
                self.assertTrue(any('invalid mGBA binary hash' in e for e in release_audit.audit(release=True, require_mame=False)))
                wasm.unlink()
                self.assertTrue(any('mGBA 0.10.5' in e for e in release_audit.audit(release=True, require_mame=False)))

    def test_bridge_change_requires_matching_binary_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            mf = fake / 'web/mgba/manifest.json'
            info = json.loads(mf.read_text())
            info['bridge_sha256'] = hashlib.sha256((fake/'native/mgba_bridge.c').read_bytes()).hexdigest()
            mf.write_text(json.dumps(info))
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertFalse(any('mGBA bridge changed' in e
                                     for e in release_audit.audit(release=True, require_mame=False)))
                (fake / 'native/mgba_bridge.c').write_text('// modified')
                self.assertTrue(any('mGBA bridge changed' in e for e in release_audit.audit(release=True, require_mame=False)))

    def test_chip8_paddle_rally_has_original_game_and_controls(self):
        demo = (ROOT / 'web/demo.js').read_text()
        app = (ROOT / 'web/app.js').read_text()
        page = (ROOT / 'web/index.html').read_text()
        readme = (ROOT / 'README.md').read_text()
        self.assertIn("DEMO_TITLE = '패들 랠리'", demo)
        self.assertIn('createPaddleRallyRom()', demo)
        self.assertIn("key 5 (W on the keyboard)", demo)
        self.assertIn("key 8 (S on the keyboard)", demo)
        self.assertIn('playChip8(DEMO_ROM,DEMO_TITLE,true)', app)
        self.assertRegex(app, r"from '\./demo\.js\?v=[0-9a-f]{12}'")
        self.assertIn('데모 게임 플레이', page)
        self.assertIn('id="demo-roles"', page)
        self.assertIn('오른쪽 · 플레이어', page)
        self.assertIn('왼쪽 · 컴퓨터', page)
        self.assertIn('demoActive && lit', app)
        self.assertIn("$('demo-roles').classList.toggle('hidden',!demoActive)", app)
        self.assertIn('id="demo-controls"', page)
        self.assertIn('demoControls.classList.toggle', app)
        self.assertIn('**패들 랠리**', readme)
        self.assertNotIn('내장 데모 2026', app)

    def test_score_separator_and_sticky_footer_layout(self):
        demo = (ROOT / 'web/demo.js').read_text()
        css = (ROOT / 'web/styles.css').read_text()
        page = (ROOT / 'web/index.html').read_text()
        self.assertIn("sprite('scoreColon',[0x00,0xC0,0x00,0xC0,0x00])", demo)
        self.assertIn("ref(0xA000,'scoreColon');op(0xD015)", demo)
        self.assertIn('.app{min-height:100vh;min-height:100dvh;display:flex;flex-direction:column}', css)
        self.assertIn('.app>main{flex:1 0 auto}', css)
        self.assertIn('.app>footer{margin-top:auto}', css)
        self.assertNotIn('.app>footer{position:fixed', css)
        self.assertRegex(page, r'src="\./app\.js\?v=[0-9a-f]{12}"')

    def test_fullscreen_controls_are_packaged(self):
        html = (ROOT / 'web/index.html').read_text()
        script = (ROOT / 'web/app.js').read_text()
        fullscreen = (ROOT / 'web/fullscreen.js').read_text()
        style = (ROOT / 'web/styles.css').read_text()
        self.assertIn('id="fullscreen"', html)
        self.assertIn('aria-controls="player-section"', html)
        self.assertRegex(script, r"import \{ setupFullscreen \} from '\./fullscreen\.js\?v=[0-9a-f]{12}'")
        self.assertIn("'fullscreen.js'", (ROOT / 'scripts/release_audit.py').read_text())
        self.assertIn('fullscreenchange', fullscreen)
        self.assertIn("event.key === 'Escape'", fullscreen)
        self.assertIn('requestFullscreen()', fullscreen)
        self.assertIn('object-fit:contain', style)
        self.assertIn('.theater-mode', style)
        self.assertIn('@media (pointer:fine) and (min-width:900px)', style)

    def test_system_selection_hides_only_after_player_starts(self):
        html = (ROOT / 'web/index.html').read_text()
        script = (ROOT / 'web/app.js').read_text()
        self.assertIn('class="library" id="system-library"', html)
        show_player = script.split('function showPlayer(system,label){', 1)[1].split('\n}', 1)[0]
        self.assertIn("$('system-library').classList.add('hidden')", show_player)
        self.assertIn("$('player-section').classList.remove('hidden')", show_player)
        # Pausing keeps the playing layout; returning home reloads the default selection view.
        self.assertNotIn("$('system-library').classList", script.split("$('toggle').onclick=", 1)[1].split('\n};', 1)[0])
        self.assertIn('window.location.reload()', script.split('async function exitGame()', 1)[1])

    def test_demo_is_only_available_for_chip8(self):
        html = (ROOT / 'web/index.html').read_text()
        script = (ROOT / 'web/app.js').read_text()
        css = (ROOT / 'web/styles.css').read_text()
        self.assertIn('id="load-buttons"', html)
        self.assertIn('id="demo"', html)
        self.assertIn("const hasDemo=system.id==='chip8'", script)
        self.assertIn("$('demo').disabled=!hasDemo", script)
        self.assertIn("$('demo').classList.toggle('hidden',!hasDemo)", script)
        self.assertIn("$('load-buttons').classList.toggle('buttons--single',!hasDemo)", script)
        self.assertIn("if(selected.id==='chip8')playChip8(DEMO_ROM", script)
        self.assertIn('.buttons.buttons--single{grid-template-columns:1fr}', css)

    def test_compact_header_intro_and_local_platform_icons(self):
        html = (ROOT / 'web/index.html').read_text()
        css = (ROOT / 'web/styles.css').read_text()
        app = (ROOT / 'web/app.js').read_text()
        self.assertIn('.header{height:84px;display:flex', css)
        self.assertNotIn('border-bottom:1px solid #2a2a3b', css)
        self.assertIn('별도 계정이나 게임 서버 없이 로컬에서 실행하며', html)
        self.assertNotIn('자체 CHIP-8, mGBA 기반', html)
        self.assertIn('grid-template-columns:repeat(4,minmax(0,1fr))', css)
        self.assertIn('const PLATFORM_ICONS = Object.freeze({', app)
        for key in ("chip8:", "'mgba-gb':", "mgba:", "nes:"):
            self.assertIn(key, app)
        self.assertIn('aria-hidden="true"', app)
        self.assertIn('icon.innerHTML=PLATFORM_ICONS[system.id]', app)
        self.assertIn('.system-icon svg{', css)
        self.assertIn("$('demo').classList.toggle('hidden',!hasDemo)", app)

    def test_platform_touch_controller_bundle_and_css(self):
        app = (ROOT / 'web/app.js').read_text()
        script = (ROOT / 'web/controller.js').read_text()
        css = (ROOT / 'web/styles.css').read_text()
        audit_source = (ROOT / 'scripts/release_audit.py').read_text()
        workflow = (ROOT / '.github/workflows/verify.yml').read_text()
        self.assertIn("import { renderController", app)
        self.assertIn('activeController?.releaseAll()', app)
        self.assertIn("'controller.js'", audit_source)
        self.assertIn('node --check web/controller.js', workflow)
        for selector in ('.controller-dpad', '.controller-face', '.controller-shoulders',
                         '.controller-meta', '.keypad--chip8', '.keypad--handheld'):
            self.assertIn(selector, css)
        self.assertIn("const SHOULDERS", script)
        self.assertIn("if (isGba)", script)


    def test_demo_match_result_and_colored_walls_are_demo_only(self):
        demo = (ROOT / 'web/demo.js').read_text()
        app = (ROOT / 'web/app.js').read_text()
        html = (ROOT / 'web/index.html').read_text()
        self.assertIn('DEMO_SERVE_DELAY_TICKS = 120', demo)
        self.assertIn('DEMO_WIN_SCORE = 5', demo)
        self.assertIn('DEMO_FINISHED_PC', demo)
        self.assertIn('demoActive && (y===6 || y===30', app)
        self.assertIn("$('demo-result-title').textContent=won?", app)
        self.assertIn('id="demo-result"', html)
        self.assertIn('id="demo-replay"', html)
        self.assertIn('role="status" aria-live="polite"', html)

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
        for heading in ('### 추가', '### 개선', '### 수정', '### 호환성', '### 테스트'):
            self.assertIn(heading, history)
        self.assertIn('1.2.0-r4', (ROOT / 'docs/SOURCE_OFFER.md').read_text())
        for path in ('README.md', 'docs/ARCHITECTURE.md', 'docs/RELEASE_CHECKLIST.md',
                     'docs/THIRD_PARTY.md', 'web/open-source.html'):
            source = (ROOT / path).read_text()
            self.assertIsNone(re.search(r'\b\d+\.\d+\.\d+-r\d+\b', source), path)
        self.assertIn('<span class="edition">v1.2.0-r4</span>', (ROOT / 'web/index.html').read_text())

    def test_release_guard_requires_correct_header_badge(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            html = fake / 'web/index.html'
            source = html.read_text(encoding='utf-8')
            current_badge = f'<span class="edition">v{release_audit.VERSION}</span>'
            self.assertEqual(source.count(current_badge), 1, 'test must replace the current badge')
            html.write_text(source.replace(current_badge, '<span class="edition">v0.1.0-r6</span>', 1),
                            encoding='utf-8')
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertTrue(any('header version badge must match' in error
                                    for error in release_audit.audit(release=True, require_mame=False)))

    def test_release_guard_rejects_unnecessary_visible_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            readme = fake / 'README.md'
            readme.write_text(readme.read_text() + '\n버전: 1.0.0-r1\n')
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertTrue(any('unnecessary product version shown in README.md' in error
                                    for error in release_audit.audit(release=True, require_mame=False)))


    def test_local_favicons_are_packaged_for_both_pages(self):
        from xml.etree import ElementTree
        svg = ROOT / 'web/favicon.svg'
        ico = ROOT / 'web/favicon.ico'
        self.assertEqual(ElementTree.parse(svg).getroot().tag,
                         '{http://www.w3.org/2000/svg}svg')
        contents = ico.read_bytes()
        self.assertGreater(len(contents), 200)
        self.assertEqual(contents[:4], b'\x00\x00\x01\x00')
        self.assertGreaterEqual(int.from_bytes(contents[4:6], 'little'), 2)
        for page in ('index.html', 'open-source.html'):
            html = (ROOT / 'web' / page).read_text()
            self.assertIn('href="./favicon.svg"', html)
            self.assertIn('href="./favicon.ico"', html)
        self.assertEqual(audit(release=False), [])

    def test_release_rejects_missing_favicon_or_page_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                (fake / 'web/favicon.ico').unlink()
                self.assertTrue(any('favicon' in error for error in audit(release=True, require_mame=False)))
                (fake / 'web/favicon.ico').write_bytes((ROOT / 'web/favicon.ico').read_bytes())
                source = fake / 'web/open-source.html'
                source.write_text(source.read_text().replace('href="./favicon.svg"', 'href="./missing.svg"'))
                self.assertTrue(any('missing favicon link' in error for error in audit(release=True, require_mame=False)))


    def test_jsnes_release_blocks_missing_modules_and_detects_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / 'repo'
            shutil.copytree(ROOT, fake, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            # Always begin with a pre-vendoring checkout, even when the
            # developer has already installed and committed JSNES modules.
            shutil.rmtree(fake / 'web/vendor', ignore_errors=True)
            with patch.object(release_audit, 'ROOT', fake), patch.object(release_audit, 'WEB', fake / 'web'):
                self.assertTrue(any('JSNES 2.1.0 vendor' in error for error in audit(release=True, require_mame=False)))
                vendor = fake / 'web/vendor/jsnes'
                (vendor / 'src').mkdir(parents=True)
                fake_module = b'export default class NES {}\n'
                for name in ('nes.js', 'controller.js', 'utils.js'):
                    (vendor / 'src' / name).write_bytes(fake_module)
                manifest = {
                    'package':'jsnes', 'version':'2.1.0', 'license':'Apache-2.0',
                    'upstream':'https://github.com/bfirsh/jsnes',
                    'npm_integrity':'sha512-'+'A'*86+'==',
                    'files': {f'src/{name}': hashlib.sha256(fake_module).hexdigest()
                              for name in ('nes.js', 'controller.js', 'utils.js')},
                }
                (vendor / 'manifest.json').write_text(json.dumps(manifest))
                self.assertFalse(any('JSNES' in e for e in audit(release=True, require_mame=False)))
                (vendor / 'src/nes.js').write_bytes(b'altered')
                self.assertTrue(any('invalid JSNES source hash' in e for e in audit(release=True, require_mame=False)))

if __name__ == '__main__':
    unittest.main()
