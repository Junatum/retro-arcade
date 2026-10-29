# 오픈소스 및 저작권 고지

| 구성 | 저작권 / 라이선스 | 포함 |
|---|---|---|
| SmartSafeHub Retro Arcade UI, CHIP-8 | SmartSafeHub contributors, GPL-3.0-or-later | 예 |
| mGBA 0.10.5 GB/GBC/GBA 코어 | Jeffrey Pfau 및 기여자, MPL-2.0 | WASM/JS 번들 |
| JSNES 2.1.0 NES/Famicom 에뮬레이터 | Ben Firshman 및 JSNES 기여자, Apache-2.0 | 검증된 ES 모듈 소스 |
| Gearsystem Game Gear / Master System / SG-1000 | Nacho Sanchez 및 기여자, GPL-3.0 | JS/WASM 및 매니페스트 포함 |
| BlastEm Mega Drive / Genesis | Michael Pavone 및 기여자, GPL-3.0-or-later | `-Oz` 빌드 JS/WASM 및 매니페스트 포함 |
| MAME 0.289 (두 선택 소스 드라이버) | MAMEDev 및 기여자, GPL-2.0-or-later; 소스별 BSD-3-Clause 등 | **`-Oz` 로컬 빌드 JS/WASM·매니페스트 포함** |
| Libretro API 헤더 | Libretro 프로젝트, MIT | 대응 소스에서 빌드 시 사용 |
| EmulatorJS 및 기타 코어 | 원저작자 | 아니요 |
| 게임 ROM / 상용 BIOS | 각 저작권자 | 아니요 |

mGBA 공식 출처: https://github.com/mgba-emu/mgba (`0.10.5`, 정확한 커밋은 `web/mgba/manifest.json` 참조).

mGBA의 MPL-2.0 라이선스 전문은 `LICENSES/mGBA.txt`에 포함됩니다. 브라우저 연동을 위한 별도 브리지 `native/mgba_bridge.c`는 GPL-3.0-or-later입니다. 빌드 스크립트 `scripts/build_mgba.py`로 정적 라이브러리와 브리지를 연결합니다. 실제 바이너리 배포 시 정확한 소스 커밋, 구성 옵션, 대응 소스 및 수정 사항을 이용할 수 있도록 유지해야 합니다. ROM 및 상용 BIOS 파일은 포함하지 않습니다.

JSNES 공식 출처: https://github.com/bfirsh/jsnes (`2.1.0`). Apache-2.0 원문은 `LICENSES/JSNES.txt`에서 확인할 수 있습니다. 브라우저 오프라인 배포용으로 원본 JS 모듈만 벤더링하며 무결성 정보는 `web/vendor/jsnes/manifest.json`을 참조합니다.

libretro API header: MIT — 원문 `LICENSES/Libretro.txt`에 포함.

Gearsystem: https://github.com/drhelius/Gearsystem, `3.9.21` 태그·`d4a86dfa0a6493020d64af6816ecc35461407c67`. BlastEm: https://www.retrodev.com/repos/blastem, `v1.0.0` 직후 Libretro 수정 변경집합 `625fa5a85505`. 두 코어는 Emscripten으로 로컬 빌드한 JS/WASM이 **이미 포함**되어 있으며, 해시와 빌드 설정은 각각의 `manifest.json`에서 확인합니다. BlastEm의 데스크톱 전용 디버그·오실로스코프 호출은 `native/blastem_headless.h`에서 브라우저용으로 처리합니다. GPLv3 라이선스 전문은 `LICENSES/Gearsystem.txt`, `LICENSES/BlastEm.txt`로 제공합니다. Libretro 헤더의 MIT 고지와 정확한 대응 소스·빌드 파일도 배포 시 유지해야 합니다. [소스 제공 안내](SOURCE_OFFER.md)는 출처·재현 절차를 설명하며, APK 배포자의 실제 소스 제공 의무를 대신하지 않습니다.

MAME: https://github.com/mamedev/mame, 고정 태그 `mame0289`. 전체 프로젝트 GPL-2.0-or-later, 일부 개별 파일은 BSD-3-Clause 등 별도 라이선스. `LICENSES/MAME-GPL2.txt`는 GPLv2 원문이며 소스 파일별 고지 전체를 대체하지 않습니다. MAME 이름·로고 상표 사용 허가는 별도입니다. 완성된 MAME JS/WASM의 구체적 소스는 로컬 빌드 뒤 `web/mame/manifest.json`에서 확인합니다. 현재 배포 소스에는 `web/mame/mame.js` 및 `mame.wasm`과 검증 매니페스트가 포함되어 있으며, MAME 0.289의 선택 드라이버 빌드 결과입니다. 빌드 리비전과 옵션은 매니페스트에 기록됩니다. `LICENSES/MAME-GPL2.txt`는 MAME에 포함된 모든 BSD 등 개별 파일의 라이선스 고지를 대체하지 않습니다. 배포자는 해당 버전의 전체 대응 소스, 개별 저작권 고지와 라이선스, 빌드 절차를 확인하고 실제로 제공해야 합니다.
