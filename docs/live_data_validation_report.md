# 실데이터 전환 검증 보고서

검증일: 2026-05-13

## 목적

샘플 데이터 기반 MVP를 실제 서울시 OpenAPI 기반 MVP로 전환했는지 확인한다. API 키 값은 문서, 로그, 캡처에 기록하지 않는다.

## API 연결 진단

진단 스크립트:

```text
python tools/check_seoul_api_connection.py
```

성공한 서비스명:

- 공공서비스예약: `ListPublicReservationCulture`, `ListPublicReservationEducation`, `ListPublicReservationSport`, `ListPublicReservationInstitution`
- 문화행사: `culturalEventInfo`

실패한 후보 서비스명은 `docs/api_connection_report.md`에 실패 사유와 함께 기록했다. live pipeline은 성공한 서비스명만 사용한다.

## 수집 결과

| 항목 | 값 |
|---|---:|
| 데이터 모드 | API |
| 공공서비스예약 수집 | 2,527건 |
| 문화행사 수집 | 3,924건 |
| 통합 후보 | 6,451건 |
| 연령 파싱 성공률 | 100.0% |
| 날짜 파싱 성공률 | 100.0% |
| 좌표 보유율 | 98.1% |
| 예약상태 확인 가능 비율 | 97.4% |
| 공식 링크 보유율 | 100.0% |
| 마감/종료 후보 | 4,235건 |

## 생성 파일

- `data/processed/unified_programs.csv`
- `data/processed/unified_programs_live.csv`
- `data/processed/district_age_metrics.csv`
- `data/processed/weekly_choice_metrics.csv`
- `data/processed/data_quality_summary.csv`
- `data/snapshots/api_snapshot_YYYYMMDD_HHMM/`

## 검증 결과

| 검증 항목 | 결과 | 메모 |
|---|---|---|
| API 키가 있으면 API 모드로 실행되는가 | 통과 | `data_collection_meta.json`의 `data_mode=api` |
| 실제 데이터가 1건 이상 수집되는가 | 통과 | 통합 후보 6,451건 |
| 성공 서비스명만 pipeline에 쓰는가 | 통과 | `api_service_registry.json` 기반 |
| 샘플 데이터와 API 데이터가 섞이지 않는가 | 통과 | 샘플 유사 행 0건 |
| 통합 스키마 필수 컬럼이 존재하는가 | 통과 | pytest 검증 |
| 예약상태 매핑이 작동하는가 | 통과 | pytest 검증 |
| 30일 초과 미래 후보가 기본 추천에서 제외되는가 | 통과 | pytest 검증 |
| 플랜B가 원 후보와 동일하지 않은가 | 통과 | pytest 검증 |

## 실행한 테스트

```text
python -m py_compile app.py src/api/seoul_openapi.py src/api/public_reservation.py src/api/culture_events.py src/api/cache.py src/api/config.py src/normalize_status.py src/normalize_date.py src/normalize_age.py src/normalize_location.py src/normalize_live.py src/metrics.py src/build_all.py src/recommend.py tools/check_seoul_api_connection.py
결과: 통과

python -m pytest -q
결과: 9 passed
```

## 한계

본 결과물은 서울시 OpenAPI와 공개 출처 링크를 기반으로 후보를 탐색하는 시각화 도구입니다. 실제 회차별 잔여석과 최종 신청 가능 여부는 공식 예약/출처 페이지에서 확인해야 합니다.
