# Retro Arcade 공개 / APK 배포 확인

- [ ] 포함된 mGBA 0.10.5 JS/WASM과 매니페스트의 빌드 출처·해시 확인 (브리지 또는 코어 변경 시에만 재빌드)
- [ ] `web/mgba/mgba.js`, `mgba.wasm`, `manifest.json` 세 파일 커밋
- [ ] 개발 PC에서 `python3 scripts/vendor_jsnes.py` 한 번 실행하고 `web/vendor/jsnes/` 모듈·manifest 커밋 (OpenWrt 빌드 시 다운로드 금지)
- [ ] Gearsystem 3.9.21과 BlastEm 625fa5a85505 검증된 소스에서 각각 JS/WASM 빌드하고 해당 `manifest.json` 및 라이선스 원문 함께 커밋
- [ ] `web/gearsystem/`, `web/blastem/` 모듈을 각각 실제 Sega 홈브루 ROM으로 열어 프레임·오디오·키와 배터리 저장 확인
- [ ] 저사양 모바일 기기 및 LAN HTTP에서 메모리·오디오·프레임 테스트, GPL/MIT 및 기타 실제 링크된 의존성 라이선스 감사
- [ ] `python3 scripts/release_audit.py --release` 통과 (JSNES 소스 미포함·변조 시 실패)
- [ ] Python 및 JavaScript 단위 테스트 모두 통과
- [ ] `python3 scripts/cache_bust.py --check` 통과 (배포 JS/CSS 해시 최신 여부)
- [ ] `python3 tests/browser_e2e.py -v` Chromium HTTP/모바일 E2E 통과
- [ ] 저장소 차단·저장 실패·복원 실패 경고 및 종료 확인 동작 테스트
- [ ] CHIP-8 내장 데모 브라우저 실행 확인
- [ ] GB / GBC / GBA 실제 ROM별 화면·키보드·터치·배터리 저장·재실행 확인
- [ ] NES/Famicom `.nes` 실 ROM과 주요 Mapper별 화면·입력·배터리 저장·일시정지 확인
- [ ] NES 오디오 켜기 버튼으로 LAN HTTP, 모바일 브라우저에서 소리·일시정지·종료 확인
- [ ] 기존 브라우저 저장 데이터 유지 및 이전 에뮬레이터 세이브 호환성 제한 안내
- [ ] LAN HTTP 환경, CSP 및 IndexedDB 브라우저 호환성 확인
- [ ] 지원 모델 4종에서 APK 설치·삭제·업데이트·용량 검사
- [ ] GPLv3 수정 APK 설치에 필요한 정보 제공 여부 검토
- [ ] mGBA MPL-2.0 대응 소스 및 LICENSE 고지 검증
- [ ] JSNES Apache-2.0 원문 및 upstream 버전 고지 확인
- [ ] ROM 및 상용 BIOS 미포함 확인
- [ ] CHIP-8/mGBA 오디오 미지원, NES/Sega 오디오 활성화 방법과 호환성 안내 확인

- [ ] CHIP-8 내장 **패들 랠리**에서 W/S(터치 5/8) 이동, 공 반사, 점수 변경 확인
