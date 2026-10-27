# SmartSafeHub Retro Arcade

SmartSafeHub Apps에서 제공하는 **로컬 레트로 게임 앱**입니다. 공유기는 웹 파일을 제공하며, 게임은 PC 또는 스마트폰 **브라우저에서 직접 실행**됩니다. 별도 계정이나 게임 서버는 필요하지 않습니다.

**현재 버전:** `0.1.0-r4`

## 지원 게임기

| 게임기 | 게임 파일 | 실행 엔진 | 터치 조작 |
|---|---|---|---|
| CHIP-8 | `.ch8`, `.c8` | 자체 JavaScript 실행기 | 4×4 숫자 키패드 |
| Game Boy / Game Boy Color | `.gb`, `.gbc` | mGBA 0.10.5 | 십자 방향키, A/B, SELECT/START |
| Game Boy Advance | `.gba` | mGBA 0.10.5 | 십자 방향키, A/B, SELECT/START, L/R |
| NES / Famicom | `.nes` | JSNES 2.1.0 | 십자 방향키, A/B, SELECT/START |

Game Boy, Game Boy Color, Game Boy Advance는 **하나의 mGBA 엔진**으로 실행됩니다. CHIP-8에는 내장 데모가 포함되어 있으며, **내장 데모 실행 버튼은 CHIP-8 선택 시에만 표시**됩니다.

## 주요 기능

- 게임기를 선택하고 **사용 권한이 있는 ROM 파일**을 브라우저에서 불러와 실행
- 실제 휴대용 게임기와 유사한 **터치 버튼 배치**, 키보드 조작 및 멀티터치
- 화면 비율을 유지하는 **전체화면** 및 모바일 화면 확장 모드
- 게임 시작 후 선택 화면 자동 숨김, 종료 시 복귀
- GB/GBC/GBA 게임의 **배터리 저장 데이터를 브라우저에 보관**하고 재실행 시 복원
- 실행에 외부 인터넷 연결이 필요 없고, **ROM 데이터는 공유기나 외부 서버로 전송되지 않음**

**제한 사항:** CHIP-8과 mGBA 오디오 및 세이브 스테이트는 지원하지 않습니다. NES 오디오는 사용자 조작으로 활성화할 수 있습니다. 게임 ROM과 상용 BIOS는 포함하지 않습니다. 지원 모델은 ipTIME AX3000SM/AX3000SE/A3004T 및 Xiaomi AX3000T이며, GL-MT300N-V2는 이 앱의 지원 대상에서 제외됩니다.

## 실행해 보기

SmartSafeHub Apps에서 설치한 뒤 **Retro Arcade**를 열고 게임기를 선택해 ROM을 불러오면 됩니다. CHIP-8은 ROM 없이 내장 데모도 실행할 수 있습니다.

개발 PC에서는 저장소 루트에서 다음 명령으로 실행할 수 있습니다.

```sh
python3 scripts/release_audit.py --release
python3 -m http.server 8080 --directory web
```

브라우저에서 <http://127.0.0.1:8080/>로 접속하세요. 게임 파일은 직접 준비해야 합니다. mGBA JS/WASM과 JSNES 원본 소스는 정식 릴리스 저장소에 포함되어야 하므로 **일반적인 실행이나 OpenWrt APK 빌드에서는 다시 컴파일하지 않습니다.**

## JSNES 소스 최초 준비

정확히 2.1.0 npm 패키지를 검증한 뒤 필요한 ES 모듈만 `web/vendor/jsnes/`에 포함합니다. 개발 PC에서 **한 번만** 수행하고 생성된 소스를 커밋하세요. 공유기와 OpenWrt 빌드 서버에는 npm/인터넷이 필요하지 않습니다.

```sh
python3 scripts/vendor_jsnes.py
python3 scripts/release_audit.py --release
```

다운로드가 차단된 환경에서는 JSNES 2.1.0 npm tarball과 npm 공식 SHA-512 integrity 값을 확보해 `--archive`, `--integrity` 옵션으로 지정합니다. 정식 릴리스에는 검증된 소스가 모두 포함되어야 합니다.

## 문서

- [아키텍처·개발 및 WASM 재빌드](docs/ARCHITECTURE.md)
- [설치·수정판 안내](docs/INSTALLATION_INFO.md)
- [릴리스 체크리스트](docs/RELEASE_CHECKLIST.md)
- [소스 제공 안내](docs/SOURCE_OFFER.md)
- [외부 오픈소스 고지](docs/THIRD_PARTY.md)
- [mGBA 라이선스](LICENSES/mGBA.txt)
- [JSNES 라이선스](LICENSES/JSNES.txt)
- [변경 이력](CHANGELOG.md)

프로젝트 UI와 CHIP-8 코드는 **GPL-3.0-or-later**, mGBA 코어는 **MPL-2.0**, JSNES는 **Apache-2.0** 라이선스를 따릅니다. 자세한 배포·소스 제공 조건은 위 문서에서 확인하세요.
