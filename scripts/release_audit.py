#!/usr/bin/env python3
"""Verify offline Retro Arcade inventory and provenance before release."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
try:
    from scripts.cache_bust import check as check_browser_cache
    from scripts.mame_registry import check as check_mame_registry
except ModuleNotFoundError:  # python3 scripts/release_audit.py
    from cache_bust import check as check_browser_cache
    from mame_registry import check as check_mame_registry

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'
VERSION = '1.2.0-r4'
EXPECTED_WEB = {
    'index.html', 'styles.css', 'favicon.svg', 'favicon.ico', 'app.js', 'fullscreen.js', 'controller.js', 'chip8.js', 'systems.js',
    'mame-player.js', 'mame/runner.html', 'mame/runner.js', 'mame/runner.css', 'mame/machines.js', 'demo.js', 'open-source.html', 'battery-store.js', 'save-session.js', 'mgba-player.js', 'jsnes-player.js', 'nes-audio.js', 'sega-player.js', 'audio-controls.js',
}
MGBA_VENDOR = {'mgba/mgba.js', 'mgba/mgba.wasm', 'mgba/manifest.json'}
SEGA_ENGINES = ('gearsystem', 'blastem')
SEGA_VENDOR = {f'{name}/{file}' for name in SEGA_ENGINES
               for file in (f'{name}.js', f'{name}.wasm', 'manifest.json')}
MAME_TAG = 'mame0289'
MAME_VERSION = '0.289'
MAME_SOURCES = 'src/mame/pacman/pacman.cpp,src/mame/galaxian/galaxian.cpp'
MAME_VENDOR = {'mame/mame.js', 'mame/mame.wasm', 'mame/manifest.json'}
SEGA_LICENSE = {'gearsystem': 'Gearsystem.txt', 'blastem': 'BlastEm.txt'}
EXPECTED_SOURCE_COMPONENTS = {
    'native': {'mgba_bridge.c', 'sega_libretro_bridge.c', 'blastem_headless.h'},
    'scripts': {'build_mgba.py', 'build_sega.py', 'build_mame.py', 'cache_bust.py', 'release_audit.py', 'vendor_jsnes.py', 'mame_registry.py'},
    'LICENSES': {'mGBA.txt', 'JSNES.txt', 'Gearsystem.txt', 'BlastEm.txt', 'Libretro.txt', 'MAME-GPL2.txt'},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(release: bool = False, require_sega: bool = True, require_mame: bool = True) -> list[str]:
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
    if meta.get('version') != VERSION or meta.get('license') != 'GPL-3.0-or-later AND GPL-2.0-or-later AND MPL-2.0 AND Apache-2.0 AND MIT':
        errors.append('incorrect app version/license')
    if meta.get('included_systems') != ['CHIP-8', 'Game Boy', 'Game Boy Color', 'Game Boy Advance', 'NES', 'Famicom', 'Game Gear', 'Master System', 'SG-1000', 'Mega Drive', 'Genesis', 'Arcade (MAME 0.289 selected drivers)'] or meta.get('offline') is not True:
        errors.append('incorrect included platforms/offline policy')
    for required in ('PKG_VERSION:=1.2.0', 'PKG_RELEASE:=4', 'PKG_LICENSE:=GPL-3.0-or-later GPL-2.0-or-later MPL-2.0 Apache-2.0 MIT',
                     'python3 $(CURDIR)/scripts/release_audit.py --release'):
        if required not in mk:
            errors.append(f'incorrect OpenWrt package config: {required}')
    # Keep a single version badge in the application header, but do not
    # repeat the product version in general-purpose user documentation.
    if page.count(f'<span class="edition">v{VERSION}</span>') != 1:
        errors.append('header version badge must match the OpenWrt release version')
    # Both user-facing pages must load the locally bundled favicon files.
    for page_name, html in (('index.html', page), ('open-source.html', notice)):
        for name in ('favicon.svg', 'favicon.ico'):
            if f'href="./{name}"' not in html:
                errors.append(f'missing favicon link in {page_name}: {name}')
    try:
        icon_svg = (WEB / 'favicon.svg').read_text(encoding='utf-8')
        icon_ico = (WEB / 'favicon.ico').read_bytes()
        if ('<svg' not in icon_svg or 'xmlns="http://www.w3.org/2000/svg"' not in icon_svg or
                '<script' in icon_svg or re.search(r'(?:href|src)=["\'](?:https?:|//)', icon_svg)):
            errors.append('invalid or nonlocal favicon SVG')
        if (len(icon_ico) < 22 or icon_ico[:4] != b'\x00\x00\x01\x00' or
                icon_ico[4:6] == b'\x00\x00'):
            errors.append('invalid favicon ICO header')
    except OSError as exc:
        errors.append(f'missing favicon assets: {exc}')
    for document, content in (('README.md', readme),
                              ('web/open-source.html', notice)):
        if VERSION in content or re.search(r'\b\d+\.\d+\.\d+-r\d+\b', content):
            errors.append(f'unnecessary product version shown in {document}')
    for document in ('docs/ARCHITECTURE.md', 'docs/RELEASE_CHECKLIST.md', 'docs/THIRD_PARTY.md'):
        try:
            content = (ROOT / document).read_text(encoding='utf-8')
            if re.search(r'\b\d+\.\d+\.\d+-r\d+\b', content):
                errors.append(f'unnecessary product version shown in {document}')
        except OSError as exc:
            errors.append(f'missing documentation: {exc}')
    try:
        if VERSION not in (ROOT / 'docs/SOURCE_OFFER.md').read_text(encoding='utf-8'):
            errors.append('source offer must identify exact release version')
    except OSError as exc:
        errors.append(f'missing source offer: {exc}')
    try:
        history = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
        if re.findall(r'^## (\d+\.\d+\.\d+-r\d+)\b', history, re.M) != [VERSION, '1.2.0-r3', '1.2.0-r2', '1.2.0-r1', '1.1.0-r5', '1.1.0-r4', '1.1.0-r3', '1.1.0-r2', '1.1.0-r1', '1.0.0-r1', '0.1.0-r6', '0.1.0-r5', '0.1.0-r4', '0.1.0-r3', '0.1.0-r2', '0.1.0-r1']:
            errors.append('changelog must contain the current release and all previous versions')
    except OSError as exc:
        errors.append(f'missing changelog: {exc}')
    if 'GNU GENERAL PUBLIC LICENSE' not in license_text.upper():
        errors.append('GPL license missing')
    if 'Mozilla Public License Version 2.0' not in mgba_license:
        errors.append('mGBA MPL-2.0 license missing')
    try:
        if 'Permission is hereby granted' not in (ROOT / 'LICENSES/Libretro.txt').read_text():
            errors.append('Libretro API MIT license missing')
    except OSError as exc:
        errors.append(f'missing Libretro MIT notice: {exc}')
    if 'mGBA' not in readme or 'mGBA' not in notice:
        errors.append('mGBA attribution missing')
    if not (ROOT / 'LICENSES/JSNES.txt').is_file() or 'Apache License' not in (ROOT / 'LICENSES/JSNES.txt').read_text(encoding='utf-8'):
        errors.append('JSNES Apache-2.0 license missing')
    if 'JSNES' not in readme or 'JSNES' not in notice:
        errors.append('JSNES attribution missing')
    if 'GNU GENERAL PUBLIC LICENSE' not in (ROOT / 'LICENSES/MAME-GPL2.txt').read_text():
        errors.append('MAME GPLv2 license missing')
    if 'MAME' not in readme or 'MAME' not in notice:
        errors.append('MAME attribution missing')
    try:
        runner_html = (WEB / 'mame/runner.html').read_text(encoding='utf-8')
        if ("style-src 'self'" not in runner_html or
                '<link rel="stylesheet" href="./runner.css">' not in runner_html or
                re.search(r'<style(?:\s|>)|\sstyle\s*=', runner_html, re.I)):
            errors.append('mame: runner CSP requires external local stylesheet')
    except OSError as exc:
        errors.append(f'mame: runner HTML unavailable ({exc})')
    for engine in SEGA_ENGINES:
        lic = ROOT / 'LICENSES' / SEGA_LICENSE[engine]
        if not lic.is_file() or 'GNU GENERAL PUBLIC LICENSE' not in lic.read_text(errors='replace').upper():
            errors.append(f'{engine}: GPL license missing')
        if engine.lower() not in readme.lower() or engine.lower() not in notice.lower():
            errors.append(f'{engine} attribution missing')
    web_files = {p.relative_to(WEB).as_posix() for p in WEB.rglob('*') if p.is_file()}
    # Stock OpenWrt uhttpd maps .js to text/javascript but does not recognize .mjs.
    # Module scripts served with its fallback MIME are rejected by browsers.
    if any(name.endswith('.mjs') for name in web_files):
        errors.append('OpenWrt uhttpd incompatible .mjs web module: use .js')
    if './app.js?v=' not in page:
        errors.append('OpenWrt entrypoint must use a JavaScript MIME-compatible .js URL')
    try:
        stale = check_browser_cache(web=WEB)
        if stale:
            errors.append(f'stale browser asset hashes: {stale}; run scripts/cache_bust.py --update')
    except (OSError, ValueError) as exc:
        errors.append(f'cannot verify browser asset hashes: {exc}')
    vendor_files = {name for name in web_files if name.startswith('vendor/jsnes/')}
    ordinary_web = web_files - vendor_files - MAME_VENDOR
    if (ordinary_web - SEGA_VENDOR) not in (EXPECTED_WEB, EXPECTED_WEB | MGBA_VENDOR):
        errors.append(f'unexpected/incomplete web inventory: {sorted((ordinary_web - SEGA_VENDOR) ^ (EXPECTED_WEB | MGBA_VENDOR))}')
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
                   'web/battery-store.js', 'web/save-session.js', 'web/mgba-player.js', 'web/jsnes-player.js', 'web/nes-audio.js', 'web/sega-player.js', 'web/audio-controls.js', 'web/mame-player.js', 'web/mame/runner.js', 'web/mame/machines.js'):
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
        if path.is_file() and path.suffix.lower() in ('.apk', '.ipk', '.gb', '.gbc', '.gba', '.ch8', '.c8', '.nes', '.gg', '.sms', '.sg', '.gen', '.rom'):
            errors.append(f'ROM/compiled package in source: {path.relative_to(ROOT)}')
        if path.is_file() and path.suffix.lower() in ('.wasm', '.data'):
            if WEB not in path.parents or path.relative_to(WEB).as_posix() not in MGBA_VENDOR | SEGA_VENDOR | MAME_VENDOR:
                errors.append(f'unreviewed binary: {path.relative_to(ROOT)}')
    for required in ('docs/THIRD_PARTY.md', 'docs/ARCHITECTURE.md', 'docs/SOURCE_OFFER.md',
                     'docs/INSTALLATION_INFO.md', 'docs/RELEASE_CHECKLIST.md',
                     'native/mgba_bridge.c', 'native/sega_libretro_bridge.c', 'scripts/build_mgba.py', 'scripts/build_sega.py', 'scripts/vendor_jsnes.py', 'scripts/build_mame.py', 'scripts/mame_registry.py', 'LICENSES/MAME-GPL2.txt', 'LICENSES/mGBA.txt', 'LICENSES/JSNES.txt', 'LICENSES/Gearsystem.txt', 'LICENSES/BlastEm.txt', 'LICENSES/Libretro.txt'):
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
    # New engines are built by the developer, never downloaded at runtime.
    # A source-only check is allowed before build, but a package release cannot
    # omit either core or substitute precompiled, unreviewed third-party assets.
    for engine in SEGA_ENGINES:
        names = {f'{engine}/{engine}.js', f'{engine}/{engine}.wasm', f'{engine}/manifest.json'}
        present = names & web_files
        if not present and (not release or not require_sega):
            continue
        if present != names:
            errors.append(f'{engine}: JS/WASM/manifest must be bundled together before release')
            continue
        try:
            manifest = json.loads((WEB / engine / 'manifest.json').read_text(encoding='utf-8'))
            tag, upstream = (('3.9.21', 'https://github.com/drhelius/Gearsystem')
                             if engine == 'gearsystem' else ('v1.0.0', 'https://www.retrodev.com/repos/blastem'))
            revision = manifest.get('revision')
            good_rev = (re.fullmatch(r'[0-9a-f]{40}', str(revision)) if engine == 'gearsystem'
                        else str(revision).startswith('625fa5a85505'))
            if (manifest.get('engine') != engine or manifest.get('tag') != tag or
                manifest.get('upstream') != upstream or manifest.get('license') != 'GPL-3.0-or-later' or not good_rev or
                manifest.get('pin') != ('tag' if engine == 'gearsystem' else 'upstream-post-tag-libretro-fix')):
                errors.append(f'{engine}: unapproved upstream revision/license')
            if sha256(ROOT / 'LICENSES' / SEGA_LICENSE[engine]) != manifest.get('license_sha256'):
                errors.append(f'{engine}: GPL notice hash mismatch')
            if sha256(ROOT / 'native/sega_libretro_bridge.c') != manifest.get('bridge_sha256'):
                errors.append(f'{engine}: bridge changed since build; rebuild WASM')
            if engine == 'blastem' and sha256(ROOT / 'native/blastem_headless.h') != manifest.get('headless_stubs_sha256'):
                errors.append('blastem: headless stubs changed since build; rebuild WASM')
            # Allow source/legacy checks before rebuilding; reject old -O2
            # artifacts in the actual APK release gate until -Oz is proven.
            if engine == 'blastem' and require_sega and release:
                if (manifest.get('optimization') != ['-Oz', '-flto'] or
                        manifest.get('build_script_sha256') != sha256(ROOT / 'scripts/build_sega.py')):
                    errors.append('blastem: -Oz/-flto build required; rebuild JS/WASM and manifest')
            for name in (f'{engine}.js', f'{engine}.wasm'):
                target = WEB / engine / name
                if sha256(target) != manifest.get('artifacts', {}).get(name):
                    errors.append(f'{engine}: invalid artifact hash {name}')
            if (WEB / engine / f'{engine}.wasm').read_bytes()[:8] != b'\x00asm\x01\x00\x00\x00':
                errors.append(f'{engine}: invalid WebAssembly header')
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            errors.append(f'{engine}: invalid release manifest ({exc})')
    # Every published 1.2.0 APK must contain a locally built, provenance-pinned
    # MAME JS/WASM pair. Never accept a stub or a partial bundle.
    mame_present = MAME_VENDOR & web_files
    if mame_present != MAME_VENDOR:
        if release and require_mame:
            errors.append('mame: JS/WASM/manifest required before 1.2.0 APK release')
        elif mame_present:
            errors.append('mame: incomplete JS/WASM/manifest bundle')
    else:
        try:
            manifest = json.loads((WEB / 'mame/manifest.json').read_text(encoding='utf-8'))
            good = (manifest.get('engine') == 'mame' and
                    manifest.get('version') == MAME_VERSION and manifest.get('tag') == MAME_TAG and
                    manifest.get('upstream') == 'https://github.com/mamedev/mame' and
                    re.fullmatch(r'[0-9a-f]{40}', str(manifest.get('revision', ''))) and
                    manifest.get('license') == 'GPL-2.0-or-later' and
                    manifest.get('drivers') == ['pacman', 'galaxian'] and
                    manifest.get('optimization') == 'z' and
                    manifest.get('build_dir') == 'build-ssharcade-oz' and
                    manifest.get('runtime_exports') == ['FS'] and
                    manifest.get('sources') == MAME_SOURCES.split(','))
            if not good:
                errors.append('mame: unapproved release, driver set, or license')
            if manifest.get('license_sha256') != sha256(ROOT / 'LICENSES/MAME-GPL2.txt'):
                errors.append('mame: license checksum mismatch')
            if manifest.get('build_script_sha256') != sha256(ROOT / 'scripts/build_mame.py'):
                errors.append('mame: build script changed; rebuild required')
            for name in ('mame.js', 'mame.wasm'):
                if manifest.get('artifacts', {}).get(name) != sha256(WEB / 'mame' / name):
                    errors.append(f'mame: invalid artifact hash {name}')
            if not (WEB / 'mame/mame.wasm').read_bytes().startswith(b'\x00asm\x01\x00\x00\x00'):
                errors.append('mame: invalid WebAssembly header')
            if not check_mame_registry(WEB / 'mame/mame.wasm', WEB / 'mame/machines.js'):
                errors.append('mame: supported machine list does not match bundled WASM')
            runtime = (WEB / 'mame/mame.js').read_text(encoding='utf-8')
            has_helpers = ('Module["FS_createPath"]' in runtime and
                           'Module["FS_createDataFile"]' in runtime)
            has_fs = 'Module["FS"]' in runtime or 'Module.FS=' in runtime
            if not (has_helpers or has_fs):
                errors.append('mame: no compatible exported ROM filesystem API')
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            errors.append(f'mame: invalid release manifest ({exc})')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='check source layout before local WASM rebuild')
    mode.add_argument('--release', action='store_true', help='require all pinned engines including MAME' )
    mode.add_argument('--existing', action='store_true', help='check previously built engines without requiring MAME')
    args = parser.parse_args()
    errors = audit(release=args.release or args.existing, require_sega=not args.existing, require_mame=not args.existing)
    if errors:
        print('FAIL: Retro Arcade inventory')
        for err in errors:
            print(' - ' + err)
        return 1
    print('PASS: ' + ('APK assets and license provenance verified' if args.release else 'existing released engines verified (MAME release not implied)' if args.existing else 'source inventory verified (WASM build separate)'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
