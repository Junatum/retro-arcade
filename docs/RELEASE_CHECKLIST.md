# Retro Arcade 공개 / APK 배포 확인

- [ ] MAME 0.289의 **정확한 태그**와 pacman/galaxian 2개 드라이버만 사용했는지 확인
- [ ] `web/mame/mame.js`, `mame.wasm`, `manifest.json`을 로컬에서 빌드·포함하고 해시·라이선스를 검증
- [ ] 실제 MAME JS의 `FS_createPath`·`FS_createDataFile`을 이용한 로컬 ZIP 배치 및 브라우저 SDL 캔버스/입력/오디오 확인
- [ ] `python3 scripts/mame_registry.py --check`로 WASM 내장 기기 식별자와 브라우저 허용 목록 일치 확인
- [ ] MAME 실행 화면의 `runner.css` 로컬 로딩과 `style-src 'self'` CSP 차단 로그 확인
- [ ] 정확한 MAME 고정 리비전 및 사용된 개별 소스 파일의 BSD 등 라이선스 고지·대응 소스 제공 확인
- [ ] 라이선스/상표 검토 및 상용 게임 데이터·BIOS **미포함** 확인
- [ ] 실기에서 호환되는 로컬 테스트 파일의 실행과 브라우저 메모리·Flash 사용량 확인


- [ ] 포함된 mGBA 0.10.5 JS/WASM과 매니페스트의 빌드 출처·해시 확인 (브리지 또는 코어 변경 시에만 재빌드)
- [ ] `web/mgba/mgba.js`, `mgba.wasm`, `manifest.json` 세 파일 커밋
- [ ] 개발 PC에서 `python3 scripts/vendor_jsnes.py` 한 번 실행하고 `web/vendor/jsnes/` 모듈·manifest 커밋 (OpenWrt 빌드 시 다운로드 금지)
- [ ] 포함된 Gearsystem 3.9.21 / BlastEm 625fa5a85505 JS/WASM·매니페스트·라이선스 해시 확인 (소스·브리지·빌드 옵션 변경 시만 재빌드)
- [ ] BlastEm `-Oz -flto`가 매니페스트에 기록되고 이전 `-O2` 바이너리가 배포되지 않는지 확인
- [ ] `web/gearsystem/`, `web/blastem/` 모듈을 각각 실제 Sega 홈브루 ROM으로 열어 프레임·오디오·키와 배터리 저장 확인
- [ ] 저사양 모바일 기기 및 LAN HTTP에서 메모리·오디오·프레임 테스트, GPL/MIT 및 기타 실제 링크된 의존성 라이선스 감사
- [ ] `python3 scripts/release_audit.py --release` 통과 (JSNES 소스 미포함·변조 시 실패)
- [ ] Python 및 JavaScript 단위 테스트 모두 통과
- [ ] `python3 scripts/cache_bust.py --check` 통과 (배포 JS/CSS 해시 최신 여부)
- [ ] `python3 tests/browser_e2e.py -v` Chromium HTTP/모바일 E2E 통과
- [ ] ROM 없는 MAME 실 WASM 브라우저 스모크 검사(파일시스템·기기 목록, 외부 통신 없음) 통과. 실제 게임 영상·사운드·입력 검증은 별도로 수행
- [ ] 저장소 차단·저장 실패·복원 실패 경고 및 종료 확인 동작 테스트
- [ ] CHIP-8 내장 데모 브라우저 실행 확인
- [ ] GB / GBC / GBA 실제 ROM별 화면·키보드·터치·배터리 저장·재실행 확인
- [ ] NES/Famicom `.nes` 실 ROM과 주요 Mapper별 화면·입력·배터리 저장·일시정지 확인
- [ ] NES 및 Sega 시작 시 기본 소리 켜짐, 차단 시 재시도 버튼, 음소거·복구, LAN HTTP/모바일에서 소리·일시정지·종료 확인
- [ ] 기존 브라우저 저장 데이터 유지 및 이전 에뮬레이터 세이브 호환성 제한 안내
- [ ] LAN HTTP 환경, CSP 및 IndexedDB 브라우저 호환성 확인
- [ ] 지원 모델 4종에서 APK 설치·삭제·업데이트·용량 검사
- [ ] 배포 APK와 일치하는 고정 릴리스 소스와 Gearsystem/BlastEm upstream 스냅샷을 실제 다운로드 가능하게 제공하는지 확인
- [ ] 라이선스 고지·브리지·shim·빌드 스크립트·정확한 upstream 커밋을 대응 소스 패키지에 포함하거나 동등한 접근 경로를 제공하는지 확인
- [ ] GPLv3 소비자용 공유기에서 수정 APK 설치·실행에 필요한 정보 제공 여부 검토
- [ ] mGBA MPL-2.0 대응 소스 및 LICENSE 고지 검증
- [ ] JSNES Apache-2.0 원문 및 upstream 버전 고지 확인
- [ ] ROM 및 상용 BIOS 미포함 확인
- [ ] CHIP-8/mGBA 오디오 미지원, NES/Sega 오디오 활성화 방법과 호환성 안내 확인

- [ ] CHIP-8 내장 **패들 랠리**에서 W/S(터치 5/8) 이동, 공 반사, 점수 변경 확인
