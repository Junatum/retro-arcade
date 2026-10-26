#!/usr/bin/env python3
"""One-time local mGBA 0.10.5 -> WebAssembly build (never used by APK build).

Requires checked-out official mGBA source, Emscripten (emcc/emcmake), CMake.
Does not run `git clone`, fetch binary blobs, or contact a network at build time.
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

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'web/mgba'
UPSTREAM='https://github.com/mgba-emu/mgba'
VERSION='0.10.5'
EXPORTS=['_ssh_mgba_load','_ssh_mgba_frame','_ssh_mgba_framebuffer',
         '_ssh_mgba_width','_ssh_mgba_height','_ssh_mgba_key','_ssh_mgba_save_size','_ssh_mgba_save',
         '_ssh_mgba_restore','_ssh_mgba_destroy','_malloc','_free']


def call(*cmd, cwd=None):
    subprocess.run(cmd,cwd=cwd,check=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True,help='offline checkout of mgba-emu/mgba tag 0.10.5')
    args=parser.parse_args()
    source=args.source.resolve()
    for tool in ('git','emcc','emcmake','cmake'):
        if not shutil.which(tool):parser.error(f'{tool} not found')
    if not (source/'CMakeLists.txt').is_file() or not (source/'LICENSE').is_file():
        parser.error('invalid upstream mGBA source tree')
    revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    tag=subprocess.check_output(['git','-C',str(source),'describe','--tags','--exact-match','HEAD'],text=True).strip()
    if tag!=VERSION or not re.fullmatch(r'[0-9a-f]{40}',revision):
        parser.error(f'expected mGBA tag {VERSION}, got {tag} ({revision})')
    if 'Mozilla Public License' not in (source/'LICENSE').read_text(errors='replace'):
        parser.error('upstream MPL-2.0 LICENSE missing')
    with tempfile.TemporaryDirectory(prefix='retro-mgba-') as tmp:
        build=Path(tmp)/'build'
        # mGBA CMake generates config headers and links platform-independent core.
        call('emcmake','cmake','-S',str(source),'-B',str(build),
             # mGBA 0.10.5 requires CMake 3.1 policy compatibility.
             # CMake 4 removed policies older than 3.5; do not modify upstream files.
             '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
             # mGBA only defines _GNU_SOURCE on Linux, not Emscripten.
             # Its strict C11 mode otherwise hides PATH_MAX/strdup/strlcpy.
             '-DCMAKE_C_FLAGS=-D_GNU_SOURCE',
             '-DCMAKE_BUILD_TYPE=Release',
             '-DBUILD_STATIC=ON','-DBUILD_SHARED=OFF',
             '-DDISABLE_FRONTENDS=ON','-DDISABLE_DEPS=ON',
             # Use mGBA's actual CMake options, not the unused USE_GL flags.
             '-DBUILD_GL=OFF','-DBUILD_GLES2=OFF','-DBUILD_GLES3=OFF',
             # mCore's struct layout depends on USE_DEBUGGERS; the thin
             # browser bridge must use the same layout as libmgba.
             '-DUSE_DEBUGGERS=OFF','-DENABLE_SCRIPTING=OFF',
             '-DUSE_SQLITE3=OFF',
             '-DCMAKE_POSITION_INDEPENDENT_CODE=ON')
        call('cmake','--build',str(build),'--target','mgba','--parallel','2')
        libs=list(build.rglob('libmgba.a'))
        if len(libs)!=1:
            parser.error(f'expected one libmgba.a, found {len(libs)}')
        js=Path(tmp)/'mgba.js'
        call('emcc','-O2','-std=gnu11','-D_GNU_SOURCE','-DBUILD_STATIC',
             '-I'+str(source/'include'),'-I'+str(build/'include'),'-I'+str(build),
             str(ROOT/'native/mgba_bridge.c'),str(libs[0]),
             '--no-entry','-sMODULARIZE=1','-sEXPORT_ES6=1',
             '-sEXPORT_NAME=createMgba','-sENVIRONMENT=web',
             '-sALLOW_MEMORY_GROWTH=1','-sMAXIMUM_MEMORY=268435456',
             '-sFORCE_FILESYSTEM=1','-sASSERTIONS=0',
             '-sEXPORTED_RUNTIME_METHODS=HEAPU8',
             '-sEXPORTED_FUNCTIONS='+json.dumps(EXPORTS,separators=(',',':')),
             '-lm','-o',str(js))
        wasm=Path(tmp)/'mgba.wasm'
        if not wasm.is_file() or wasm.read_bytes()[:8]!=b'\x00asm\x01\x00\x00\x00':
            parser.error('invalid Emscripten WebAssembly output')
        OUT.mkdir(parents=True,exist_ok=True)
        for name in ('mgba.js','mgba.wasm'):
            shutil.copy2(Path(tmp)/name,OUT/name)
        # MPL notice is obtained from the checked-out release, not invented.
        shutil.copy2(source/'LICENSE',ROOT/'LICENSES/mGBA.txt')
        manifest={
            'upstream':UPSTREAM,'tag':VERSION,'revision':revision,
            'license':'MPL-2.0',
            'emcc':subprocess.check_output(['emcc','--version'],text=True).splitlines()[0],
            'artifacts':{name:sha(OUT/name) for name in ('mgba.js','mgba.wasm')},
            'bridge_sha256':sha(ROOT/'native/mgba_bridge.c'),
        }
        (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        print('mGBA 0.10.5 compiled locally; commit web/mgba/* with corresponding source/notice')

if __name__=='__main__':main()
