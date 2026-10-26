#!/usr/bin/env python3
"""Vendor unmodified JSNES 2.1.0 ESM source once; OpenWrt builds stay offline.

Run on a connected development PC: python3 scripts/vendor_jsnes.py
Or: python3 scripts/vendor_jsnes.py --archive /path/to/jsnes-2.1.0.tgz
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import re
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2.1.0'
METADATA_URL = f'https://registry.npmjs.org/jsnes/{VERSION}'
EXPECTED_TARBALL = f'https://registry.npmjs.org/jsnes/-/jsnes-{VERSION}.tgz'
IMPORTS = re.compile(r'''(?:from\s+|import\s*\(?\s*)["'](\.[^"']+)["']''')


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'SmartSafeHub-vendor-jsnes/1'}), timeout=45) as response:
        return response.read()


def verify_integrity(data: bytes, integrity: str) -> None:
    algo, _, expected = integrity.partition('-')
    if algo != 'sha512' or not expected or base64.b64encode(hashlib.sha512(data).digest()).decode() != expected:
        raise ValueError('JSNES npm tarball integrity verification failed')


def unpack_source(archive: bytes) -> tuple[dict[str, bytes], bytes]:
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tf:
        members = {entry.name: entry for entry in tf if entry.isfile()}
        pkg_file = members.get('package/package.json')
        if not pkg_file:
            raise ValueError('invalid JSNES archive (package.json missing)')
        info = json.loads(tf.extractfile(pkg_file).read())
        if info.get('name') != 'jsnes' or info.get('version') != VERSION or info.get('license') != 'Apache-2.0':
            raise ValueError('unexpected JSNES package version/license')
        lic = members.get('package/LICENSE')
        if not lic:
            raise ValueError('JSNES Apache license missing')
        license_bytes = tf.extractfile(lic).read()
        if b'Apache License' not in license_bytes:
            raise ValueError('unrecognized JSNES LICENSE')
        selected: dict[str, bytes] = {}
        pending = ['nes.js', 'controller.js']
        while pending:
            name = pending.pop()
            if name in selected:
                continue
            if not re.fullmatch(r'[A-Za-z0-9_./-]+\.js', name) or '..' in Path(name).parts:
                raise ValueError(f'unexpected JSNES file path: {name}')
            member = members.get('package/src/' + name)
            if not member:
                raise ValueError(f'missing JSNES module: {name}')
            contents = tf.extractfile(member).read()
            selected[name] = contents
            for module in IMPORTS.findall(contents.decode('utf-8')):
                dependency = (Path(name).parent / module).as_posix()
                # normalize ./ and ../ while rejecting escape outside src
                from posixpath import normpath
                dependency = normpath(dependency)
                if dependency.startswith('../') or dependency.startswith('/'):
                    raise ValueError(f'JSNES import escaped src: {name} -> {module}')
                pending.append(dependency)
        return selected, license_bytes


def vendor(archive: bytes, integrity: str) -> int:
    verify_integrity(archive, integrity)
    source, license_bytes = unpack_source(archive)
    # Only publish a complete, verified vendor directory; do not leave partial files.
    target = ROOT / 'web/vendor/jsnes'
    with tempfile.TemporaryDirectory(prefix='retro-jsnes-') as directory:
        temp = Path(directory) / 'jsnes'
        for name, content in source.items():
            path = temp / 'src' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        manifest = {
            'package': 'jsnes', 'version': VERSION, 'license': 'Apache-2.0',
            'upstream': 'https://github.com/bfirsh/jsnes', 'npm_integrity': integrity,
            'files': {f'src/{name}': hashlib.sha256(data).hexdigest() for name, data in sorted(source.items())},
        }
        (temp / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        import shutil
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(temp, target)
    license_target = ROOT / 'LICENSES/JSNES.txt'
    license_target.parent.mkdir(parents=True, exist_ok=True)
    license_target.write_bytes(license_bytes)
    print(f'PASS: JSNES {VERSION} installed ({len(source)} unmodified modules, SHA-512 archive checked)')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='offline npm package tarball to vendor')
    parser.add_argument('--integrity', help='sha512-... npm integrity (required with --archive)')
    args = parser.parse_args()
    if args.archive:
        if not args.integrity:
            parser.error('--archive requires --integrity for verified provenance')
        archive, integrity = args.archive.read_bytes(), args.integrity
    else:
        metadata = json.loads(fetch(METADATA_URL))
        if metadata.get('name') != 'jsnes' or metadata.get('version') != VERSION:
            raise ValueError('npm metadata does not match pinned JSNES version')
        dist = metadata.get('dist', {})
        if dist.get('tarball') != EXPECTED_TARBALL:
            raise ValueError('npm tarball URL does not match pinned version')
        integrity = dist['integrity']
        archive = fetch(EXPECTED_TARBALL)
    return vendor(archive, integrity)


if __name__ == '__main__':
    raise SystemExit(main())
