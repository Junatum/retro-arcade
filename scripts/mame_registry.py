#!/usr/bin/env python3
"""Check the first-party arcade machine allowlist against bundled MAME 0.289.

Extract *machine identifiers*, not ROM names, URLs or downloadable assets, from
both selected driver's registration tables. This is deliberately tied to the
pinned WASM; if upstream layout changes, fail closed and review the new build.
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WASM = ROOT / 'web/mame/mame.wasm'
REGISTRY = ROOT / 'web/mame/machines.js'
_SECTIONS = (
    ('SGalaxian (Namco set 1)', '13gmgalax_state'),
    ('Puck Man (Japan, set 1)', '13alibaba_state'),
)


def embedded_machines(wasm: bytes) -> tuple[str, ...]:
    if not wasm.startswith(b'\x00asm\x01\x00\x00\x00'):
        raise ValueError('not a MAME WebAssembly file')
    chunks = [v.decode('ascii') for v in re.findall(rb'[\x20-\x7e]{4,}', wasm)]
    ids = []
    for start, end in _SECTIONS:
        starts = [i for i, v in enumerate(chunks) if start in v]
        if len(starts) != 1:
            raise ValueError(f'MAME registration table missing/ambiguous: {start}')
        a = starts[0]
        ends = [i for i, v in enumerate(chunks[a+1:], a+1) if end in v]
        if len(ends) != 1:
            raise ValueError(f'MAME registration table terminator missing/ambiguous: {end}')
        ids.extend(v for v in chunks[a:ends[0]] if re.fullmatch(r'[a-z][a-z0-9_]{1,30}', v))
    if len(ids) < 10 or len(ids) != len(set(ids)) or not {'pacman', 'galaxian', 'mooncrst', 'puckman'}.issubset(ids):
        raise ValueError('MAME machine registry is incomplete or duplicated')
    return tuple(ids)


def render(machines: tuple[str, ...]) -> str:
    lines = ['/* First-party, machine-ID-only allowlist extracted from the bundled MAME 0.289',
             ' * driver registration tables (pacman.cpp + galaxian.cpp). No ROM metadata,',
             ' * downloads or game assets. Keep in sync when rebuilding MAME. */',
             'export const ARCADE_MACHINES = Object.freeze([']
    for offset in range(0, len(machines), 12):
        lines.append('  ' + ','.join(repr(v) for v in machines[offset:offset+12]) + ',')
    lines.extend((']);', 'const MACHINE_IDS = new Set(ARCADE_MACHINES);',
                  'export function arcadeMachine(filename) {',
                  "  const match = /^([a-z][a-z0-9_]{1,30})\\.zip$/i.exec(String(filename || '').trim());",
                  '  const id = match?.[1]?.toLowerCase();',
                  '  return id && MACHINE_IDS.has(id) ? id : null;',
                  '}',
                  'export function isArcadeMachine(id) { return MACHINE_IDS.has(id); }', ''))
    return '\n'.join(lines)


def check(wasm: Path = WASM, registry: Path = REGISTRY, update: bool = False) -> bool:
    expected = render(embedded_machines(wasm.read_bytes()))
    if update:
        registry.write_text(expected, encoding='utf-8')
        return True
    return registry.is_file() and registry.read_text(encoding='utf-8') == expected


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--update', action='store_true')
    args = p.parse_args()
    try:
        if not check(update=args.update):
            p.exit(1, 'FAIL: MAME machine registry does not match bundled WASM\n')
    except (OSError, ValueError) as exc:
        p.exit(1, f'FAIL: MAME registry: {exc}\n')
    print('PASS: MAME machine registry matches bundled WASM')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
