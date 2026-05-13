# 서울 데이터 기반 아이체험 큐레이터

부모가 “이번 주말 우리 아이 어디 갈까?”를 빠르게 판단하도록 돕는 서울 공공데이터 기반 인터랙티브 시각화입니다. 예약 서비스가 아니며, 실제 회차별 잔여석과 신청 가능 여부는 공식 예약/출처 링크에서 최종 확인해야 합니다.

## 현재 방향

첫 화면은 데이터 목록이 아니라 큐레이션 화면입니다. 선택한 날짜, 아이 나이, 출발 자치구, 비용, 실내/실외, 관심분야를 기준으로 부적합 후보를 먼저 걸러내고, 오늘의 추천 1곳과 추천 후보 5곳, 막혔을 때 갈 만한 대체 후보를 보여줍니다.

청년·성인·반려동물·조직 모집·평일 전용 프로그램은 부모용 추천에서 먼저 제외합니다. “제한없음” 또는 0~99세 데이터도 자동 적합으로 보지 않고, 아동·가족 맥락이 확인될 때만 추천 후보로 사용합니다.

오늘의 추천은 선택한 날짜를 최우선으로 봅니다. 선택 날짜와 정확히 맞는 후보가 있으면 그 안에서만 1순위를 고르고, 없을 때만 같은 주말 후보를 비교합니다. ±7일 또는 30일 이내 후보는 “조건을 넓히면 늘어나는 후보”에서 따로 안내합니다.

## 화면 흐름

1. 부모용 홈: 오늘의 결론, 오늘의 추천 1곳, 추천 후보 5곳, 대체 후보, 조건을 넓히면 늘어나는 후보, 지금은 추천하지 않은 이유
2. 추천 탐색: 지도와 주요 후보 20곳 리스트, 오늘의 추천 순/가까운 순/신청 부담 낮은 순/무료·저비용 우선/실내 우선 정렬
3. 후보 비교: 오늘의 추천과 신청 부담 낮은 대체 후보를 기본 비교
4. 상세 확인: 이용규칙 카드, 추천 이유와 주의점, 주변/유사 대체안
5. 서울시 관점: 지역별 기회, 선택지 부족 주말, 대체 후보 부족, 이용장벽 분석

## 실행 방법

```powershell
pip install -r requirements.txt
python -m src.build_all
streamlit run app.py --server.port 8501
```

API 키를 사용할 경우 프로젝트 루트에 `.env`를 만들고 다음 값을 넣습니다. 실제 키 값은 문서나 로그에 남기지 않습니다.

```text
SEOUL_OPENAPI_KEY=YOUR_SEOUL_OPENAPI_KEY_HERE
NEIS_API_KEY=YOUR_NEIS_API_KEY_HERE
SCHOOLINFO_API_KEY=YOUR_SCHOOLINFO_API_KEY_HERE
```

API 키가 없거나 호출이 실패하면 앱은 샘플 데이터만 사용하며, 샘플 모드 경고를 화면에 표시합니다. API 데이터와 샘플 데이터는 섞지 않습니다.

실제 API 연결 진단과 재수집은 다음 명령으로 수행합니다.

```powershell
python tools/check_seoul_api_connection.py
python -m src.build_all --force-refresh
```

2026-05-13 기준 확인된 live 수집 결과는 공공서비스예약 2,527건, 서울문화행사 3,924건, 통합 후보 6,451건입니다. 성공한 서비스명은 `data/cache/api_service_registry.json`에 저장되며, API 키 값은 출력하거나 문서에 기록하지 않습니다.

## API 연동 구조

- `src/api/seoul_openapi.py`: 서울 열린데이터광장 공통 호출
- `src/api/public_reservation.py`: 공공서비스예약 후보 서비스 수집
- `src/api/culture_events.py`: 문화행사 수집
- `src/api/detail_page_parser.py`: 공개 상세 페이지 보조 파싱
- `src/api/cache.py`: 같은 날짜 캐시
- `src/normalize_status.py`: 예약상태 표준화
- `src/curation_rules.py`: 대상층·요일·대체 후보·예약 난이도 신호
- `src/recommend.py`: 부모용 하드필터와 큐레이션 정렬

## 구현하지 않는 기능

- 로그인
- 회원가입
- 자동예약
- 결제
- 알림
- DB 저장
- 비공개 API 또는 로그인 후 데이터 접근

## 정확성 유의사항

`접수중` 또는 `예약가능` 상태도 실제 신청 성공을 보장하지 않습니다. 회차별 잔여석, 취소/노쇼 규칙, 보호자 동반 여부, 준비물은 공식 예약/출처 링크에서 최종 확인해야 합니다. 이동시간은 실제 교통 API가 아니라 자치구 간 상대거리 기반 추정 범위입니다.

예약 난이도는 공개 데이터의 현재 상태와 일정 기준으로 만든 신호입니다. 반복 스냅샷이 충분히 쌓이기 전에는 과거 마감 패턴으로 표현하지 않습니다.

## 주요 문서

- `docs/recommendation_failure_audit.md`: 부적합 추천 통과 원인 감사
- `docs/target_filter_rules.md`: 아동·가족 대상 하드필터 규칙
- `docs/weekend_filter_rules.md`: 주말·평일 전용 필터 규칙
- `docs/curation_view_spec.md`: Top 1 + Top 5 큐레이션 화면 규격
- `docs/backup_candidate_logic.md`: 대체 후보 선정 기준
- `docs/reservation_difficulty_signal.md`: 예약 난이도 신호 정의
- `docs/ux_wording_review.md`: 부모용 화면 문구 점검
- `docs/api_connection_report.md`: 실제 서비스명 연결 진단 보고서
- `docs/data_limitations.md`: 데이터 한계와 정확성 원칙
- `docs/validation_report.md`: 테스트 및 검증 결과
- `docs/ppt_capture_guide.md`: PPT 캡처 가이드

본 결과물은 서울시 OpenAPI와 공개 출처 링크를 기반으로 후보를 탐색하는 시각화 도구입니다. 실제 회차별 잔여석과 최종 신청 가능 여부는 공식 예약/출처 페이지에서 확인해야 합니다.
