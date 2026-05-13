# PPT용 이미지 및 캡처 가이드

## 자동 생성 PNG

현재 파이프라인 또는 앱 실행 중 다음 PNG가 생성된다.

- `outputs/figures/01_empty_weekend_calendar.png`
- `outputs/figures/02_planb_tilemap.png`
- `outputs/figures/03_age_blindspot_heatmap.png`
- `outputs/figures/04_choice_planb_matrix.png`
- `outputs/figures/05_barrier_decomposition.png`
- `outputs/figures/06_condition_relaxation_funnel.png`

## UI 캡처 권장 파일명

Streamlit UI 자체는 카드와 입력 컨트롤이 포함되어 있어 정적 export보다 브라우저 캡처가 안정적이다. PPT용으로 다음 화면을 캡처한다.

- `outputs/figures/01_parent_home_summary.png`
- `outputs/figures/02_recommendation_cards.png`
- `outputs/figures/03_explore_map_list.png`
- `outputs/figures/04_compare_candidates.png`
- `outputs/figures/05_detail_backup_candidates.png`
- `outputs/figures/10_policy_summary.png`

## 캡처 절차

1. `streamlit run app.py`로 앱을 실행한다.
2. 브라우저 폭을 1366px 이상으로 맞춘다.
3. 부모용 홈에서 오늘의 추천 1곳, 오늘의 Top 5 일부, 대체 후보가 보이도록 캡처한다.
4. 추천 탐색 탭에서 지도와 리스트가 같이 보이도록 캡처한다.
5. 후보 비교 탭에서 자동 코멘트와 비교표를 캡처한다.
6. 상세 + 대체 후보 탭에서 이용규칙 카드와 대체안 일부를 캡처한다.
7. 서울시 관점 탭에서 요약 인사이트 3개와 대표 차트를 캡처한다.

## PPT 메시지 연결

- 부모 화면: "이번 주말 후보를 30초 안에 좁히는 화면"
- 조건을 넓히면 늘어나는 후보: "후보가 부족한 이유와 조건 완화 효과를 설명하는 시각화"
- 서울시 관점: "지역·연령·주차 단위의 공급 격차와 대체 후보 취약성을 해석하는 화면"

## 주의 문구

PPT 하단에는 다음 문구를 포함한다.

> 본 결과물은 서울시 OpenAPI와 공개 출처 링크를 기반으로 후보를 탐색하는 시각화 도구입니다. 실제 회차별 잔여석과 최종 신청 가능 여부는 공식 예약/출처 페이지에서 확인해야 합니다.

## API 스냅샷 고정

PPT에 같은 숫자를 반복 사용하려면 `data/snapshots/api_snapshot_YYYYMMDD_HHMM/` 폴더를 기준으로 캡처한다. 스냅샷에는 `unified_programs.csv`, `data_quality_summary.csv`, `policy_metrics.csv`, `README.md`가 포함된다.

권장 캡처 순서:

1. 부모 홈 요약
2. 지금 신청 가능한 곳 카드
3. 예약이 어렵거나 마감된 후보
4. 후보 비교
5. 조건을 넓히면 늘어나는 후보
6. 정책 실행 브리프
7. 자치구별 지역 기회 분석
