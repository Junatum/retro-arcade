# 대응 소스 및 라이선스 안내 — SmartSafeHub Retro Arcade 1.1.0-r5

이 문서는 OpenWrt APK에 포함된 **HTML/JavaScript/WebAssembly 바이너리의 대응 소스 확인 방법**을 설명합니다. 실제 배포자가 원본 소스와 빌드 방법을 정확하게 제공해야 하며, 문서의 링크만 기재했다고 모든 배포 의무가 충족되는 것은 아닙니다.

## 자체 코드 및 소스 출처

- 프로젝트: https://github.com/Junatum/retro-arcade (UI·CHIP-8·연결 브리지·빌드 스크립트, `GPL-3.0-or-later`)
- 배포본과 일치하는 **릴리스 커밋 또는 고정 태그**를 기준으로 소스 전체를 제공합니다. 기본 브랜치의 최신 상태는 배포된 APK의 대응 소스가 아닐 수 있습니다.
- 포함되는 빌드 관련 파일: `native/mgba_bridge.c`, `native/sega_libretro_bridge.c`, `native/blastem_headless.h`, `scripts/build_mgba.py`, `scripts/build_sega.py`, `scripts/vendor_jsnes.py`, `Makefile` 및 관련 문서·라이선스.

## 포함된 외부 에뮬레이터

| 구성 | 적용 라이선스 | 정확한 소스·빌드 출처 |
|---|---|---|
| mGBA (GB/GBC/GBA) | MPL-2.0 | https://github.com/mgba-emu/mgba · 태그 `0.10.5`, 커밋 `26b7884bc25a5933960f3cdcd98bac1ae14d42e2` |
| JSNES (NES/Famicom) | Apache-2.0 | https://github.com/bfirsh/jsnes · npm `2.1.0`; 원본 ES 모듈은 `web/vendor/jsnes/src/`에 포함 |
| Gearsystem (Game Gear/SMS/SG-1000) | GPL-3.0 | https://github.com/drhelius/Gearsystem · 태그 `3.9.21`, 커밋 `d4a86dfa0a6493020d64af6816ecc35461407c67` |
| BlastEm (Mega Drive/Genesis) | GPL-3.0-or-later | https://www.retrodev.com/repos/blastem · Mercurial 변경집합 `625fa5a85505` (`v1.0.0` 직후 Libretro 수정) |
| Libretro API 헤더 | MIT | 위 upstream 소스에 포함된 `libretro.h`, `LICENSES/Libretro.txt` 고지 |

각 바이너리와 대응 소스의 연결은 다음 매니페스트로 확인합니다.

- `web/mgba/manifest.json`: mGBA upstream 커밋, Emscripten 버전, 브리지 해시 및 JS/WASM SHA-256.
- `web/vendor/jsnes/manifest.json`: npm SHA-512 무결성 값과 원본 JavaScript 파일별 SHA-256.
- `web/gearsystem/manifest.json`: Gearsystem upstream 리비전, 브리지·라이선스·JS/WASM 해시.
- `web/blastem/manifest.json`: BlastEm upstream 변경집합, 브리지·브라우저 전용 shim 해시, `-Oz`/`-flto`, 빌드 스크립트와 JS/WASM 해시.

정확한 JS/WASM 파일과 매니페스트는 **현재 소스에 포함되어 있습니다**. 원본 프로젝트 전체의 체크아웃은 이 저장소에 복사하지 않았으므로, 배포자는 고정 리비전의 upstream 소스가 실제로 계속 제공되도록 별도 보관하거나 배포물과 함께 내려받을 수 있도록 제공해야 합니다.

## 대응 바이너리 재빌드

개발 PC에 Git, Mercurial(`hg`), Python, Emscripten SDK를 설치합니다. 두 Sega 코어를 빌드할 때 사용한 Emscripten 버전은 각각의 `manifest.json`에 기록되어 있습니다. 빌드 스크립트는 OpenWrt에서 실행되지 않습니다.

```sh
# 프로젝트 저장소에서 실행 (빌드 당시의 동일한 릴리스 소스로 체크아웃)
git clone --branch 3.9.21 https://github.com/drhelius/Gearsystem.git /tmp/Gearsystem
hg clone https://www.retrodev.com/repos/blastem /tmp/blastem
hg --cwd /tmp/blastem update -r 625fa5a85505

python3 scripts/build_sega.py gearsystem --source /tmp/Gearsystem
python3 scripts/build_sega.py blastem --source /tmp/blastem

# mGBA 코어 또는 브리지 변경 시에만 재빌드
git clone --branch 0.10.5 https://github.com/mgba-emu/mgba.git /tmp/mgba-0.10.5
python3 scripts/build_mgba.py --source /tmp/mgba-0.10.5

# JSNES는 원본 npm 패키지 무결성 검증 후 필요한 모듈만 포함
# python3 scripts/vendor_jsnes.py

python3 scripts/cache_bust.py --update
python3 scripts/release_audit.py --release
```

BlastEm은 Emscripten 컴파일 시 `-Oz -flto`, 브리지 C 컴파일 시 `-Oz`, 최종 링크 시 `-Oz -flto`를 사용합니다. 재빌드 결과가 기존 SHA-256과 완전히 동일하지 않을 수 있으므로 빌드 환경과 원본 커밋/변경분도 함께 기록해야 합니다. 상세한 빌드 및 검증 조건은 [아키텍처](ARCHITECTURE.md)를 참조하세요.

## 실제 배포 전 확인 사항

1. **배포한 APK와 일치하는 릴리스 소스** 및 필요한 빌드 스크립트·수정 사항·라이선스 전문을 다운로드 가능하게 공개하거나 해당 배포 방식에 맞는 소스 제공 절차를 마련합니다. upstream의 이동 가능한 브랜치 링크만 사용하지 않습니다.
2. APK를 네트워크에서 제공한다면 해당 바이너리와 실질적으로 동등하게 접근할 수 있는 대응 소스 경로를 명시합니다. 소스 배포·서면 제안의 구체적 요건은 해당 GPL 조항과 판매 방식에 따라 확인해야 합니다.
3. 소비자용 공유기와 함께 판매하는 경우 수정한 GPL 프로그램을 설치·실행하기 위한 정보 제공 의무가 적용되는지 검토합니다. [설치·수정판 안내](INSTALLATION_INFO.md)를 참조하세요.
4. mGBA의 MPL-2.0 적용 파일과 JSNES의 Apache-2.0 고지·NOTICE 등 실제 포함물에 대한 의무를 확인합니다. [외부 오픈소스 고지](THIRD_PARTY.md) 및 `LICENSES/`를 참조하세요.

**게임 ROM과 상용 BIOS는 제공하지 않습니다.** 소스 제공 및 라이선스 준수의 최종 책임은 APK 배포자에게 있습니다.
