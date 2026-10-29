#!/usr/bin/env python3
"""Build the pinned MAME arcade subset; never download ROMs or upstream sources.

The upstream MAME Emscripten output is not produced by this repository's
frontend build process. Keep it an explicit developer-side prerequisite.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = 'mame0289'
VERSION = '0.289'
SOURCES = 'src/mame/pacman/pacman.cpp,src/mame/galaxian/galaxian.cpp'
SUBTARGET = 'ssharcade'
OPTIMIZATION = 'z'  # MAME passes this as -Oz to Emscripten.
BUILD_DIRECTORY = 'build-ssharcade-oz'
RECEIPT_NAME = '.ssharcade-oz-build.json'
UPSTREAM = 'https://github.com/mamedev/mame'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"{' '.join(args)} failed ({result.returncode}):\n" +
                         (result.stdout + '\n' + result.stderr)[-6000:])
    return result.stdout.strip()


def verify_source(source: Path) -> str:
    if not all((source / name).is_file() for name in ('makefile', 'src/mame/pacman/pacman.cpp',
                                                       'src/mame/galaxian/galaxian.cpp')):
        raise ValueError('MAME 0.289 source with both selected drivers is required')
    revision = run('git', '-C', str(source), 'rev-parse', 'HEAD')
    tag_revision = run('git', '-C', str(source), 'rev-list', '-n', '1', TAG)
    if not re.fullmatch(r'[0-9a-f]{40}', revision) or revision != tag_revision:
        raise ValueError('MAME checkout must be pinned at exact mame0289 tag')
    if run('git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('MAME checkout has local modifications: source audit required')
    return revision


def verify_artifacts(js: Path, wasm: Path) -> None:
    if not js.is_file() or not wasm.is_file():
        raise ValueError('official MAME Emscripten JS and WASM are both required')
    if not wasm.read_bytes().startswith(b'\x00asm\x01\x00\x00\x00'):
        raise ValueError('invalid MAME WASM header')
    source = js.read_text(encoding='utf-8')
    if len(source) < 2048 or 'Module' not in source or 'FS' not in source:
        raise ValueError('unexpected MAME JS; ensure a browser build exporting FS')
    if 'import(' in source or 'https://' in source[:3000]:
        raise ValueError('unreviewed MAME loader dependency')


def find_mame_artifacts(source: Path) -> tuple[Path, Path]:
    """Find the exact upstream SOURCES= build, never a different MAME target.

    In MAME 0.289 scripts/src/main.lua, specifying SOURCES makes the binary
    project name SUBTARGET (ssharcade), not mame+SUBTARGET.  The asmjs target
    has an .html launcher and Emscripten emits a sibling .js/.wasm pair.
    """
    js = source / f'{SUBTARGET}.js'
    wasm = source / f'{SUBTARGET}.wasm'
    if js.is_file() and wasm.is_file():
        return js, wasm
    missing = [str(path) for path in (js, wasm) if not path.is_file()]
    # These are only diagnostic hints.  Never package an arbitrary mame*.js or
    # a leftover artifact for another subtarget just because it is present.
    found = sorted(item.name for item in source.iterdir()
                   if item.is_file() and item.suffix in ('.js', '.wasm'))
    raise ValueError(
        'MAME build output missing: ' + ', '.join(missing) + '\n'
        + 'Expected matching Emscripten artifacts: '
        + f'{SUBTARGET}.js and {SUBTARGET}.wasm in {source}\n'
        + 'Found JS/WASM at source root: ' + (', '.join(found[:16]) or '(none)')
        + '\nIf the output was written elsewhere, pass --js PATH --wasm PATH '
          '(both must be from the same build).'
    )



def receipt_payload(revision: str, js: Path, wasm: Path) -> dict:
    """Bind locally generated outputs to this exact -Oz build script and source."""
    return {
        'tag': TAG, 'revision': revision, 'sources': SOURCES.split(','),
        'subtarget': SUBTARGET, 'optimization': OPTIMIZATION,
        'build_dir': BUILD_DIRECTORY,
        'build_script_sha256': digest(Path(__file__).resolve()),
        'artifacts': {'js': digest(js), 'wasm': digest(wasm)},
    }


def write_receipt(source: Path, revision: str, js: Path, wasm: Path) -> None:
    """Record a successful local -Oz build for subsequent --package-only runs."""
    (source / RECEIPT_NAME).write_text(
        json.dumps(receipt_payload(revision, js, wasm), indent=2) + '\n',
        encoding='utf-8',
    )


def verify_receipt(source: Path, revision: str, js: Path, wasm: Path) -> None:
    """Never relabel the old -Os output as -Oz through --package-only."""
    receipt = source / RECEIPT_NAME
    if not receipt.is_file():
        raise ValueError('MAME -Oz build receipt missing; rebuild without --package-only')
    try:
        saved = json.loads(receipt.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ValueError('invalid MAME -Oz build receipt; rebuild required') from exc
    if saved != receipt_payload(revision, js, wasm):
        raise ValueError('MAME -Oz build receipt does not match source or JS/WASM; '
                         'rebuild without --package-only')


def package(source: Path, revision: str, js: Path, wasm: Path) -> None:
    verify_artifacts(js, wasm)
    destination = ROOT / 'web/mame'
    destination.mkdir(exist_ok=True)
    for src, output in ((js, 'mame.js'), (wasm, 'mame.wasm')):
        shutil.copyfile(src, destination / output)
    manifest = {
        'engine': 'mame', 'version': VERSION, 'tag': TAG, 'revision': revision,
        'upstream': UPSTREAM, 'license': 'GPL-2.0-or-later',
        'sources': SOURCES.split(','), 'drivers': ['pacman', 'galaxian'],
        'optimization': OPTIMIZATION, 'build_dir': BUILD_DIRECTORY,
        'runtime_exports': ['FS'],
        'license_sha256': digest(ROOT / 'LICENSES/MAME-GPL2.txt'),
        'build_script_sha256': digest(ROOT / 'scripts/build_mame.py'),
        'emscripten': run('emcc', '--version').splitlines()[0],
        'artifacts': {'mame.js': digest(destination / 'mame.js'),
                      'mame.wasm': digest(destination / 'mame.wasm')},
    }
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('PASS: packaged MAME 0.289 (source: ' + str(source) + '); run release_audit --release')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--js', type=Path, help='path to official Emscripten output JS')
    parser.add_argument('--wasm', type=Path, help='path to matching official WASM')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--package-only', action='store_true', help='use already built official MAME artifacts')
    args = parser.parse_args()
    try:
        source = args.source.resolve()
        revision = verify_source(source)
        if (args.js is None) != (args.wasm is None):
            raise ValueError('--js and --wasm must be supplied together')
        if not args.package_only:
            if not 1 <= args.jobs <= 8:
                raise ValueError('jobs must be 1..8')
            # A failed build must not leave behind reusable -Os/-Oz provenance.
            (source / RECEIPT_NAME).unlink(missing_ok=True)
            run('embuilder', 'build', 'sdl3', 'sdl3_ttf')
            run('emmake', 'make', '-j' + str(args.jobs), 'SUBTARGET=' + SUBTARGET,
                'SOURCES=' + SOURCES, 'REGENIE=1', 'NO_OPENGL=1', 'TOOLS=0',
                'OPTIMIZE=' + OPTIMIZATION, 'BUILDDIR=' + BUILD_DIRECTORY,
                'LDOPTS=-sEXPORTED_RUNTIME_METHODS=FS', cwd=source)
        if args.js:
            js, wasm = args.js.resolve(), args.wasm.resolve()
        else:
            js, wasm = find_mame_artifacts(source)
        verify_artifacts(js, wasm)
        if args.package_only:
            verify_receipt(source, revision, js, wasm)
        else:
            write_receipt(source, revision, js, wasm)
        package(source, revision, js, wasm)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == '__main__':
    sys.exit(main())
