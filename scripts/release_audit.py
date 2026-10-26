#!/usr/bin/env python3
"""Fail-closed offline inventory for the single-source CHIP-8 release.

This checks included files and declared licensing, not a legal opinion and not
proof that the package has been installed on the target router models.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'
EXPECTED_WEB = {
    'index.html', 'styles.css', 'app.mjs', 'chip8.mjs', 'systems.mjs',
    'demo.mjs', 'open-source.html',
}
VERSION = '0.1.0-r1'


def audit() -> list[str]:
    issues = []
    try:
        meta = json.loads((ROOT / 'app-info.json').read_text(encoding='utf-8'))
        makefile = (ROOT / 'Makefile').read_text(encoding='utf-8')
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        page = (WEB / 'index.html').read_text(encoding='utf-8')
        notice = (WEB / 'open-source.html').read_text(encoding='utf-8')
        license_text = (ROOT / 'LICENSE').read_text(encoding='utf-8')
    except (OSError, ValueError) as exc:
        return [f'missing or invalid release file: {exc}']
    if meta.get('version') != VERSION or meta.get('license') != 'GPL-3.0-or-later':
        issues.append('metadata version/license mismatch')
    if meta.get('included_systems') != ['CHIP-8'] or meta.get('offline') is not True:
        issues.append('unexpected enabled platforms or online mode')
    for literal in ('PKG_VERSION:=0.1.0', 'PKG_RELEASE:=1', 'PKG_LICENSE:=GPL-3.0-or-later',
                    'python3 $(CURDIR)/scripts/release_audit.py --release'):
        if literal not in makefile:
            issues.append(f'unsupported package setting: {literal}')
    if VERSION not in page or VERSION not in readme:
        issues.append('version not consistent in README or web page')
    if 'GNU GENERAL PUBLIC LICENSE' not in license_text.upper():
        issues.append('GPL license text is missing')
    if 'EmulatorJS' not in readme or '번들하지 않습니다' not in readme:
        issues.append('EmulatorJS status must be explained accurately')
    if 'CHIP-8' not in notice:
        issues.append('app license screen is incomplete')
    web_files = {p.relative_to(WEB).as_posix() for p in WEB.rglob('*') if p.is_file()}
    if web_files != EXPECTED_WEB:
        issues.append('unexpected/missing web assets: ' + repr(sorted(web_files ^ EXPECTED_WEB)))
    for script in ('web/app.mjs', 'web/chip8.mjs', 'web/demo.mjs', 'web/systems.mjs'):
        body = (ROOT / script).read_text(encoding='utf-8')
        if re.search(r'\b(?:import\s*\(|fetch\s*\(|WebSocket\s*\(|XMLHttpRequest\s*\()', body):
            issues.append(f'network/dynamic module API in {script}')
        if re.search(r"(?:from\s*|import\s*)['\"](?:https?:|//)", body):
            issues.append(f'external import in {script}')
    for path in ROOT.rglob('*'):
        if path.is_symlink():
            issues.append(f'symlink not allowed: {path.relative_to(ROOT)}')
        if path.is_file() and path.suffix.lower() in ('.wasm', '.data', '.min', '.apk', '.ipk', '.ch8', '.c8', '.nes', '.gba'):
            issues.append(f'unreviewed asset: {path.relative_to(ROOT)}')
    for required in ('THIRD_PARTY.md', 'SOURCE_OFFER.md', 'INSTALLATION_INFO.md', 'RELEASE_CHECKLIST.md'):
        if not (ROOT / required).is_file():
            issues.append(f'missing publication notice: {required}')
    if (ROOT / 'COMMIT_MESSAGE.txt').exists():
        issues.append('unwanted COMMIT_MESSAGE.txt')
    if (ROOT / 'web/vendor').exists():
        issues.append('unreviewed EmulatorJS binaries present')
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true', help='check source/metadata inventory')
    group.add_argument('--release', action='store_true', help='verify distributable source inventory')
    args = parser.parse_args()
    issues = audit()
    if issues:
        print('FAIL: Retro Arcade single-release inventory:')
        for issue in issues:
            print(' - ' + issue)
        return 1
    print('PASS: single-release original CHIP-8 source inventory verified offline')
    if args.release:
        print('NOTE: hardware APK installation, ROM compatibility, GPLv3 device obligations remain separately testable.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
