# 설치 및 수정판 이용 안내

SmartSafeHub Retro Arcade는 로컬 OpenWrt 웹서버가 정적 웹 파일을 제공하는 독립 APK입니다.

- 패키지명: `smartsafehub-app-retro-arcade`
- 웹 파일 설치 위치: `/www/retro-arcade/`
- 게임 실행 주소: `/retro-arcade/`
- WASM은 브라우저에서 로딩하며, 공유기 CPU는 에뮬레이션에 사용되지 않습니다.
- 서명과 설치는 SmartSafeHub가 사용하는 OpenWrt APK 저장소 정책에 따릅니다.

소스 수정판의 빌드 방법은 [아키텍처 및 개발 가이드](ARCHITECTURE.md), 배포된 바이너리의 정확한 출처와 재빌드 조건은 [대응 소스 안내](SOURCE_OFFER.md)에서 확인할 수 있습니다. GPLv3 프로그램을 소비자용 공유기에 제공하는 경우, 해당 장치에서 수정된 버전을 설치·실행하기 위해 필요한 서명/설치 정보의 제공 의무가 발생할 수 있습니다. **현재 이 저장소만으로는 기기별 설치 제한 또는 펌웨어 복구 절차가 실제로 검증됐다고 주장하지 않습니다.** 배포 전 [릴리스 체크리스트](RELEASE_CHECKLIST.md)에 있는 장치별 설치 검증을 완료하세요.
