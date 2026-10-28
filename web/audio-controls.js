/* Local-only audio UI. The browser, not a global autoplay setting, decides
 * whether audio may begin without an additional click. */
export function supportsGameAudio(systemId) {
  return systemId === 'nes' || systemId === 'blastem' || systemId.startsWith('gearsystem-');
}

const STATES = Object.freeze({
  starting: ['🔊 소리 연결 중', '소리를 자동으로 켜고 있습니다. 소리가 안 나오면 위 버튼을 눌러 주세요.'],
  on: ['🔊 소리 켜짐', '소리 켜짐 · 버튼을 누르면 음소거할 수 있습니다.'],
  off: ['🔇 소리 꺼짐', '소리가 꺼져 있습니다. 위 버튼을 눌러 다시 켤 수 있습니다.'],
  blocked: ['🔊 소리 켜기', '브라우저가 자동 사운드를 제한했습니다. 위의 소리 켜기 버튼을 눌러 주세요.'],
});

export function paintAudioState(button, hint, state) {
  const [label, explanation] = STATES[state] || STATES.blocked;
  button.textContent = label;
  button.setAttribute('aria-pressed', String(state === 'on'));
  // Keep the longer explanation available on hover without adding a banner.
  button.title = explanation;
  button.classList.toggle('sound-button--on', state === 'on');
  button.classList.toggle('sound-button--attention', state === 'blocked' || state === 'off');
  hint.textContent = explanation;
}
