# SmartSafeHub Retro Arcade

[![CI](https://github.com/Junatum/retro-arcade/actions/workflows/verify.yml/badge.svg)](https://github.com/Junatum/retro-arcade/actions/workflows/verify.yml)
![OpenWrt](https://img.shields.io/badge/OpenWrt-Compatible-blue)
![Offline](https://img.shields.io/badge/Offline-Ready-brightgreen)
[![License](https://img.shields.io/github/license/Junatum/retro-arcade?label=License)](LICENSE)

SmartSafeHub Apps에서 제공하는 **로컬 레트로 게임 앱**입니다. 공유기는 웹 파일을 제공하며, 게임은 PC 또는 스마트폰 **브라우저에서 직접 실행**됩니다. 별도 계정이나 게임 서버는 필요하지 않습니다.

## 패키지 버전

아래 표는 SmartSafeHub 저장소에 배포된 Retro Arcade 패키지 버전입니다. Stable 및 Beta 배지는 최신 배포 버전을 자동으로 표시합니다.

| 패키지 | Stable | Beta |
| --- | --- | --- |
| Retro Arcade | [![Stable Retro Arcade](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Frepo.smartsafehub.com%2Fstable%2Fversions.json&query=%24.packages%5B%22smartsafehub-app-retro-arcade%22%5D&label=&color=brightgreen&cacheSeconds=300)](https://repo.smartsafehub.com/stable/versions.json) | [![Beta Retro Arcade](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Frepo.smartsafehub.com%2Fbeta%2Fversions.json&query=%24.packages%5B%22smartsafehub-app-retro-arcade%22%5D&label=&color=orange&cacheSeconds=300)](https://repo.smartsafehub.com/beta/versions.json) |

## 지원 게임기

| 게임기 | 게임 파일 | 실행 엔진 | 터치 조작 |
|---|---|---|---|
| CHIP-8 | `.ch8`, `.c8` | 자체 JavaScript 실행기 | 4×4 숫자 키패드 |
| Game Boy / Game Boy Color | `.gb`, `.gbc` | mGBA 0.10.5 | 십자 방향키, A/B, SELECT/START |
| Game Boy Advance | `.gba` | mGBA 0.10.5 | 십자 방향키, A/B, SELECT/START, L/R |
| NES / Famicom | `.nes` | JSNES 2.1.0 | 십자 방향키, A/B, SELECT/START |
| Game Gear | `.gg` | Gearsystem 3.9.21 | 십자 방향키, A/B, SELECT/START |
| Master System | `.sms` | Gearsystem 3.9.21 | 십자 방향키, A/B, SELECT/START |
| SG-1000 | `.sg` | Gearsystem 3.9.21 | 십자 방향키, A/B, SELECT/START |
| Mega Drive / Genesis | `.md`, `.gen`, `.bin` | BlastEm 1.0.0 계열 | 십자 방향키, A/B/C, X/Y/Z, START/MODE |
| Arcade (선택 드라이버) | `.zip` (내장 기기 식별자와 일치) | MAME 0.289 (로컬 JS/WASM 번들) | 십자 방향키, 버튼 1/2, COIN/START |

Game Boy, Game Boy Color, Game Boy Advance는 **하나의 mGBA 엔진**으로 실행됩니다. CHIP-8에는 직접 제작한 **패들 랠리** 미니게임이 포함되어 있으며, **데모 게임 플레이 버튼은 CHIP-8 선택 시에만 표시**됩니다.

## Arcade (MAME 0.289, 선택 드라이버)

아케이드 화면은 MAME 0.289의 두 소스 드라이버에서 빌드된 **기기 식별자**를 내장 WASM과 대조해 지원합니다. 게임 파일은 사용자가 직접 선택하며 공유기·서버로 전송하지 않습니다. 기기별로 추가 파일이 필요한 경우 실행에 실패할 수 있으며, 앱은 게임 파일을 제공하거나 다운로드하지 않습니다.

현재 저장소에는 개발 PC에서 빌드한 **MAME 0.289 `mame.js`·`mame.wasm`·`manifest.json`이 포함**되어 있습니다. 일반 실행 또는 OpenWrt APK 빌드를 위해 MAME를 다시 컴파일할 필요는 없습니다. `release_audit.py --release`는 파일 누락, 바뀐 바이너리 해시, 빌드 출처 불일치를 검사합니다. 다만 실제 아케이드 게임의 화면·입력·오디오·모바일 성능은 별도로 확인해야 하며, 자동 검사 통과만으로 실기 호환성을 보장하지 않습니다.

```sh
# 다음 단계는 엔진 변경 또는 대응 소스 재빌드가 필요할 때에만 실행합니다.
# 개발 PC에서 Emscripten 6.0.13 (SDL3 지원), Git, Python 준비
# 빌드 명령 실행 위치는 Retro Arcade 저장소 루트

git clone --depth 1 --branch mame0289 https://github.com/mamedev/mame.git /tmp/mame
[ ! -f /tmp/mame/ssharcade.wasm ] || cp /tmp/mame/ssharcade.wasm /tmp/mame-before.wasm
python3 scripts/build_mame.py --source /tmp/mame --jobs 2
# -Oz 빌드 후 이전 파일과 비교: ls -lh /tmp/mame-before.wasm web/mame/mame.wasm
# 기본 산출물: /tmp/mame/ssharcade.js + /tmp/mame/ssharcade.wasm
# 다른 위치에 생성된 경우 --js /path/to/file.js --wasm /path/to/file.wasm 지정
python3 scripts/cache_bust.py --update
python3 scripts/release_audit.py --release
```

MAME의 **`OPTIMIZE=z` (`-Oz`)** 빌드는 `BUILDDIR=build-ssharcade-oz`에 새 중간 산출물을 생성하므로 기존 `-Os` 오브젝트를 재사용하지 않습니다. `--package-only`는 앞서 성공한 `-Oz` 빌드의 로컬 영수증과 JS/WASM 해시가 일치할 때에만 허용합니다. 이전 빌드에 적용하면 실패하므로 먼저 위 빌드 명령을 실행하세요. `-Oz`는 성능과 브라우저 호환성에 영향을 줄 수 있어 실제 게임 테스트가 필요합니다.

실제 번들된 MAME 0.289 JS에서는 `Module.FS` 대신 **`FS_createPath`·`FS_createDataFile`** 런타임 함수를 제공합니다. Arcade 실행기는 이 API로 사용자가 선택한 ROM ZIP을 `/roms/`에 기록하며, 향후 `Module.FS`를 제공하는 호환 빌드도 처리합니다. 이 기능은 외부 다운로드를 사용하지 않습니다. 빌드 설정은 `OPTIMIZE=z` (`-Oz`), `BUILDDIR=build-ssharcade-oz`이며, 실제 JS/WASM 해시와 고정 커밋은 `web/mame/manifest.json`에 기록됩니다. 화면 스타일은 CSP를 유지하도록 로컬 `runner.css`로 분리돼 있습니다. 조작: 방향키, Z(버튼 1), X(버튼 2), 5(COIN), 1(1P START). MAME의 별도 실행기 내부 오디오/일시정지 지원은 실기 검증이 필요합니다. 상표상 앱 화면에서는 **Arcade**로 표시합니다.

## 주요 기능

- 게임기를 선택하고 **사용 권한이 있는 ROM 파일**을 브라우저에서 불러와 실행
- 실제 휴대용 게임기와 유사한 **터치 버튼 배치**, 키보드 조작 및 멀티터치
- 화면 비율을 유지하는 **전체화면** 및 모바일 화면 확장 모드
- 게임 시작 후 선택 화면 자동 숨김, 종료 시 복귀
- 지원 게임의 **배터리 저장 데이터(GB/GBC/GBA·NES·Sega)를 브라우저에 보관**하고 재실행 시 복원
- 실행에 외부 인터넷 연결이 필요 없고, **ROM 데이터는 공유기나 외부 서버로 전송되지 않음**

**제한 사항:** CHIP-8과 mGBA 오디오 및 세이브 스테이트는 지원하지 않습니다. NES 및 Sega 게임은 게임 시작 시 소리를 자동으로 켜려고 시도합니다. 제목 옆에서 현재 소리 상태를 확인하거나 음소거할 수 있고, 브라우저가 차단하면 같은 버튼으로 다시 켤 수 있습니다. 게임 ROM과 상용 BIOS는 포함하지 않습니다. 지원 모델은 ipTIME AX3000SM/AX3000SE/A3004T 및 Xiaomi AX3000T이며, GL-MT300N-V2는 이 앱의 지원 대상에서 제외됩니다.

## 실행해 보기

SmartSafeHub Apps에서 설치한 뒤 **Retro Arcade**를 열고 게임기를 선택해 ROM을 불러오면 됩니다. CHIP-8은 ROM 없이 **데모 게임 플레이** 버튼을 눌러 컴퓨터와 대결할 수 있습니다. 키보드 **W/S** 또는 화면의 **5/8** 버튼으로 오른쪽의 주황색 플레이어 패들을 위아래로 움직이세요. 왼쪽 초록색 패들은 컴퓨터이며, 파란색 테두리는 경기장을 나타냅니다. 득점 후 약 2초간 공이 멈추며 **5점 선승**으로 승리·패배 결과와 다시 플레이 버튼을 표시합니다. 화면 상단에는 양쪽 역할과 점수가 표시됩니다.

개발 PC에서는 저장소 루트에서 다음 명령으로 실행할 수 있습니다.

```sh
python3 scripts/release_audit.py --release
python3 -m http.server 8080 --directory web
```

브라우저에서 <http://127.0.0.1:8080/>로 접속하세요. 게임 파일은 직접 준비해야 합니다. mGBA·Gearsystem·BlastEm·MAME의 JS/WASM과 JSNES 원본 모듈은 현재 소스에 포함되어 있으므로 **일반적인 실행이나 OpenWrt APK 빌드에서는 다시 컴파일하지 않습니다.**

## Gearsystem · BlastEm 로컬 빌드

현재 저장소에는 **Gearsystem과 BlastEm의 로컬 빌드 결과물(JS/WASM), 매니페스트, 라이선스 고지**가 포함되어 있습니다. 따라서 일반적인 Retro Arcade 실행 및 OpenWrt APK 빌드에는 Emscripten이나 원본 소스의 재다운로드가 필요하지 않습니다. 아래 절차는 **엔진 소스·브리지·빌드 옵션 변경 또는 재현 빌드가 필요할 때만** 개발 PC에서 수행하세요. 이 절차가 게임 호환성을 자동으로 보증하지는 않습니다.

```sh
# 개발 PC의 emsdk 환경을 먼저 활성화합니다.
# Git Gearsystem 3.9.21, Mercurial BlastEm 공식 수정 커밋으로 고정합니다.
git clone --depth 1 --branch 3.9.21 https://github.com/drhelius/Gearsystem.git /path/to/Gearsystem
hg clone https://www.retrodev.com/repos/blastem /path/to/blastem
hg --cwd /path/to/blastem update -r 625fa5a85505
python3 scripts/build_sega.py gearsystem --source /path/to/Gearsystem
python3 scripts/build_sega.py blastem --source /path/to/blastem
python3 scripts/cache_bust.py --update
python3 scripts/release_audit.py --release
```

BlastEm은 코어 컴파일에 `-Oz -flto`를 적용하고 `make -B`로 기존 오브젝트 재사용을 방지합니다. 브리지와 최종 링크에도 크기 최적화를 적용합니다. Gearsystem은 기존 `-O2` 빌드를 유지합니다. 각 엔진의 정확한 upstream 리비전, Emscripten 버전, JS/WASM 해시 및 BlastEm 최적화 옵션은 `web/gearsystem/manifest.json`, `web/blastem/manifest.json`에 기록됩니다. **빌드 스크립트를 수정한 경우 BlastEm 재빌드가 필요**하며, 매니페스트가 이전 빌드와 일치하지 않으면 `--release` 검사가 실패합니다.

Gearsystem이 출력하는 `.bc` 파일은 실제로 `emar` 정적 아카이브이며 빌드 스크립트가 형식을 확인해 `.a`로 링크합니다. BlastEm의 macOS용 `sed` 처리와 브라우저 전용 비게임 디버그 기능도 빌드 스크립트에서 처리합니다. 게임 ROM과 상용 BIOS는 포함하지 않습니다.

**상용 APK 배포 전:** 각 JS/WASM의 대응 소스(정확한 리비전), 빌드 스크립트와 필요한 변경분, 라이선스 고지에 접근할 수 있어야 합니다. GitHub의 최신 브랜치 주소만으로는 배포된 바이너리와 동일한 소스를 보장하지 않습니다. [소스 제공 안내](docs/SOURCE_OFFER.md)와 [출시 체크리스트](docs/RELEASE_CHECKLIST.md)를 확인하세요.

## JSNES 소스 최초 준비

정확히 2.1.0 npm 패키지를 검증한 뒤 필요한 ES 모듈만 `web/vendor/jsnes/`에 포함합니다. 개발 PC에서 **한 번만** 수행하고 생성된 소스를 커밋하세요. 공유기와 OpenWrt 빌드 서버에는 npm/인터넷이 필요하지 않습니다.

```sh
python3 scripts/vendor_jsnes.py
python3 scripts/release_audit.py --release
```

다운로드가 차단된 환경에서는 JSNES 2.1.0 npm tarball과 npm 공식 SHA-512 integrity 값을 확보해 `--archive`, `--integrity` 옵션으로 지정합니다. 정식 릴리스에는 검증된 소스가 모두 포함되어야 합니다.

## 배포 전 안정성 검사

소스 변경 후 `python3 scripts/cache_bust.py --update`로 JavaScript/CSS URL의 내용 해시를 갱신합니다. OpenWrt APK 빌드나 공유기에서는 이 명령을 실행하지 않습니다.

```sh
python3 scripts/cache_bust.py --check
python3 scripts/release_audit.py --release
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

실제 Chromium HTTP 통합 테스트는 개발 환경에서 Playwright가 준비된 경우 `python3 tests/browser_e2e.py -v`로 실행합니다. 이 명령은 테스트용 임시 HTTP 서버만 사용하고 게임 파일을 내려받지 않습니다.

배터리 저장 게임의 경우 저장 실패·복원 실패를 플레이어에 표시하며 종료 시 재확인합니다. 브라우저 종료·전원 손실 등 갑작스러운 상황에서는 마지막 저장이 보장되지 않으므로 진행 중에는 수시로 게임 내부 저장을 수행하세요.

## 문서

- [아키텍처·개발 및 WASM 재빌드](docs/ARCHITECTURE.md)
- [설치·수정판 안내](docs/INSTALLATION_INFO.md)
- [릴리스 체크리스트](docs/RELEASE_CHECKLIST.md)
- [소스 제공 안내](docs/SOURCE_OFFER.md)
- [외부 오픈소스 고지](docs/THIRD_PARTY.md)
- [mGBA 라이선스](LICENSES/mGBA.txt)
- [JSNES 라이선스](LICENSES/JSNES.txt)
- [Gearsystem 라이선스](LICENSES/Gearsystem.txt)
- [BlastEm 라이선스](LICENSES/BlastEm.txt)
- [MAME GPLv2 라이선스](LICENSES/MAME-GPL2.txt)
- [변경 이력](CHANGELOG.md)

프로젝트 UI와 CHIP-8 코드는 **GPL-3.0-or-later**, mGBA 코어는 **MPL-2.0**, JSNES는 **Apache-2.0**, Gearsystem과 BlastEm은 **GPLv3 계열**, MAME는 프로젝트 전체 기준 **GPL-2.0-or-later**이며 Libretro API 헤더는 **MIT** 라이선스를 따릅니다. 자세한 배포·소스 제공 조건은 위 문서에서 확인하세요.
