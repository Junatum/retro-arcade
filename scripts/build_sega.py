#!/usr/bin/env python3
"""Build pinned Gearsystem/BlastEm libretro cores for offline Retro Arcade.

On the developer PC with emsdk activated and the upstream sources checked out:
  python3 scripts/build_sega.py gearsystem --source /path/to/Gearsystem
  python3 scripts/build_sega.py blastem --source /path/to/blastem
No network access occurs during this command. Neither source nor ROMs are bundled.
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
BRIDGE = ROOT / 'native/sega_libretro_bridge.c'
BLASTEM_HEADLESS = ROOT / 'native/blastem_headless.h'
GEARSYSTEM_TAG = '3.9.21'
BLASTEM_TAG = 'v1.0.0'
# v1.0.0 itself had a broken libretro target; upstream fixed it next commit.
# Pin that exact post-tag repair rather than a mutable tip/nightly revision.
BLASTEM_REV = '625fa5a85505'
EXPORTS = [
    '_ssh_retro_init', '_ssh_retro_load', '_ssh_retro_run', '_ssh_retro_key',
    '_ssh_retro_width', '_ssh_retro_height', '_ssh_retro_pixels',
    '_ssh_retro_fps_milli', '_ssh_retro_audio_rate', '_ssh_retro_audio',
    '_ssh_retro_save_size', '_ssh_retro_save', '_ssh_retro_restore',
    '_ssh_retro_destroy', '_malloc', '_free',
]


def invoke(*command: str, cwd: Path | None = None) -> str:
    """Show the *actual* compiler output instead of only CalledProcessError."""
    try:
        return subprocess.check_output(command, cwd=cwd, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        output = (exc.output or '').strip()
        if len(output) > 30000:
            output = output[:4000] + '\n... compiler output truncated ...\n' + output[-24000:]
        if not output:
            output = '(the command returned no diagnostic output)'
        raise ValueError(
            f'{command[0]} failed (exit {exc.returncode}):\n'
            f'{" ".join(command)}\n{output}'
        ) from exc


def core_for_link(engine: str, core: Path, tmp: Path) -> Path:
    """Gearsystem's *.bc is actually an `emar` archive, not LLVM bitcode.

    Copy to an unambiguous *.a filename before invoking em++, so recent
    Emscripten drivers do not try to interpret an archive as raw bitcode.
    Nothing in the upstream checkout is renamed or rewritten.
    """
    with core.open('rb') as archive:
        signature = archive.read(8)
    if signature == b'!<arch>\n':
        target = tmp / f'{engine}_libretro.a'
        shutil.copyfile(core, target)
        return target
    if engine == 'gearsystem' and (signature.startswith(b'BC\xc0\xde') or signature.startswith(b'\x00asm')):
        # Keep compatibility if upstream starts writing true LLVM bitcode or a
        # direct WASM object instead of the current ar archive.
        return core
    raise ValueError(f'{engine}: unsupported libretro core binary format: {signature!r}')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_source(engine: str, source: Path) -> tuple[str, Path, Path]:
    if engine == 'gearsystem':
        if not (source / 'platforms/libretro/Makefile').is_file():
            raise ValueError('Gearsystem Libretro Makefile missing')
        revision = invoke('git', 'rev-parse', 'HEAD', cwd=source).strip()
        tag = invoke('git', 'describe', '--tags', '--exact-match', 'HEAD', cwd=source).strip()
        if not re.fullmatch(r'[0-9a-f]{40}', revision) or tag != GEARSYSTEM_TAG:
            raise ValueError(f'Gearsystem source must be clean tag {GEARSYSTEM_TAG}, got {tag}')
        status = invoke('git', 'status', '--porcelain', '--untracked-files=all', cwd=source)
        # Upstream's Makefile names the generated static archive *.bc and the
        # tag does not ignore it. A previous failed link can therefore leave
        # an untracked output; it is safe because the make clean below deletes
        # and recompiles it before linking.
        permitted = {'?? platforms/libretro/gearsystem_libretro_emscripten.bc'}
        if any(line not in permitted for line in status.splitlines()):
            raise ValueError('Gearsystem source checkout has local modifications')
        license_path = source / 'LICENSE'
        header_path = source / 'platforms/libretro'
    else:
        if not (source / 'Makefile').is_file() or not (source / 'libblastem.c').is_file():
            raise ValueError('BlastEm 1.0.0 Libretro source missing')
        revision = invoke('hg', 'id', '-i', cwd=source).strip().rstrip('+')
        if not revision.startswith(BLASTEM_REV) or '+' in invoke('hg', 'id', '-i', cwd=source):
            raise ValueError(f'BlastEm source must be the verified libretro fix following {BLASTEM_TAG} ({BLASTEM_REV})')
        license_path = source / 'COPYING'
        header_path = source
    if not license_path.is_file() or 'GNU GENERAL PUBLIC LICENSE' not in license_path.read_text(errors='replace').upper():
        raise ValueError(f'{engine}: upstream GPL license file missing')
    if not (header_path / 'libretro.h').is_file():
        raise ValueError(f'{engine}: Libretro API header missing')
    return revision, license_path, header_path


def blastem_makefile_overlay() -> str:
    """Build BlastEm without changing the upstream checkout.

    Upstream uses `sed rom.db -e ...` in its implicit %.db.c rule.
    BSD sed (macOS) treats that first filename as a program, so override
    only rom.db.c with a portable ordering of the *same* substitutions.
    Make expands $$ into a literal $ before passing the recipe to sed.
    """
    return (
        'include Makefile\n'
        'rom.db.c: rom.db\n'
        "\tsed -e 's/\"/\\\\\"/g' "
        "-e 's/^\\(.*\\)$$/\"\\1\\\\n\"/' "
        "-e '1s/^\\(.*\\)$$/const char rom_db_data[] = \\1/' "
        "-e '$$s/^\\(.*\\)$$/\\1;/' < $< > $@\n"
        'ssh-blastem.a: $(LIBOBJS:%.o=$(LIBOBJDIR)/%.o)\n'
        '\t$(AR) rcs $@ $^\n'
    )


def build_core(engine: str, source: Path, tmp: Path) -> Path:
    if engine == 'gearsystem':
        outdir = source / 'platforms/libretro'
        # Avoid reusing old *.o files from a different Emscripten version.
        # Also remove the untracked *.bc left by an earlier failed link.
        invoke('emmake', 'make', '-C', str(outdir), 'clean', 'platform=emscripten',
               'CC=emcc', 'CXX=em++', 'AR=emar')
        invoke('emmake', 'make', '-C', str(outdir), '-j2', 'platform=emscripten',
               'CC=emcc', 'CXX=em++', 'AR=emar')
        core = outdir / 'gearsystem_libretro_emscripten.bc'
    else:
        # BlastEm v1.0.0 plus upstream libretro fix normally links a native .so. Build its
        # existing libretro object list as an Emscripten archive instead. No
        # modifications are made to upstream source files.
        overlay = tmp / 'Makefile.libretro-ssh'
        overlay.write_text(blastem_makefile_overlay(), encoding='utf-8')
        invoke('emmake', 'make', '-C', str(source), '-f', str(overlay), '-j2',
               'ssh-blastem.a', 'CC=emcc', 'CXX=em++', 'AR=emar',
               'CPU=wasm', 'NOGL=1', 'Z80_DISPATCH=call')
        core = source / 'ssh-blastem.a'
    if not core.is_file() or core.stat().st_size < 4096:
        raise ValueError(f'{engine}: compiler did not emit a libretro archive')
    return core


def link_web_core(engine: str, header_path: Path, core: Path, temp: Path) -> Path:
    """Compile the Libretro bridge as C before the final C++ link.

    Emscripten 6.x's em++ compiles even .c inputs as C++; using emcc
    avoids C++ pointer-conversion errors and C++-mangled export names.
    """
    bridge_object = temp / 'sega_libretro_bridge.o'
    # Compile the two optional BlastEm UI stubs into *only* BlastEm's
    # bridge object. This preserves existing Gearsystem binary/manifest hashes.
    # IS_LIB excludes the SDL desktop types in BlastEm's render.h.
    browser_stubs = ('-DIS_LIB', '-include', str(BLASTEM_HEADLESS)) if engine == 'blastem' else ()
    invoke('emcc', '-O2', '-std=c11', '-I' + str(header_path), *browser_stubs,
           '-c', str(BRIDGE), '-o', str(bridge_object))
    js = temp / f'{engine}.js'
    invoke('em++', '-O2', str(bridge_object), str(core), '-o', str(js),
           '--no-entry', '-sMODULARIZE=1', '-sEXPORT_ES6=1',
           f'-sEXPORT_NAME=create{engine.title()}', '-sENVIRONMENT=web',
           '-sALLOW_MEMORY_GROWTH=1', '-sMAXIMUM_MEMORY=268435456',
           '-sFORCE_FILESYSTEM=1', '-sASSERTIONS=0',
           '-sEXPORTED_RUNTIME_METHODS=["FS","HEAPU8","HEAP16","HEAPU32"]',
           '-sEXPORTED_FUNCTIONS=' + json.dumps(EXPORTS, separators=(',', ':')),
           '-lm')
    return js


def build(engine: str, source: Path) -> None:
    for tool in ('emcc', 'em++', 'emmake', 'emar', 'make'):
        if not shutil.which(tool):
            raise ValueError(f'missing required tool: {tool} (activate Emscripten SDK)')
    if not shutil.which('git' if engine == 'gearsystem' else 'hg'):
        raise ValueError('missing upstream source version control tool')
    revision, license_path, header_path = check_source(engine, source)
    outdir = ROOT / 'web' / engine
    license_out = ROOT / 'LICENSES' / ('Gearsystem.txt' if engine == 'gearsystem' else 'BlastEm.txt')
    with tempfile.TemporaryDirectory(prefix=f'retro-{engine}-') as temporary:
        temp = Path(temporary)
        core = build_core(engine, source, temp)
        link_input = core_for_link(engine, core, temp)
        js = link_web_core(engine, header_path, link_input, temp)
        wasm = temp / f'{engine}.wasm'
        if not wasm.is_file() or wasm.read_bytes()[:8] != b'\x00asm\x01\x00\x00\x00':
            raise ValueError('invalid Emscripten WASM output')
        # Complete build first; publish only when the linked artifacts exist.
        outdir.mkdir(parents=True, exist_ok=True)
        for name in (f'{engine}.js', f'{engine}.wasm'):
            shutil.copy2(temp / name, outdir / name)
        shutil.copy2(license_path, license_out)
        manifest = {
            'engine': engine, 'tag': GEARSYSTEM_TAG if engine == 'gearsystem' else BLASTEM_TAG,
            'pin': 'tag' if engine == 'gearsystem' else 'upstream-post-tag-libretro-fix',
            'revision': revision,
            'upstream': ('https://github.com/drhelius/Gearsystem' if engine == 'gearsystem'
                         else 'https://www.retrodev.com/repos/blastem'),
            'license': 'GPL-3.0-or-later', 'license_sha256': sha(license_out),
            'bridge_sha256': sha(BRIDGE),
            'emcc': invoke('emcc', '--version').splitlines()[0],
            'artifacts': {name: sha(outdir / name) for name in (f'{engine}.js', f'{engine}.wasm')},
        }
        if engine == 'blastem':
            manifest['headless_stubs_sha256'] = sha(BLASTEM_HEADLESS)
        (outdir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'PASS: {engine} {manifest["tag"]} built; run scripts/cache_bust.py --update then release audit')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', choices=('gearsystem', 'blastem'))
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.engine, args.source.resolve())
    except (OSError, ValueError, subprocess.CalledProcessError) as err:
        parser.error(str(err))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
