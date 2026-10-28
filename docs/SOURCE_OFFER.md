# Source code offer — SmartSafeHub Retro Arcade 1.1.0-r4

프로젝트 자체 소스: https://github.com/Junatum/retro-arcade

- SmartSafeHub Retro Arcade UI와 CHIP-8: GPL-3.0-or-later, 본 저장소 소스
- mGBA Game Boy / Color / Advance C 코어: MPL-2.0, https://github.com/mgba-emu/mgba (공식 태그 `0.10.5`)
- JSNES NES/Famicom JavaScript 코어: Apache-2.0, https://github.com/bfirsh/jsnes (`2.1.0`). 저장소에 포함된 `web/vendor/jsnes/src/` 원본 코드와 `manifest.json`의 SHA-256 참조
- JSNES 취득/무결성 검증: [`scripts/vendor_jsnes.py`](../scripts/vendor_jsnes.py)
- 로컬 WebAssembly 연계 브리지: [`native/mgba_bridge.c`](../native/mgba_bridge.c)
- 빌드 방법: [`scripts/build_mgba.py`](../scripts/build_mgba.py), [아키텍처](ARCHITECTURE.md)
- 배포본의 정확한 upstream 커밋, Emscripten 버전, JS/WASM SHA-256: [`web/mgba/manifest.json`](../web/mgba/manifest.json)

mGBA의 MPL-2.0 소스 제공 의무 및 GPLv3 프로그램의 배포 요건을 확인하세요. 게임 ROM과 상용 BIOS는 제공하지 않습니다.

- Gearsystem Sega 8-bit 코어: GPL-3.0, https://github.com/drhelius/Gearsystem (`3.9.21`)
- BlastEm Sega Mega Drive 코어: GPL-3.0-or-later, https://www.retrodev.com/repos/blastem (`v1.0.0` 직후 공식 libretro 빌드 수정 변경집합 `625fa5a85505`)
- 공통 Libretro 브리지: [`native/sega_libretro_bridge.c`](../native/sega_libretro_bridge.c)
- 두 엔진의 로컬 빌드 명령: [`scripts/build_sega.py`](../scripts/build_sega.py)
- SHA-256 및 대응 upstream 커밋: `web/gearsystem/manifest.json`, `web/blastem/manifest.json` (로컬 빌드 후 생성)

BlastEm은 소스 컴파일부터 최종 WASM 링크까지 `-Oz`와 LTO를 사용합니다. 배포 시 `web/blastem/manifest.json`의 `optimization` 및 `build_script_sha256` 필드로 대응 빌드를 검증합니다.

두 엔진의 바이너리를 배포할 때는 정확한 변경집합의 소스, 빌드 스크립트, 종속 라이브러리의 고지를 함께 제공해야 합니다.
