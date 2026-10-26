# SmartSafeHub Retro Arcade

**SmartSafeHub Apps용 브라우저 기반 초경량 게임 에뮬레이터.**

버전: **0.1.0-r1**. 이 저장소는 **하나의 공개/배포 소스**만 관리합니다. OpenWrt 라우터는 정적 파일만 제공하고, 게임 실행은 PC 또는 모바일 **웹브라우저**에서 처리합니다. 게임 ROM은 라우터나 인터넷 서버로 전송되지 않습니다.

## EmulatorJS와의 관계

처음에는 [EmulatorJS](https://github.com/EmulatorJS/EmulatorJS) 4.2.3을 기반으로 NES, GB/GBC, GBA, PS1을 통합하는 구조를 개발했습니다. 그러나 **당시 확보한 JavaScript/WASM 바이너리의 정확한 대응 소스 및 개별 라이선스를 충분히 검증하지 못했으므로 이 공개 버전에는 포함하지 않습니다.** 따라서 **현재 릴리스는 EmulatorJS를 사용하거나 번들하지 않습니다.** 기존 EmulatorJS 개발 아이디어와 예제에 감사하며, 라이선스 및 소스 대응 검증 후 플랫폼 확대를 검토할 예정입니다.

현재 실제로 포함된 것은 **SmartSafeHub 프로젝트에서 직접 구현한 CHIP-8 인터프리터**이며, 별도의 실행 바이너리·외부 CDN·빌드 다운로드·NPM 설치가 필요하지 않습니다. CHIP-8은 역사적 8비트 가상 머신이며 NES/GB/PS1 ROM을 실행하지 않습니다.

## 실제 포함 기능

- CHIP-8 64×32 렌더링, 기본 35개 명령 범주, 0-F 입력 키패드, 딜레이/사운드 타이머(소리 출력은 제외)
- `.ch8`, `.c8` 파일을 로컬 브라우저에서 읽고 실행 (최대 3,584바이트)
- 자체 작성한 내장 `2026` 그래픽 데모, 일시정지 및 실행 종료
- 키보드 `1234 QWER ASDF ZXCV` / 모바일 터치 키패드
- HTML/JS/CSS만 사용하는 오프라인 정적 웹 실행
- 게임 ROM/BIOS, 외부 소스의 사전 컴파일 WASM, 외부 서버 통신 불포함

**제약:** Super-CHIP/XO-CHIP 확장, 오디오 출력, 세이브 상태, NES/GB/GBA/PS1은 미지원입니다. ROM마다 호환성은 달라질 수 있습니다. 브라우저 실제 게임 테스트와 OpenWrt 모델별 APK 설치 시험은 아직 완료되지 않았습니다.

## 로컬 미리보기

```sh
cd web
python3 -m http.server 8080
# http://127.0.0.1:8080/
```

**내장 데모 실행**으로 인터넷과 추가 ROM 없이 앱 인터프리터·화면 출력을 확인할 수 있습니다. 실제 게임을 사용하려면 배포 및 사용 권한이 있는 `.ch8`/`.c8` 파일을 선택하세요.

## OpenWrt 25.12+ (apk)

소스를 OpenWrt 빌드 환경의 `package/smartsafehub-app-retro-arcade/`에 두고 컴파일합니다.

```sh
make package/smartsafehub-app-retro-arcade/compile V=s
```

기존 SmartSafeHub 서명·승인된 APK 저장소를 통해 배포하고 `/retro-arcade/`를 열어 실행합니다. 앱 정보 `app-info.json`은 **카탈로그 등록 참고용**으로, `hub` API의 자동 등록을 구현한 것은 아닙니다. 지원 후보는 AX3000SM / AX3000SE / A3004T / Xiaomi AX3000T이며 GL-MT300N-V2는 제외합니다.

## 라이선스

- 이 릴리스의 앱 UI 및 CHIP-8 인터프리터: **GPL-3.0-or-later** (저장소 `LICENSE`)
- 현재 실행 시 사용하는 제3자 라이브러리: **없음**
- EmulatorJS, Libretro 코어, ROM, BIOS: **포함되지 않음**

자세한 내용은 [THIRD_PARTY.md](THIRD_PARTY.md), [SOURCE_OFFER.md](SOURCE_OFFER.md), [INSTALLATION_INFO.md](INSTALLATION_INFO.md)를 확인하세요. 자체 개발 소스는 공개되며, GPL에 따른 수정/재배포 조건이 적용됩니다.
