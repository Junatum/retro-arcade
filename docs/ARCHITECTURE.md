# 아키텍처 및 개발 가이드

SmartSafeHub Retro Arcade의 구현, 빌드 및 검증 방법입니다. 사용자 소개는 [README](../README.md)를 참조하세요.

## 실행 구조

```text
SmartSafeHub Apps → OpenWrt 정적 웹서버 (/www/retro-arcade/)
    └─ 사용자 브라우저 (HTML / JS / WASM)
        ├─ CHIP-8: 내장 JavaScript 코어
        ├─ GB/GBC/GBA: mGBA 0.10.5 C 코어 → Emscripten WASM
        └─ NES/Famicom: JSNES 2.1.0 ES modules (no WASM)
```

ROM은 브라우저에서만 처리합니다. 외부 CDN, 게임 서버, 상용 BIOS는 사용하지 않습니다.

## 파일 구성

| 경로 | 역할 |
|---|---|
| `web/app.js`, `web/systems.js` | 플랫폼 선택, ROM 로딩, 입력 및 렌더링 루프 |
| `web/controller.js` | CHIP-8 4×4 키패드, GB/GBC 십자키·A/B·SELECT/START, GBA L/R 터치 컨트롤러와 멀티터치 해제 |
| `web/chip8.js`, `web/demo.js` | CHIP-8 실행기·내장 데모 |
| `web/jsnes-player.js`, `web/nes-audio.js` | NES 실행/프레임 변환, SRAM, HTTP 환경의 Web Audio (사용자 활성화) |
| `web/vendor/jsnes/` | 정확히 JSNES 2.1.0 원본 ES 모듈·매니페스트, 처음 개발 시 한 번 내려받아 포함 |
| `scripts/vendor_jsnes.py` | npm SHA-512 무결성 검증, 원본 모듈 의존성 트리 추출 |
| `web/mgba-player.js` | mGBA JS/WASM 호출, 해상도 전환, 배터리 저장 |
| `web/battery-store.js` | IndexedDB 기반 브라우저 전용 ROM 세이브 저장소 |
| `native/mgba_bridge.c` | mGBA `mCore` 호출 (GB/GBC/GBA), 프레임버퍼/키/세이브 API |
| `scripts/build_mgba.py` | 공식 소스로부터 로컬 WASM/매니페스트 빌드 |
| `web/mgba/` | 고정된 `mgba.js`, `mgba.wasm`, `manifest.json` |
| `scripts/release_audit.py` | 버전, 출처, 파일 해시, ABI 브리지 일치 검증 |
| `Makefile`, `app-info.json` | OpenWrt APK 패키징 / SmartSafeHub Apps 메타데이터 |

## 플랫폼 및 저장

- CHIP-8: `.ch8`, `.c8` 최대 3,584바이트, 내장 데모 제공. 내장 데모 실행 버튼은 CHIP-8에서만 표시되며 다른 플랫폼에서는 숨깁니다.
- Game Boy / Color: `.gb`, `.gbc`, 최대 8MiB, mGBA의 GB 코어, 160×144 화면.
- Game Boy Advance: `.gba`, 최대 32MiB, mGBA의 GBA 코어, 240×160 화면.
- NES/Famicom: `.nes`, 최대 8MiB, JSNES 코어, 256×240 화면. 십자키·A/B·SELECT/START, 브라우저 IndexedDB에 배터리 RAM 저장. 오디오 켜기는 사용자가 클릭해야 하며 Web Audio 지원 브라우저에 한합니다.
- 방향키, X(A)/Z(B), Enter(Start)/Shift(Select); GBA는 A(L)/S(R) 추가 지원.
- 브라우저의 IndexedDB(`smartsafehub-retro-arcade`)에 `mgba:` 접두사로 배터리 저장 데이터를 보관합니다. ROM 파일은 업로드하지 않습니다.

**이전 별도 코어의 GB/GBC 배터리 파일은 mGBA 저장 형식과 호환이 보장되지 않습니다.** 자동으로 불러오거나 변환하지 않으며, 브라우저 데이터를 삭제하지 않고 보관할 것을 권장합니다.

## mGBA 0.10.5 WASM 번들 및 재빌드

현재 저장소에는 GB/GBC/GBA 지원 브리지와 일치하는 `mgba.js`, `mgba.wasm`, `manifest.json`이 포함됩니다. 평소 앱 실행·OpenWrt APK 빌드 시 **WASM 재빌드는 필요하지 않습니다.** 공식 mGBA 코어, `native/mgba_bridge.c` 또는 빌드 옵션을 변경할 때만 개발 PC에서 재빌드하세요. 변경된 브리지와 기존 WASM이 불일치하면 릴리스 검사에서 배포를 차단합니다.

개발 PC에 Git, CMake, Emscripten(`emcc`, `emcmake`)을 설치하고 공식 소스를 준비합니다.

```sh
git clone --depth 1 --branch 0.10.5 https://github.com/mgba-emu/mgba.git /tmp/mgba-0.10.5
python3 scripts/build_mgba.py --source /tmp/mgba-0.10.5
python3 scripts/release_audit.py --release
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

재빌드한 경우 `web/mgba/mgba.js`, `mgba.wasm`, `manifest.json`이 갱신됩니다. 해당 세 파일을 함께 커밋해야 합니다. 검사는 정확한 upstream 태그/커밋, SHA-256, 브리지 코드와 매니페스트 일치를 검사합니다. 일반 OpenWrt APK 빌드에는 Emscripten이 필요하지 않습니다.

배포에 앞서 본인이 적법하게 보유한 GB/GBC/GBA ROM으로 화면·입력·세이브/재실행, 브라우저 HTTP 환경의 동작을 확인하세요. **CI 단위 테스트와 매니페스트 검사만으로 실기기 실행까지 검증한 것은 아닙니다.**

## OpenWrt 설치

소스를 OpenWrt `package/smartsafehub-app-retro-arcade/`에 두고 다음을 실행합니다.

```sh
make package/smartsafehub-app-retro-arcade/compile V=s
```

웹 진입점은 `/retro-arcade/`, 설치 경로는 `/www/retro-arcade/`입니다. 지원 모델은 ipTIME AX3000SM/AX3000SE/A3004T, Xiaomi AX3000T이며 GL-MT300N-V2는 제외합니다. 장치별 설치 확인은 [체크리스트](RELEASE_CHECKLIST.md)를 참조하세요.

## 라이선스

UI/CHIP-8은 GPL-3.0-or-later이고 mGBA 코어는 MPL-2.0입니다. [오픈소스 고지](THIRD_PARTY.md), [소스 제공 안내](SOURCE_OFFER.md), [설치 안내](INSTALLATION_INFO.md)를 참조하세요.

## JSNES 2.1.0 (원본 ES 모듈, 빌드 없음)

JSNES는 `scripts/vendor_jsnes.py`로 npm 2.1.0 타르볼의 SHA-512를 검증해 `web/vendor/jsnes/src/`에 필요한 원본 ES 모듈만 복사합니다. 원본 내용의 SHA-256을 `manifest.json`에 기록하며 `release_audit.py --release`가 변경·누락을 차단합니다. **OpenWrt APK 빌드 과정은 인터넷을 사용하지 않습니다.** 미준비 상태에서는 릴리스 검사가 실패합니다. `python3 scripts/vendor_jsnes.py`는 개발 PC에서 한 번만 실행하세요.

외부 CDN 및 FCEUmm/libretro 코어를 사용하지 않습니다. HTTP 환경에서 오디오가 가능한 경우 `AudioContext`와 `ScriptProcessorNode`로 재생합니다(일부 브라우저는 제한될 수 있음). `.nes` 파일은 서버로 업로드하지 않습니다.

### 내장 CHIP-8 미니게임

`web/demo.js`는 Atari ROM 등을 가져오지 않고 자체 작성한 **패들 랠리**의 CHIP-8 명령어·스프라이트를 조립합니다. 앱의 기존 CHIP-8 인터프리터만 사용하며 게임 파일을 공유기로 업로드하지 않습니다. W/S(터치 키패드 5/8)로 오른쪽 플레이어 패들을 움직이고 왼쪽 컴퓨터를 상대로 점수를 얻습니다. 내장 게임에 한해 오른쪽 플레이어 패들을 주황색으로 강조하며 외부 CHIP-8 ROM의 색상은 변경하지 않습니다.

내장 패들 랠리에서는 코트 경계선과 플레이어 색상만 브라우저의 화면 변환 단계에서 표시하므로 외부 CHIP-8 ROM의 픽셀은 변경되지 않습니다. 득점 후 CHIP-8 지연 타이머(60Hz, 120틱)로 약 2초간 서브를 대기하며, 5점에 먼저 도달하면 ROM이 종료 상태를 고정하고 웹 UI가 승리·패배 및 다시 플레이 버튼을 표시합니다.

## 출시 안정화

- `web/save-session.js`: 읽기·복원 오류를 사용자에게 알리고, 저장 데이터를 즉시 복사하여 IndexedDB 쓰기를 순서대로 처리합니다. 브라우저가 강제 종료되면 비동기 저장 완료는 보장할 수 없습니다.
- `scripts/cache_bust.py --update`: 개발할 때만 실행하며 첫 번째 파티 JavaScript import와 HTML의 CSS·엔트리포인트에 내용 해시를 부여합니다. `--check`는 CI와 OpenWrt 릴리스 검사에서 강제합니다.
- 서드파티 JSNES 원본 코드는 변조하지 않고 벤더 매니페스트로 검증합니다. 업데이트 시 벤더 모듈 경로를 포함한 캐시 정책 재검증이 필요합니다.
- `tests/browser_e2e.py`: 테스트 PC 또는 GitHub CI에서 Chromium/Playwright로 실제 HTTP, 320/390/1280px 화면, NES 합성 테스트 ROM 및 mGBA WASM 초기화를 검사합니다. 별도 상용 게임 ROM은 사용하지 않습니다.
- OpenWrt APK 자체는 오프라인으로 검증된 JS/WASM 자산만 설치하며 `vendor_jsnes.py`, `build_mgba.py`를 재실행하지 않습니다.
