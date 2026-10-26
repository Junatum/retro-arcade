/* Fullscreen/theater controller; requires no network or privileged browser APIs. */
export function setupFullscreen(section, button, doc, body) {
  let theater = false;
  const active = () => theater || doc.fullscreenElement === section;
  const sync = () => {
    const expanded = active();
    section.classList.toggle('theater-mode', theater);
    body.classList.toggle('theater-open', expanded);
    button.setAttribute('aria-pressed', String(expanded));
    button.textContent = expanded ? '⤢ 화면 축소' : '⛶ 전체화면';
    button.title = expanded ? '게임 전체화면 종료 (Esc)' : '게임을 화면 가득 표시';
  };
  const exit = async () => {
    if (theater) {
      theater = false;
    } else if (doc.fullscreenElement === section && typeof doc.exitFullscreen === 'function') {
      try { await doc.exitFullscreen(); } catch { /* Preserve the actual native state. */ }
    }
    sync();
  };
  const toggle = async () => {
    if (active()) return exit();
    if (typeof section.requestFullscreen === 'function') {
      try {
        await section.requestFullscreen();
        if (doc.fullscreenElement === section) {
          sync();
          return;
        }
      } catch { /* Browsers without page fullscreen use theater mode. */ }
    }
    theater = true;
    sync();
  };
  doc.addEventListener('fullscreenchange', sync);
  doc.addEventListener('keydown', event => {
    if (event.key === 'Escape' && theater) {
      theater = false;
      sync();
      event.preventDefault();
    }
  });
  sync();
  return { toggle, exit, active };
}
