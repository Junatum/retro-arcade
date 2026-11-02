"""Atari license provenance and fail-closed packaging contract; no game ROMs."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_atari, release_audit

ROOT = Path(__file__).resolve().parents[1]


class AtariSecurityTests(unittest.TestCase):
    def test_runtime_guard_allows_cpu_instruction_fetch_but_blocks_network(self):
        # The emulator uses ordinary CPU opcode fetching, which is not a
        # browser network request. The original guard rejected `.fetch()`.
        legitimate = [
            'class Cpu{fetch(){return this.memory.read(this.pc++)}step(){return this.fetch()}}',
            'const cpu={fetch(){return 42}};cpu.fetch();',
            'class Cpu{fetch(a){return a}};new Cpu().fetch(3);',
            'let prefetchCount=1;const fetchOpcode=()=>prefetchCount;',
        ]
        for js in legitimate:
            with self.subTest(legitimate=js):
                self.assertIsNone(build_atari.denied_runtime_reason(js))

        malicious = [
            'fetch("https://example.invalid/rom.a26")',
            'fetch?.("/games/index.json")',
            'window.fetch("https://example.invalid")',
            'globalThis["fetch"]("/game.a26")',
            'self.fetch("/game.a26")',
            'new XMLHttpRequest()',
            'new WebSocket("wss://example.invalid")',
            'navigator.sendBeacon("/stats", "rom")',
            'importScripts("https://example.invalid/x.js")',
            'const x="games-catalog"',
            'const x="google-analytics"',
            'const x="free games"',
            'const x="fetch-games"',
        ]
        for js in malicious:
            with self.subTest(malicious=js):
                self.assertIsNotNone(build_atari.denied_runtime_reason(js))

    def test_release_and_build_share_exact_same_runtime_guard(self):
        self.assertIs(release_audit.denied_runtime_reason, build_atari.denied_runtime_reason)
        source = (ROOT / 'scripts/release_audit.py').read_text()
        self.assertIn('denied_runtime_reason(from_bytes)', source)
        self.assertNotIn("re.search(r'\\bfetch", source)

    def test_release_fails_closed_until_offline_engine_is_built(self):
        # This test must work both before and after a real local Atari build.
        # Build output is intentionally not removed from the developer's tree:
        # simulate the missing engine only inside an isolated web root.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'copy'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            web = root / 'web'
            shutil.rmtree(web / 'atari2600', ignore_errors=True)
            with patch.object(release_audit, 'ROOT', root), patch.object(release_audit, 'WEB', web):
                self.assertEqual(release_audit.audit(release=False), [])
                issues = release_audit.audit(release=True)
            self.assertTrue(any('atari2600: locally built' in issue for issue in issues), issues)
        self.assertIn('python3 $(CURDIR)/scripts/release_audit.py --release', (ROOT / 'Makefile').read_text())

    def test_no_rom_catalog_or_download_path_in_release_sources(self):
        build = (ROOT / 'scripts/build_atari.py').read_text()
        bridge = (ROOT / 'native/atari_bridge.ts').read_text()
        app = (ROOT / 'web/app.js').read_text()
        self.assertNotIn('fetch-games.mjs', bridge)
        self.assertNotIn('fetchGame(', bridge)
        self.assertNotIn('trackGameLoaded', bridge)
        self.assertNotIn('fetch:games', (ROOT / 'package.json').read_text())
        self.assertNotIn('fetch:games', app)
        self.assertIn('name.startswith((\'src/ui/\'', build)
        self.assertIn('DENIED_RUNTIME', build)
        self.assertIn("'no_game_roms':True", build)
        self.assertIn("'no_downloads':True", build)
        self.assertIn("'no_telemetry':True", build)
        self.assertIn('Atari 2600', (ROOT / 'docs/THIRD_PARTY.md').read_text())
        self.assertIn('MIT License', (ROOT / 'LICENSES/Atari2600.txt').read_text())
        self.assertIn('Atari2600.txt', (ROOT / 'Makefile').read_text())

    def test_rejects_prohibited_roms_and_upstream_web_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            extra = Path(tmp) / 'web'
            # Copy web root to exercise the full inventory gate.
            shutil.copytree(ROOT / 'web', extra)
            (extra / 'atari2600').mkdir(exist_ok=True)
            (extra / 'atari2600' / 'example.a26').write_bytes(b'test ROM placeholder')
            (extra / 'atari2600' / 'games.js').write_text('fetch("https://example.com/")')
            with patch.object(release_audit, 'WEB', extra):
                errors = release_audit.audit(release=False)
            self.assertTrue(any('prohibited ROM/game content' in error for error in errors), errors)
            self.assertTrue(any('unapproved Atari asset' in error for error in errors), errors)

    def test_tampered_engine_fails_integrity_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'copy'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git','__pycache__'))
            dest = root / 'web/atari2600'
            dest.mkdir(exist_ok=True)
            data = (b'export class RetroAtariCore{};' * 100)
            (dest / 'engine.js').write_bytes(data)
            manifest = {
                'engine':'atari2600','upstream':'https://github.com/mohrt/atari2600',
                'revision':'a'*40,'license':'MIT',
                'source_inventory_sha256':'b'*64,'source_files':15,
                'compiled_sources':{name:'c'*64 for name in (
                    'emulator.ts','atari2600.ts','cart/detect.ts','render/screen.ts','io/controllers/ports.ts')},
                'no_game_roms':True,'no_downloads':True,'no_telemetry':True,
                'license_sha256':release_audit.sha256(root/'LICENSES/Atari2600.txt'),
                'bridge_sha256':release_audit.sha256(root/'native/atari_bridge.ts'),
                'build_script_sha256':release_audit.sha256(root/'scripts/build_atari.py'),
                'artifacts':{'engine.js':hashlib.sha256(data).hexdigest()},
            }
            (dest/'manifest.json').write_text(json.dumps(manifest))
            with patch.object(release_audit,'ROOT',root),patch.object(release_audit,'WEB',root/'web'):
                self.assertEqual(release_audit.audit(release=False), [])
                # A genuinely clean bundled CPU .fetch() is allowed by both
                # build and release checks when its checksum is refreshed.
                safe = data + b'class Cpu{fetch(){return 1}step(){return this.fetch()}}'
                (dest/'engine.js').write_bytes(safe)
                manifest['artifacts']['engine.js'] = hashlib.sha256(safe).hexdigest()
                (dest/'manifest.json').write_text(json.dumps(manifest))
                clean_errors = release_audit.audit(release=True)
                self.assertFalse(any('atari2600:' in e for e in clean_errors),clean_errors)
                # A new bare network fetch is rejected even if other release
                # assets are missing in the isolated test fixture.
                unsafe = safe+b'fetch("https://evil.invalid/")'
                (dest/'engine.js').write_bytes(unsafe)
                # An attacker cannot bypass the runtime policy merely by
                # updating the file hash in manifest.json.
                manifest['artifacts']['engine.js'] = hashlib.sha256(unsafe).hexdigest()
                (dest/'manifest.json').write_text(json.dumps(manifest))
                self.assertTrue(any('forbidden download' in e
                                    for e in release_audit.audit(release=True)), 'network code accepted')

    def test_pinned_source_must_be_clean_and_rom_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'upstream'
            (src / 'src/cart').mkdir(parents=True)
            (src / 'src/io/controllers').mkdir(parents=True)
            (src / 'src/render').mkdir(parents=True)
            names = ['emulator.ts','atari2600.ts','cart/detect.ts','io/controllers/ports.ts',
                     'render/screen.ts'] + [f'component{i}.ts' for i in range(6)]
            for name in names:
                dest = src/'src'/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text('export const n = 1;\n')
            shutil.copy2(ROOT/'LICENSES/Atari2600.txt',src/'LICENSE')
            (src/'package.json').write_text('{"name":"atari2600","private":true,"devDependencies":{}}')
            for cmd in (['git','init','-q'],['git','add','.'],['git','-c','user.email=test@example.com','-c','user.name=Test','commit','-qm','fixture']):
                subprocess.run(cmd,cwd=src,check=True,capture_output=True)
            head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
            self.assertEqual(len(build_atari.source_audit(src,head)),len(names))
            with self.assertRaisesRegex(ValueError,'does not match'):
                build_atari.source_audit(src,'0'*40)
            game = src/'src/sample.a26'
            game.write_bytes(b'not a game')
            with self.assertRaisesRegex(ValueError,'uncommitted'):
                build_atari.source_audit(src,head)
            subprocess.run(['git','add','.'],cwd=src,check=True,capture_output=True)
            subprocess.run(['git','-c','user.email=test@example.com','-c','user.name=Test','commit','-qm','fixture2'],cwd=src,check=True,capture_output=True)
            newhead = subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
            with self.assertRaisesRegex(ValueError,'ROM content'):
                build_atari.source_audit(src,newhead)


if __name__=='__main__':
    unittest.main()
