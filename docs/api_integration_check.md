# API 연동 점검

## 사용 목적

이 프로젝트는 예약 대행 서비스가 아니라 부모가 공개 데이터를 바탕으로 주말 아이체험 후보를 빠르게 고르도록 돕는 인터랙티브 시각화다. 로그인, 자동예약, 결제, 알림, DB 저장은 구현하지 않는다.

## 환경변수

- 필수: `SEOUL_OPENAPI_KEY`
- 선택: `KAKAO_REST_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`
- 현재 검증 환경: `SEOUL_OPENAPI_KEY`가 없으면 샘플 fallback으로 동작한다.

## 구현 파일

- `src/api/config.py`: `.env`와 환경변수 로드
- `src/api/seoul_openapi.py`: 서울 열린데이터광장 공통 호출 클라이언트
- `src/api/public_reservation.py`: 공공서비스예약 후보 서비스명 순차 수집
- `src/api/culture_events.py`: 문화행사 정보 수집
- `src/api/cache.py`: 같은 날짜 캐시 우선 사용
- `src/api/detail_page_parser.py`: 공개 상세 페이지 best-effort 파싱

## 공공서비스예약 API

기본 호출 형식:

```text
http://openapi.seoul.go.kr:8088/{SEOUL_OPENAPI_KEY}/json/{SERVICE_NAME}/{START_INDEX}/{END_INDEX}/
```

우선 시도 서비스명:

- `ListPublicReservationCulture`
- `ListPublicReservationEducation`
- `ListPublicReservationSport`
- `ListPublicReservationDetail`
- `ListPublicReservation`
- `ListPublicReservationAll`

수집 방식:

- `1~1000`, `1001~2000` 방식으로 페이징한다.
- 전체 건수를 알 수 있으면 전체 수집, 아니면 서비스별 최대 5000건까지만 수집한다.
- 같은 날짜에는 `data/cache/public_reservation_YYYYMMDD_HHMM.json` 캐시를 우선 사용한다.
- 원천 검증을 위해 일부 필드는 `raw_` prefix로 보존한다.

## 문화행사 API

서비스명:

- `culturalEventInfo`

상태 분류:

- 홈페이지/예약 링크가 있으면 `예약/참여 링크 확인`
- 무료이며 행사기간 내 후보면 `참여 가능성 있음`
- 종료일이 지났으면 `행사종료`
- 정보가 부족하면 `확인 필요`

## 상세 페이지 파싱 범위

공공서비스예약 `SVCID`가 있으면 다음 공개 페이지 URL을 구성한다.

```text
https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id={SVCID}
```

best-effort 파싱 대상:

- 보호자 동반 여부
- 준비물
- 취소 규칙
- 노쇼/미참여 규칙
- 잔여석 또는 정원 관련 공개 문구
- 전화번호

제한:

- 로그인 요청 없음
- 비공개 내부 API 호출 없음
- 자동예약 없음
- 1초 1건 이하, 타임아웃 10초
- 실패해도 앱은 계속 동작하며 `링크 확인 필요`로 표시

## 2026-05-13 실제 API 연결 진단 결과

`tools/check_seoul_api_connection.py`로 후보 서비스명을 직접 진단했고, 결과는 `docs/api_connection_report.md`와 `data/cache/api_service_registry.json`에 저장했다. API 키 값은 출력하거나 문서에 기록하지 않는다.

성공한 공공서비스예약 서비스명:

- `ListPublicReservationCulture`
- `ListPublicReservationEducation`
- `ListPublicReservationSport`
- `ListPublicReservationInstitution`

성공한 문화행사 서비스명:

- `culturalEventInfo`

실패한 후보 서비스명은 보고서에 실패 사유를 기록했고, live pipeline에서는 성공한 서비스명만 사용한다.

## 현재 수집 결과

- 데이터 모드: API
- 공공서비스예약 수집: 2,527건
- 문화행사 수집: 3,924건
- 통합 후보: 6,451건
- 출력 파일: `data/processed/unified_programs.csv`, `data/processed/unified_programs_live.csv`
- 품질 요약: `data/processed/data_quality_summary.csv`
- API 스냅샷: `data/snapshots/api_snapshot_YYYYMMDD_HHMM/`

본 결과물은 서울시 OpenAPI와 공개 출처 링크를 기반으로 후보를 탐색하는 시각화 도구입니다. 실제 회차별 잔여석과 최종 신청 가능 여부는 공식 예약/출처 페이지에서 확인해야 합니다.
