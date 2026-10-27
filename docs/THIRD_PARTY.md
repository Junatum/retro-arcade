# 오픈소스 및 저작권 고지

| 구성 | 저작권 / 라이선스 | 포함 |
|---|---|---|
| SmartSafeHub Retro Arcade UI, CHIP-8 | SmartSafeHub contributors, GPL-3.0-or-later | 예 |
| mGBA 0.10.5 GB/GBC/GBA 코어 | Jeffrey Pfau 및 기여자, MPL-2.0 | WASM/JS 번들 |
| JSNES 2.1.0 NES/Famicom 에뮬레이터 | Ben Firshman 및 JSNES 기여자, Apache-2.0 | 검증된 ES 모듈 소스 |
| EmulatorJS 및 Libretro 기타 코어 | 원저작자 | 아니요 |
| 게임 ROM / 상용 BIOS | 각 저작권자 | 아니요 |

mGBA 공식 출처: https://github.com/mgba-emu/mgba (`0.10.5`, 정확한 커밋은 `web/mgba/manifest.json` 참조).

mGBA의 MPL-2.0 라이선스 전문은 `LICENSES/mGBA.txt`에 포함됩니다. 브라우저 연동을 위한 별도 브리지 `native/mgba_bridge.c`는 GPL-3.0-or-later입니다. 빌드 스크립트 `scripts/build_mgba.py`로 정적 라이브러리와 브리지를 연결합니다. 실제 바이너리 배포 시 정확한 소스 커밋, 구성 옵션, 대응 소스 및 수정 사항을 이용할 수 있도록 유지해야 합니다. ROM 및 상용 BIOS 파일은 포함하지 않습니다.

JSNES 공식 출처: https://github.com/bfirsh/jsnes (`2.1.0`). Apache-2.0 원문은 `LICENSES/JSNES.txt`에서 확인할 수 있습니다. 브라우저 오프라인 배포용으로 원본 JS 모듈만 벤더링하며 무결성 정보는 `web/vendor/jsnes/manifest.json`을 참조합니다.
