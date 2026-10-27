# Retro Arcade 0.1.0-r5 공개 / APK 배포 확인

- [ ] 포함된 mGBA 0.10.5 JS/WASM과 매니페스트의 빌드 출처·해시 확인 (브리지 또는 코어 변경 시에만 재빌드)
- [ ] `web/mgba/mgba.js`, `mgba.wasm`, `manifest.json` 세 파일 커밋
- [ ] 개발 PC에서 `python3 scripts/vendor_jsnes.py` 한 번 실행하고 `web/vendor/jsnes/` 모듈·manifest 커밋 (OpenWrt 빌드 시 다운로드 금지)
- [ ] `python3 scripts/release_audit.py --release` 통과 (JSNES 소스 미포함·변조 시 실패)
- [ ] Python 및 JavaScript 단위 테스트 모두 통과
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
- [ ] CHIP-8/mGBA 오디오 미지원, NES 오디오 활성화 방법과 호환성 안내 확인

- [ ] CHIP-8 내장 **패들 랠리**에서 W/S(터치 5/8) 이동, 공 반사, 점수 변경 확인
