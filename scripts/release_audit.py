#!/usr/bin/env python3
"""Verify offline Retro Arcade inventory mGBA and JSNES provenance before release."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'
VERSION = '0.1.0-r3'
EXPECTED_WEB = {
    'index.html', 'styles.css', 'app.js', 'fullscreen.js', 'controller.js', 'chip8.js', 'systems.js',
    'demo.js', 'open-source.html', 'battery-store.js', 'mgba-player.js', 'jsnes-player.js', 'nes-audio.js',
}
MGBA_VENDOR = {'mgba/mgba.js', 'mgba/mgba.wasm', 'mgba/manifest.json'}
EXPECTED_SOURCE_COMPONENTS = {
    'native': {'mgba_bridge.c'},
    'scripts': {'build_mgba.py', 'release_audit.py', 'vendor_jsnes.py'},
    'LICENSES': {'mGBA.txt', 'JSNES.txt'},
}


def audit(release: bool = False) -> list[str]:
    errors = []
    try:
        meta = json.loads((ROOT / 'app-info.json').read_text(encoding='utf-8'))
        mk = (ROOT / 'Makefile').read_text(encoding='utf-8')
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        page = (WEB / 'index.html').read_text(encoding='utf-8')
        notice = (WEB / 'open-source.html').read_text(encoding='utf-8')
        license_text = (ROOT / 'LICENSE').read_text(encoding='utf-8')
        mgba_license = (ROOT / 'LICENSES/mGBA.txt').read_text(encoding='utf-8')
    except (OSError, ValueError) as exc:
        return [f'missing or invalid release source: {exc}']
    if meta.get('version') != VERSION or meta.get('license') != 'GPL-3.0-or-later AND MPL-2.0 AND Apache-2.0':
        errors.append('incorrect app version/license')
    if meta.get('included_systems') != ['CHIP-8', 'Game Boy', 'Game Boy Color', 'Game Boy Advance', 'NES', 'Famicom'] or meta.get('offline') is not True:
        errors.append('incorrect included platforms/offline policy')
    for required in ('PKG_VERSION:=0.1.0', 'PKG_RELEASE:=3', 'PKG_LICENSE:=GPL-3.0-or-later MPL-2.0 Apache-2.0',
                     'python3 $(CURDIR)/scripts/release_audit.py --release'):
        if required not in mk:
            errors.append(f'incorrect OpenWrt package config: {required}')
    if VERSION not in page or VERSION not in readme or VERSION not in notice:
        errors.append('version mismatch across documentation/UI')
    for document in ('docs/ARCHITECTURE.md', 'docs/RELEASE_CHECKLIST.md',
                     'docs/SOURCE_OFFER.md', 'docs/THIRD_PARTY.md'):
        try:
            if VERSION not in (ROOT / document).read_text(encoding='utf-8'):
                errors.append(f'version mismatch in documentation: {document}')
        except OSError as exc:
            errors.append(f'missing documentation: {exc}')
    try:
        history = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
        if re.findall(r'^## (0\.1\.0-r\d+)\b', history, re.M) != [VERSION, '0.1.0-r2', '0.1.0-r1']:
            errors.append('changelog must contain r3, consolidated r2, and original r1')
    except OSError as exc:
        errors.append(f'missing changelog: {exc}')
    if 'GNU GENERAL PUBLIC LICENSE' not in license_text.upper():
        errors.append('GPL license missing')
    if 'Mozilla Public License Version 2.0' not in mgba_license:
        errors.append('mGBA MPL-2.0 license missing')
    if 'mGBA' not in readme or 'mGBA' not in notice:
        errors.append('mGBA attribution missing')
    if not (ROOT / 'LICENSES/JSNES.txt').is_file() or 'Apache License' not in (ROOT / 'LICENSES/JSNES.txt').read_text(encoding='utf-8'):
        errors.append('JSNES Apache-2.0 license missing')
    if 'JSNES' not in readme or 'JSNES' not in notice:
        errors.append('JSNES attribution missing')
    web_files = {p.relative_to(WEB).as_posix() for p in WEB.rglob('*') if p.is_file()}
    # Stock OpenWrt uhttpd maps .js to text/javascript but does not recognize .mjs.
    # Module scripts served with its fallback MIME are rejected by browsers.
    if any(name.endswith('.mjs') for name in web_files):
        errors.append('OpenWrt uhttpd incompatible .mjs web module: use .js')
    if './app.js?v=' not in page:
        errors.append('OpenWrt entrypoint must use a JavaScript MIME-compatible .js URL')
    vendor_files = {name for name in web_files if name.startswith('vendor/jsnes/')}
    ordinary_web = web_files - vendor_files
    if ordinary_web not in (EXPECTED_WEB, EXPECTED_WEB | MGBA_VENDOR):
        errors.append(f'unexpected/incomplete web inventory: {sorted(ordinary_web ^ (EXPECTED_WEB | MGBA_VENDOR))}')
    if any(name.startswith('vendor/') and not name.startswith('vendor/jsnes/') for name in web_files):
        errors.append('unreviewed vendor files')
    # Keep the shipped emulation sources limited to the audited mGBA bridge.
    # New native engines/build tools/license bundles require an explicit review.
    for directory, expected in EXPECTED_SOURCE_COMPONENTS.items():
        actual = {file.relative_to(ROOT / directory).as_posix()
                  for file in (ROOT / directory).rglob('*')
                  if file.is_file() and '__pycache__' not in file.parts}
        if actual != expected:
            errors.append(f'unexpected source inventory in {directory}: {sorted(actual ^ expected)}')
    for script in ('web/app.js', 'web/fullscreen.js', 'web/controller.js', 'web/chip8.js', 'web/demo.js', 'web/systems.js',
                   'web/battery-store.js', 'web/mgba-player.js', 'web/jsnes-player.js', 'web/nes-audio.js'):
        try:
            source = (ROOT / script).read_text(encoding='utf-8')
        except OSError as exc:
            errors.append(f'missing browser script: {exc}')
            continue
        if re.search(r'\b(?:fetch\s*\(|WebSocket\s*\(|XMLHttpRequest\s*\()', source):
            errors.append(f'network API forbidden: {script}')
        if re.search(r"(?:from\s*|import\s*)['\"](?:https?:|//)", source):
            errors.append(f'external import forbidden: {script}')
    for path in ROOT.rglob('*'):
        if '.git' in path.parts or '__pycache__' in path.parts:
            continue
        if path.is_symlink():
            errors.append(f'symlink forbidden: {path.relative_to(ROOT)}')
        if path.is_file() and path.suffix.lower() in ('.apk', '.ipk', '.gb', '.gbc', '.gba', '.ch8', '.c8', '.nes'):
            errors.append(f'ROM/compiled package in source: {path.relative_to(ROOT)}')
        if path.is_file() and path.suffix.lower() in ('.wasm', '.data'):
            if WEB not in path.parents or path.relative_to(WEB).as_posix() not in MGBA_VENDOR:
                errors.append(f'unreviewed binary: {path.relative_to(ROOT)}')
    for required in ('docs/THIRD_PARTY.md', 'docs/ARCHITECTURE.md', 'docs/SOURCE_OFFER.md',
                     'docs/INSTALLATION_INFO.md', 'docs/RELEASE_CHECKLIST.md',
                     'native/mgba_bridge.c', 'scripts/build_mgba.py', 'scripts/vendor_jsnes.py', 'LICENSES/mGBA.txt', 'LICENSES/JSNES.txt'):
        if not (ROOT / required).is_file():
            errors.append(f'missing required source: {required}')
    if any((ROOT / name).exists() for name in
           ('SOURCE_OFFER.md', 'INSTALLATION_INFO.md', 'RELEASE_CHECKLIST.md')):
        errors.append('documentation must live in docs/')
    if ('./docs/SOURCE_OFFER.md' not in notice or
            './docs/INSTALLATION_INFO.md' not in notice or
            './docs/SOURCE_OFFER.md' not in mk or
            './docs/INSTALLATION_INFO.md' not in mk):
        errors.append('APK attribution/documentation paths not updated')
    if (ROOT / 'COMMIT_MESSAGE.txt').exists():
        errors.append('old vendor/commit file should not be present')

    # --check checks source layout in CI, including before a local WASM rebuild.
    # --release *always* checks binary+bridge hashes and blocks stale old GBA ABI.
    # JSNES is copied unmodified from the pinned npm package once on a development
    # machine. CI source checks may run before that step; APK releases may not.
    if vendor_files or release:
        manifest_file = WEB / 'vendor/jsnes/manifest.json'
        if not manifest_file.is_file():
            errors.append('JSNES 2.1.0 vendor modules and manifest required before release')
        else:
            try:
                manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
                modules = manifest.get('files', {})
                if (manifest.get('package') != 'jsnes' or manifest.get('version') != '2.1.0' or
                    manifest.get('license') != 'Apache-2.0' or
                    manifest.get('upstream') != 'https://github.com/bfirsh/jsnes' or
                    not re.fullmatch(r'sha512-[A-Za-z0-9+/]+=*', str(manifest.get('npm_integrity', '')))):
                    errors.append('unapproved JSNES provenance/version/license')
                if not isinstance(modules, dict) or len(modules) < 3 or not {'src/nes.js','src/controller.js'}.issubset(modules):
                    errors.append('incomplete JSNES ES module dependency inventory')
                else:
                    declared = {'vendor/jsnes/' + name for name in modules} | {'vendor/jsnes/manifest.json'}
                    if declared != vendor_files:
                        errors.append(f'unexpected JSNES vendor inventory: {sorted(declared ^ vendor_files)}')
                    for name, sha in modules.items():
                        if not re.fullmatch(r'src/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.js', name):
                            errors.append(f'unexpected JSNES module name: {name}')
                            continue
                        file = WEB / 'vendor/jsnes' / name
                        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != sha:
                            errors.append(f'invalid JSNES source hash: {name}')
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                errors.append(f'invalid JSNES manifest: {exc}')
    if release:
        if not MGBA_VENDOR.issubset(web_files):
            errors.append('mGBA 0.10.5 WASM/JS + provenance manifest are mandatory before APK release')
        else:
            try:
                manifest = json.loads((WEB / 'mgba/manifest.json').read_text(encoding='utf-8'))
                if (manifest.get('tag') != '0.10.5' or
                        not re.fullmatch(r'[0-9a-f]{40}', str(manifest.get('revision', '')))):
                    errors.append('unapproved mGBA source revision')
                if manifest.get('license') != 'MPL-2.0' or manifest.get('upstream') != 'https://github.com/mgba-emu/mgba':
                    errors.append('unapproved mGBA upstream or license')
                for name in ('mgba.js', 'mgba.wasm'):
                    if hashlib.sha256((WEB / 'mgba' / name).read_bytes()).hexdigest() != manifest.get('artifacts', {}).get(name):
                        errors.append(f'invalid mGBA binary hash: {name}')
                if (WEB / 'mgba/mgba.wasm').read_bytes()[:8] != b'\x00asm\x01\x00\x00\x00':
                    errors.append('invalid mGBA WebAssembly header')
                if hashlib.sha256((ROOT / 'native/mgba_bridge.c').read_bytes()).hexdigest() != manifest.get('bridge_sha256'):
                    errors.append('mGBA bridge changed since binary build; rebuild mGBA WASM for GB/GBC/GBA')
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                errors.append(f'invalid mGBA manifest: {exc}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='check source layout before local WASM rebuild')
    mode.add_argument('--release', action='store_true', help='require up-to-date pinned mGBA JS/WASM + manifest')
    args = parser.parse_args()
    errors = audit(release=args.release)
    if errors:
        print('FAIL: Retro Arcade inventory')
        for err in errors:
            print(' - ' + err)
        return 1
    print('PASS: ' + ('APK assets and license provenance verified' if args.release else 'source inventory verified (WASM build separate)'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
