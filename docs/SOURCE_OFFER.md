# Source code offer — SmartSafeHub Retro Arcade 0.1.0-r2

프로젝트 자체 소스: https://github.com/Junatum/retro-arcade

- SmartSafeHub Retro Arcade UI와 CHIP-8: GPL-3.0-or-later, 본 저장소 소스
- mGBA Game Boy / Color / Advance C 코어: MPL-2.0, https://github.com/mgba-emu/mgba (공식 태그 `0.10.5`)
- 로컬 WebAssembly 연계 브리지: [`native/mgba_bridge.c`](../native/mgba_bridge.c)
- 빌드 방법: [`scripts/build_mgba.py`](../scripts/build_mgba.py), [아키텍처](ARCHITECTURE.md)
- 배포본의 정확한 upstream 커밋, Emscripten 버전, JS/WASM SHA-256: [`web/mgba/manifest.json`](../web/mgba/manifest.json)

mGBA의 MPL-2.0 소스 제공 의무 및 GPLv3 프로그램의 배포 요건을 확인하세요. 게임 ROM과 상용 BIOS는 제공하지 않습니다.
