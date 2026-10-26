#!/usr/bin/env python3
"""Verify offline Retro Arcade inventory and mGBA provenance before release."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'
VERSION = '0.1.0-r2'
EXPECTED_WEB = {
    'index.html', 'styles.css', 'app.mjs', 'fullscreen.mjs', 'controller.mjs', 'chip8.mjs', 'systems.mjs',
    'demo.mjs', 'open-source.html', 'battery-store.mjs', 'mgba-player.mjs',
}
MGBA_VENDOR = {'mgba/mgba.mjs', 'mgba/mgba.wasm', 'mgba/manifest.json'}
EXPECTED_SOURCE_COMPONENTS = {
    'native': {'mgba_bridge.c'},
    'scripts': {'build_mgba.py', 'release_audit.py'},
    'LICENSES': {'mGBA.txt'},
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
    if meta.get('version') != VERSION or meta.get('license') != 'GPL-3.0-or-later AND MPL-2.0':
        errors.append('incorrect app version/license')
    if meta.get('included_systems') != ['CHIP-8', 'Game Boy', 'Game Boy Color', 'Game Boy Advance'] or meta.get('offline') is not True:
        errors.append('incorrect included platforms/offline policy')
    for required in ('PKG_VERSION:=0.1.0', 'PKG_RELEASE:=2', 'PKG_LICENSE:=GPL-3.0-or-later MPL-2.0',
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
        if re.findall(r'^## (0\.1\.0-r\d+)\b', history, re.M) != [VERSION, '0.1.0-r1']:
            errors.append('changelog must contain consolidated r2 and original r1')
    except OSError as exc:
        errors.append(f'missing changelog: {exc}')
    if 'GNU GENERAL PUBLIC LICENSE' not in license_text.upper():
        errors.append('GPL license missing')
    if 'Mozilla Public License Version 2.0' not in mgba_license:
        errors.append('mGBA MPL-2.0 license missing')
    if 'mGBA' not in readme or 'mGBA' not in notice:
        errors.append('mGBA attribution missing')
    web_files = {p.relative_to(WEB).as_posix() for p in WEB.rglob('*') if p.is_file()}
    if web_files not in (EXPECTED_WEB, EXPECTED_WEB | MGBA_VENDOR):
        errors.append(f'unexpected/incomplete web inventory: {sorted(web_files ^ (EXPECTED_WEB | MGBA_VENDOR))}')
    # Keep the shipped emulation sources limited to the audited mGBA bridge.
    # New native engines/build tools/license bundles require an explicit review.
    for directory, expected in EXPECTED_SOURCE_COMPONENTS.items():
        actual = {file.relative_to(ROOT / directory).as_posix()
                  for file in (ROOT / directory).rglob('*')
                  if file.is_file() and '__pycache__' not in file.parts}
        if actual != expected:
            errors.append(f'unexpected source inventory in {directory}: {sorted(actual ^ expected)}')
    for script in ('web/app.mjs', 'web/fullscreen.mjs', 'web/controller.mjs', 'web/chip8.mjs', 'web/demo.mjs', 'web/systems.mjs',
                   'web/battery-store.mjs', 'web/mgba-player.mjs'):
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
                     'native/mgba_bridge.c', 'scripts/build_mgba.py', 'LICENSES/mGBA.txt'):
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
    if (ROOT / 'COMMIT_MESSAGE.txt').exists() or (ROOT / 'web/vendor').exists():
        errors.append('old vendor/commit file should not be present')

    # --check checks source layout in CI, including before a local WASM rebuild.
    # --release *always* checks binary+bridge hashes and blocks stale old GBA ABI.
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
                for name in ('mgba.mjs', 'mgba.wasm'):
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
