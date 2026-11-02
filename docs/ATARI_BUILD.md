# Atari 2600 — 오프라인 빌드 및 라이선스 검증

- 원본: https://github.com/mohrt/atari2600 (Monte Ohrt, MIT).
- SmartSafeHub의 자체 브리지는 GPL-3.0-or-later. `LICENSES/Atari2600.txt`에 MIT 원문 제공.
- **기본 배포에는 ROM이 없습니다.** 원본 `npm run fetch:games`, `fetch:dormann`, `index.html`, `main.ts`, `games.ts`, `analytics.ts`, `public/`, `scripts/`, `node_modules/`, 외부 UI/폰트는 복사하거나 실행하지 않습니다.
- 원본을 통째로 웹 루트에 복사하거나 공식 GitHub Pages 결과물을 복사하지 마세요.

## 고정 커밋 검토와 로컬 빌드

1. 개발 PC에서 `git clone https://github.com/mohrt/atari2600 /path/to/atari2600`.
2. **상용 승인 전에** 해당 커밋에서 모든 파일의 저작권·SPDX·소스 출처, MIT, 제3자 리소스, npm 의존성을 검토합니다. 이 검토는 자동 검사만으로 대체되지 않습니다.
3. 승인한 커밋의 정확한 40자리 SHA를 기록하고 `git -C /path/to/atari2600 checkout --detach <SHA>`로 고정합니다. **`main`을 그대로 사용하지 않습니다.**
4. 개발 PC에 준비된 esbuild(상용 재배포 가능 라이선스와 버전을 별도 확인)를 사용해 아래를 실행합니다. 이 도구는 다운로드를 하지 않습니다.

```sh
python3 scripts/build_atari.py --source /path/to/atari2600 --revision <40자리-SHA> --audit-only
python3 scripts/build_atari.py --source /path/to/atari2600 --revision <40자리-SHA> --esbuild /path/to/esbuild
python3 scripts/cache_bust.py --update
python3 scripts/release_audit.py --release
```

결과 `web/atari2600/engine.js`, `manifest.json`은 개발 PC에서만 생성됩니다. 생성한 실행 파일과 manifest를 릴리스용 저장소에 반영하거나, OpenWrt 패키징 전에 같은 명령으로 재생성해야 합니다. `Makefile`은 네트워크에서 자동으로 빌드하거나 다운로드하지 않으며 바이너리가 없으면 실패합니다.

`manifest.json`은 고정 SHA, 전체 `src` 해시 인벤토리, 실제 컴파일된 파일 및 브리지/빌드 스크립트 해시를 기록합니다. CI는 JS 파일이 바뀌거나 출처가 없으면 배포를 차단합니다. **CI 감사만으로 원본의 독립 구현을 법적으로 확증하지는 못합니다.** 새 SHA로 업데이트할 때는 사람이 소스 출처를 재검토해야 합니다.

## 제외 범위 및 개인정보 보호

- Atari `.a26` 외 `.bin/.rom/.zip`은 지원하지 않습니다(기존 플랫폼의 확장자와 충돌 방지).
- 게임 다운로드, 게임 카탈로그 자동 조회, Google Analytics 및 원본 외부 CDN을 포함하지 않습니다.
- ROM은 브라우저의 사용자가 직접 선택하며, 공유기/서버로 업로드하지 않습니다.
- 브라우저 IndexedDB에 게임별 실행 상태를 저장하며 공유기로 전송하지 않습니다.
- 에뮬레이터 코드 및 배포자의 수정 내역에 대한 대응 소스·재현 절차와 MIT 라이선스 고지를 보존하세요.

## 아직 별도 검증이 필요한 부분

이 패치 작성 환경에서 원본 Git 저장소와 Node esbuild 바이너리를 가져올 수 없어 실제 Atari 엔진 번들 빌드 및 Atari 게임 ROM 실행 테스트는 수행하지 못했습니다. 따라서 초기 상태의 릴리스 감사는 의도적으로 실패하며, **로컬 빌드·실기 브라우저 테스트·전수 라이선스 감사 완료 전에는 상용 배포하지 마세요.**
