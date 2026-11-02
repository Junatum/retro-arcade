"""Guard browser E2E console selection against platform reordering."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BrowserPlatformSelectorsTests(unittest.TestCase):
    def test_no_positional_platform_selection_in_browser_e2e(self):
        source = (ROOT / 'tests/browser_e2e.py').read_text(encoding='utf-8')
        self.assertNotRegex(
            source,
            r"locator\(['\"]#systems button['\"]\)\.(?:nth|first|last)\(",
            'Platform order changed when Atari was added; select by data-system ID',
        )
        self.assertIn('def choose_platform(', source)

    def test_critical_platform_ids_remain_explicit_in_browser_e2e(self):
        source = (ROOT / 'tests/browser_e2e.py').read_text(encoding='utf-8')
        for system_id in ('chip8', 'nes', 'mame'):
            with self.subTest(system_id=system_id):
                self.assertIn(f"self.choose_platform(page, '{system_id}')", source)


if __name__ == '__main__':
    unittest.main()
