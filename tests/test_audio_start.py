"""Source-level browser autoplay integration contracts (no frontend build)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AudioStartTests(unittest.TestCase):
    def test_play_click_activates_audio_before_any_async_file_or_wasm_load(self):
        src = (ROOT / 'web/app.js').read_text(encoding='utf-8')
        handler = src[src.index("$('play').onclick=async()=>{"):src.index("$('demo').onclick=")]
        self.assertLess(handler.index('audio.enable()'), handler.index('await file.arrayBuffer()'))
        self.assertIn('playNes(bytes,file.name,audio,audioRequestResult)', handler)
        self.assertIn('playSega(bytes,file.name,audio,audioRequestResult)', handler)
        self.assertIn('audio?.destroy()', handler)

    def test_sound_control_is_in_game_heading_and_has_retry_feedback(self):
        html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
        heading = html[html.index('<div class="player-heading-actions">'):html.index('<div class="player-shell">')]
        self.assertIn('id="sound"', heading)
        self.assertIn('aria-pressed="false"', heading)
        self.assertIn('id="sound-status"', heading)
        self.assertIn('aria-live="polite"', heading)
        self.assertEqual(html.count('id="sound"'), 1)
        app = (ROOT / 'web/app.js').read_text(encoding='utf-8')
        self.assertIn("if(audioState==='on')game?.resume?.()", app)
        self.assertIn("setAudioState('blocked')", app)

    def test_sound_explanation_does_not_add_banner_or_gameplay_gap(self):
        css = (ROOT / 'web/styles.css').read_text(encoding='utf-8')
        # The semantic live region remains for accessibility but no longer
        # occupies a full-width row or adds margins above the game canvas.
        self.assertIn('.sound-status{position:absolute;width:1px;height:1px;', css)
        self.assertNotIn('background:#193229', css)
        self.assertNotIn('.sound-status--attention{', css)
        controls = (ROOT / 'web/audio-controls.js').read_text(encoding='utf-8')
        self.assertIn('button.title = explanation;', controls)
        self.assertIn('hint.textContent = explanation;', controls)
