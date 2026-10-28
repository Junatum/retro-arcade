"""Documentation must describe the artifacts actually shipped in an APK."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseDocumentationTests(unittest.TestCase):
    def test_source_offer_uses_current_version_and_pinned_binary_sources(self):
        docs = (ROOT / 'docs/SOURCE_OFFER.md').read_text(encoding='utf-8')
        info = json.loads((ROOT / 'app-info.json').read_text(encoding='utf-8'))
        self.assertIn(info['version'], docs)
        for engine in ('mgba', 'gearsystem', 'blastem'):
            manifest = json.loads((ROOT / f'web/{engine}/manifest.json').read_text(encoding='utf-8'))
            for name in (f'{engine}.js', f'{engine}.wasm'):
                self.assertTrue((ROOT / f'web/{engine}/{name}').is_file())
            self.assertIn(manifest['revision'], docs)
            self.assertIn(manifest['upstream'], docs)
            self.assertIn(f'web/{engine}/manifest.json', docs)
        blastem = json.loads((ROOT / 'web/blastem/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(blastem['optimization'], ['-Oz', '-flto'])
        self.assertIn('scripts/build_sega.py', docs)
        self.assertIn('native/blastem_headless.h', docs)
        self.assertIn('LICENSES/', docs)
        self.assertIn('고정 리비전', docs)

    def test_readme_and_architecture_reflect_bundled_sega_engines(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        architecture = (ROOT / 'docs/ARCHITECTURE.md').read_text(encoding='utf-8')
        third_party = (ROOT / 'docs/THIRD_PARTY.md').read_text(encoding='utf-8')
        checklist = (ROOT / 'docs/RELEASE_CHECKLIST.md').read_text(encoding='utf-8')
        self.assertNotIn('이 패치에는 에뮬레이터 바이너리가 포함되지 않으며', readme)
        self.assertIn('JS/WASM', readme)
        self.assertIn('BlastEm WASM (`-Oz` / LTO)', architecture)
        for engine in ('gearsystem', 'blastem'):
            self.assertIn(f'web/{engine}/', architecture)
        self.assertIn('이미 포함', third_party)
        self.assertIn('대응 소스', checklist)
        self.assertIn('제목 옆', readme)

    def test_sound_guidance_matches_actual_compact_audio_ui(self):
        html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
        styles = (ROOT / 'web/styles.css').read_text(encoding='utf-8')
        audio = (ROOT / 'web/audio-controls.js').read_text(encoding='utf-8')
        self.assertEqual(html.count('id="sound-status"'), 1)
        self.assertEqual(html.count('id="sound"'), 1)
        self.assertIn('.sound-status{position:absolute;width:1px;height:1px;', styles)
        self.assertIn('button.title = explanation;', audio)
        self.assertNotIn('background:#193229', styles)


if __name__ == '__main__':
    unittest.main()
