#!/usr/bin/env python3
"""Keep bundled JS/CSS import URLs content-addressed without a frontend build.

Never alters third-party JS or WebAssembly files; OpenWrt packaging remains offline.
"""
import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'
# Only first-party source modules are rewritten. Vendor code remains byte-for-byte pinned.
MODULES = ('mame/machines.js', 'mame/runner.js', 'mame-player.js', 'app.js', 'demo.js', 'chip8.js', 'controller.js', 'systems.js',
           'battery-store.js', 'fullscreen.js', 'mgba-player.js',
           'jsnes-player.js', 'nes-audio.js', 'sega-player.js',
           'audio-controls.js')
IMPORT = re.compile(r"(?P<prefix>(?:\bfrom\s*|\bimport\s*\(\s*)['\"])(?P<url>\.{1,2}/[^'\"\s)]+\.js)(?:\?v=[^'\"]+)?(?P<suffix>['\"])")
CSS = re.compile(r'(?P<pre>href="\./styles\.css)(?:\?v=[a-f0-9]{12})?(?P<post>")')
ENTRY = re.compile(r'(?P<pre>src="\./app\.js)(?:\?v=[^\"]+)?(?P<post>")')
MAME_ENTRY = re.compile(r'(?P<pre>src="\./runner\.js)(?:\?v=[^\"]+)?(?P<post>")')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def expected_contents(web=WEB):
    """Return expected source contents after dependency hashes converge."""
    # macOS exposes /var through /private/var. Resolve both sides of the
    # containment check so pathlib never compares aliased and real paths.
    web = Path(web).resolve()
    sources = {name: (web / name).read_text(encoding='utf-8') for name in MODULES}
    # A module graph is acyclic today; iterative computation also rejects a future cycle.
    for _ in range(len(MODULES) + 1):
        changed = False
        for name in MODULES:
            parent = web / name
            def update(match):
                url = match.group('url')
                target = (parent.parent / url).resolve()
                if not target.is_relative_to(web) or not target.is_file():
                    raise ValueError(f'invalid local JS dependency: {name}: {url}')
                relative = target.relative_to(web).as_posix()
                content = sources.get(relative)
                sha = hashlib.sha256(content.encode('utf-8')).hexdigest()[:12] if content is not None else digest(target)
                return f"{match.group('prefix')}{url}?v={sha}{match.group('suffix')}"
            result = IMPORT.sub(update, sources[name])
            if result != sources[name]:
                sources[name] = result
                changed = True
        if not changed:
            break
    else:
        raise ValueError('module dependency hashes did not stabilize (import cycle?)')
    for page in ('index.html', 'open-source.html'):
        text = (web / page).read_text(encoding='utf-8')
        css_hash = digest(web / 'styles.css')
        text = CSS.sub(lambda m: f"{m['pre']}?v={css_hash}{m['post']}", text)
        if page == 'index.html':
            app_hash = hashlib.sha256(sources['app.js'].encode('utf-8')).hexdigest()[:12]
            text = ENTRY.sub(lambda m: f"{m['pre']}?v={app_hash}{m['post']}", text)
        sources[page] = text
    mame_html = (web / 'mame/runner.html').read_text(encoding='utf-8')
    mame_hash = hashlib.sha256(sources['mame/runner.js'].encode('utf-8')).hexdigest()[:12]
    sources['mame/runner.html'] = MAME_ENTRY.sub(
        lambda m: f"{m['pre']}?v={mame_hash}{m['post']}", mame_html)
    return sources


def check(update=False, web=WEB):
    web = Path(web).resolve()
    changed = []
    for name, expected in expected_contents(web).items():
        file = web / name
        if file.read_text(encoding='utf-8') != expected:
            changed.append(name)
            if update:
                file.write_text(expected, encoding='utf-8')
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update', action='store_true', help='refresh dependency URLs after changing sources')
    parser.add_argument('--check', action='store_true', help='fail if any content hash is stale')
    args = parser.parse_args()
    if args.update == args.check:
        parser.error('choose exactly one of --update or --check')
    try:
        changed = check(update=args.update)
    except (OSError, ValueError) as error:
        parser.exit(1, f'FAIL: {error}\n')
    if changed and args.check:
        parser.exit(1, 'FAIL: stale browser cache hashes: ' + ', '.join(changed) + '\n')
    print(('UPDATED: ' if changed else 'PASS: browser cache hashes ') + ', '.join(changed))


if __name__ == '__main__':
    main()
