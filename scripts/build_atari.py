#!/usr/bin/env python3
"""Offline vendor build from an explicitly pinned, locally audited Atari checkout.

No downloading, no npm install, no fetch:games; fail closed on anything outside
core TypeScript sources. See docs/ATARI_BUILD.md for release approval steps.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web/atari2600'
UPSTREAM = 'https://github.com/mohrt/atari2600'
PIN = re.compile(r'[a-f0-9]{40}\Z')
ROM_EXT = {'.a26', '.bin', '.rom', '.zip', '.nes', '.gba', '.gb', '.gbc', '.ch8', '.sfc', '.smc', '.chd', '.iso', '.7z'}
DENIED_NAMES = {'games', 'game-catalog', 'analytics', 'fetch-games', 'fetch-dormann'}
# The CPU may have a `fetch()` method (instruction fetch): neither a method
# definition nor `cpu.fetch()` performs a browser network request. The old
# broad `\bfetch\s*\(` pattern rejected these legitimate engine constructs.
# Match dangerous global APIs, not arbitrary property/method names.
DENIED_RUNTIME = re.compile(
    r'(?:google-analytics|googletagmanager|games/index\.json|games-catalog|fetch-games|free games)',
    re.I,
)
NETWORK_API = r'(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts)'
GLOBAL_NETWORK = re.compile(
    r'\b(?:globalThis|window|self|global)\s*(?:\.\s*' + NETWORK_API +
    r'\b|\[\s*[\"\']' + NETWORK_API + r'[\"\']\s*\])',
    re.I,
)
NETWORK_PRIMITIVES = re.compile(r'\b(?:XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts)\b', re.I)
BARE_FETCH = re.compile(r'(?<![\w$.])fetch\s*(?:\?\.)?\s*\(', re.I)
FETCH_METHOD = re.compile(r'fetch\s*\([^()]*\)\s*\{', re.I)


def denied_runtime_reason(code: str) -> str | None:
    """Offline-only contract, shared by build and APK release audit.

    `this.fetch()` or `fetch(){...}` inside an emulated 6507 CPU is safe;
    unqualified/global fetch, network primitives, and catalog/telemetry
    markers are forbidden. This supplements the pinned source import graph
    and hash audit; it does not replace manual review of upstream source.
    """
    marker = DENIED_RUNTIME.search(code)
    if marker:
        return f'forbidden game catalog/telemetry marker: {marker.group(0)}'
    primitive = NETWORK_PRIMITIVES.search(code)
    if primitive:
        return f'forbidden network primitive: {primitive.group(0)}'
    global_api = GLOBAL_NETWORK.search(code)
    if global_api:
        return f'forbidden global network access: {global_api.group(0)}'
    for match in BARE_FETCH.finditer(code):
        # e.g. class Cpu { fetch(){...} } or {fetch(){...}}; unlike
        # fetch(url), a method declaration is not a network call.
        if FETCH_METHOD.match(code, match.start()):
            continue
        return 'forbidden global fetch invocation'
    return None



def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def source_audit(source: Path, revision: str) -> dict[str, str]:
    if not PIN.fullmatch(revision):
        raise ValueError('Specify the exact 40-digit, lower-case Git commit (--revision)')
    if not (source / '.git').exists():
        raise ValueError('Expected a local git checkout, not an unverified source archive')
    head = run(['git', 'rev-parse', 'HEAD'], source)
    if head != revision:
        raise ValueError('Git HEAD does not match the approved revision')
    if run(['git', 'status', '--porcelain', '--untracked-files=normal'], source):
        raise ValueError('Source checkout has uncommitted changes')
    license_bytes = (source / 'LICENSE').read_bytes()
    expected = (ROOT / 'LICENSES/Atari2600.txt').read_bytes()
    if license_bytes != expected:
        raise ValueError('Upstream MIT LICENSE differs from the reviewed notice')
    pack = json.loads((source / 'package.json').read_text())
    if pack.get('dependencies'):
        raise ValueError('Upstream now declares runtime dependencies: full license audit required')
    src = source / 'src'
    if not src.is_dir() or src.is_symlink():
        raise ValueError('Missing or invalid upstream src directory')
    inventory: dict[str, str] = {}
    for path in sorted(src.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlink not allowed in upstream source: {path}')
        if not path.is_file():
            continue
        relative = path.relative_to(src).as_posix()
        if path.suffix.lower() in ROM_EXT:
            raise ValueError(f'ROM content in source tree: {relative}')
        if path.suffix not in {'.ts', '.tsx', '.json', '.css', '.svg'}:
            raise ValueError(f'Unexpected source asset, requires audit: {relative}')
        if re.search(r'(?i)GPL-2\.0-only|non.?commercial|all rights reserved', path.read_text(errors='replace')):
            raise ValueError(f'New incompatible license marker: {relative}')
        inventory[relative] = sha(path.read_bytes())
    if len(inventory) < 10 or not {'emulator.ts', 'atari2600.ts', 'cart/detect.ts', 'io/controllers/ports.ts', 'render/screen.ts'}.issubset(inventory):
        raise ValueError('Atari core source inventory missing required files')
    return inventory


def build(source: Path, revision: str, esbuild: Path, *, audit_only: bool = False) -> dict:
    source = source.resolve()
    inventory = source_audit(source, revision)
    if audit_only:
        return {'revision': revision, 'files': len(inventory)}
    esbuild = esbuild.expanduser().resolve()
    if not esbuild.is_file():
        raise ValueError('Please install esbuild locally and supply --esbuild /path/to/esbuild (no auto-install)')
    with tempfile.TemporaryDirectory(prefix='ssharcade-atari-') as tmp:
        work = Path(tmp)
        shutil.copytree(source / 'src', work / 'src', symlinks=False)
        entry = work / 'src/retro_arcade_entry.ts'
        entry.write_bytes((ROOT / 'native/atari_bridge.ts').read_bytes())
        output = work / 'engine.js'
        metafile = work / 'meta.json'
        # Only explicit native TS entry + its reachable dependencies are compiled;
        # never run upstream npm scripts, CLI fetchers or its index.html.
        run([str(esbuild), str(entry), '--bundle', '--platform=browser', '--format=esm',
             '--target=es2020', '--minify', '--legal-comments=none',
             '--outfile=' + str(output), '--metafile=' + str(metafile)], work)
        data = output.read_bytes()
        meta = json.loads(metafile.read_text())
        inputs = set(meta['inputs'])
        unwanted = [name for name in inputs if name.startswith(('node_modules/', '../')) or
                    name in {'src/main.ts','src/games.ts','src/analytics.ts','src/cart/load.ts','src/cart/zip.ts'} or
                    name.startswith(('src/ui/','src/storage/','src/io/keyboard-input','src/io/touch-controls')) or
                    any(part.lower().replace('_', '-') in DENIED_NAMES for part in Path(name).parts) or
                    (name.startswith('src/') and not name.endswith(('.ts', '.tsx')))]
        if unwanted:
            raise ValueError(f'Unsafe imported code in Atari build: {unwanted}')
        reason = denied_runtime_reason(data.decode('utf-8'))
        if reason:
            raise ValueError(f'Generated engine contains unsafe code: {reason}')
        # The complete original source tree is inventoried for audit; only the
        # esbuild-reachable graph is shipped. All discovered inputs are hashed.
        input_hashes = {name.removeprefix('src/'): inventory[name.removeprefix('src/')]
                        for name in inputs if name.startswith('src/') and name != 'src/retro_arcade_entry.ts'}
        manifest = {
            'engine':'atari2600', 'upstream':UPSTREAM, 'revision':revision,
            'license':'MIT', 'license_sha256':sha((ROOT/'LICENSES/Atari2600.txt').read_bytes()),
            'source_inventory_sha256':sha(json.dumps(inventory,sort_keys=True).encode()),
            'source_files':len(inventory), 'compiled_sources':input_hashes,
            'bridge_sha256':sha((ROOT/'native/atari_bridge.ts').read_bytes()),
            'build_script_sha256':sha(Path(__file__).read_bytes()),
            'no_game_roms':True, 'no_downloads':True, 'no_telemetry':True,
            'artifacts':{'engine.js':sha(data)},
        }
        WEB.mkdir(parents=True,exist_ok=True)
        (WEB/'engine.js').write_bytes(data)
        (WEB/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True,help='clean upstream Git checkout')
    parser.add_argument('--revision',required=True,help='exact independently approved full commit SHA')
    parser.add_argument('--esbuild',type=Path,help='preinstalled local esbuild binary')
    parser.add_argument('--audit-only',action='store_true')
    args = parser.parse_args()
    if not args.audit_only and not args.esbuild:
        parser.error('--esbuild is required unless --audit-only')
    try:
        result = build(args.source,args.revision,args.esbuild or Path('unused'),audit_only=args.audit_only)
    except (OSError,ValueError,subprocess.CalledProcessError,KeyError) as exc:
        print(f'FAIL: Atari source/build audit: {exc}')
        return 1
    print('PASS: Atari 2600 pinned offline build',result['revision'])
    return 0

if __name__=='__main__':
    raise SystemExit(main())
