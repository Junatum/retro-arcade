# Open-source attribution — 0.1.0-r1

이 릴리스에 포함되는 실행 엔진은 SmartSafeHub 프로젝트의 자체 작성 CHIP-8 인터프리터(`web/chip8.mjs`)입니다. 인터프리터, UI, 내장 데모에는 **GPL-3.0-or-later** 라이선스를 적용합니다. 법적 검토가 필요한 외부 compiled JS/WASM 파일은 모두 삭제했습니다.

| Component | License | Included? |
|---|---|---|
| SmartSafeHub CHIP-8 emulator + original demo | GPL-3.0-or-later | Yes (source) |
| [EmulatorJS](https://github.com/EmulatorJS/EmulatorJS) | GPL-3.0 | **No** |
| FCEUmm / Gambatte / mGBA / PCSX ReARMed | individually licensed | **No** |
| Third-party ROMs / BIOS | copyright of respective owners | **No** |

**EmulatorJS credits:** 이전 프로토타입은 EmulatorJS 4.2.3을 사용했습니다. 현재 버전은 EmulatorJS 기반 바이너리와 코어를 포함하지 않으며 EmulatorJS 제작·후원·공식 앱이 아닙니다. 추후 사용할 경우 그 버전에 대응하는 소스, 패치, 라이선스와 재배포 고지를 검증한 후 별도 업데이트합니다.

The distribution contains only original application JavaScript/CSS/HTML and license documentation, not third-party compiled code. This declaration is based on the included file inventory; a legal review of future dependencies is still required when adding them.
