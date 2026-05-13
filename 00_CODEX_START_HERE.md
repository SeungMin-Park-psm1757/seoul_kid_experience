# Codex에 그대로 붙여넣을 시작 프롬프트

프로젝트명: 서울 데이터 기반 아이체험 큐레이터

당신은 이 프로젝트의 데이터 수집·정제·지표 산출·핵심 시각화 구현 담당이다.  
목표는 공모전 시각화 부문 제출용으로, “웹서비스”가 아니라 **서울 공공데이터 기반 인터랙티브 시각화 결과물**을 만드는 것이다.

## 0. 가장 중요한 원칙

- PPT를 먼저 만들지 말고, 데이터 기반 핵심 시각화를 먼저 만든다.
- 로그인, 회원가입, DB, 푸시 알림, 예약 자동화는 구현하지 않는다.
- 노쇼 발생률을 분석한다고 주장하지 않는다. 공개데이터로 방어하기 어렵기 때문이다.
- 노쇼/취소는 “이용규칙 가시성” 또는 “이용장벽” 요소로만 다룬다.
- 앱 기능보다 **지표와 시각화 결과**가 우선이다.
- 최종 발표자료는 실제 수치와 시각화 결과를 바탕으로 나중에 작성한다.

## 1. 먼저 읽을 문서

다음 문서를 순서대로 읽고, 현재 패키지의 목적을 이해하라.

1. `docs/project_brief.md`
2. `docs/data_sources_checklist.md`
3. `docs/metric_definitions.md`
4. `docs/visualization_spec.md`
5. `docs/redteam_checklist.md`
6. `docs/ppt_after_visualization_plan.md`

## 2. 1차 목표

샘플 데이터 기반으로 아래 결과가 생성되게 하라.

- `data/processed/unified_programs.csv`
- `data/processed/district_age_metrics.csv`
- `data/processed/weekly_choice_metrics.csv`
- `outputs/figures/01_empty_weekend_calendar.png`
- `outputs/figures/02_planb_tilemap.png`
- `outputs/figures/03_age_blindspot_heatmap.png`
- `outputs/figures/04_choice_planb_matrix.png`
- `outputs/figures/05_barrier_decomposition.png`
- Streamlit 앱 `app.py`

먼저 아래 명령으로 샘플 파이프라인을 실행하라.

```bash
python -m src.build_all --sample
streamlit run app.py
```

실행 오류가 있으면 수정하라.

## 3. 실제 데이터 연결 목표

실제 데이터는 `data/raw/`에 넣는다고 가정한다. 우선 아래 데이터셋을 연결 대상으로 삼아라.

필수 후보:
- 서울시 공공서비스예약 정보
- 서울시 문화행사 정보
- 서울형 키즈카페 시설현황정보
- 서울시 문화공간 정보 또는 박물관·미술관 정보
- 자치구별 아동 인구 또는 연령별 인구 통계

해야 할 일:
1. 실제 CSV/JSON 파일의 컬럼명을 확인한다.
2. `src/normalize.py`의 mapping 함수를 실제 컬럼명에 맞게 수정한다.
3. 모든 데이터를 `unified_programs.csv` 스키마로 맞춘다.
4. 결측값과 불확실한 필드는 `docs/data_audit.md`에 정리한다.
5. 실제 데이터 기반 결과를 `docs/metrics_result_summary.md`에 요약한다.
6. 생성된 시각화별 해석을 `docs/visualization_interpretation.md`에 작성한다.

## 4. 핵심 지표

반드시 아래 3개 지표를 계산하라.

1. 선택가능도 지수
   - 연령 적합성
   - 주말 이용 가능성
   - 비용 접근성
   - 공간 접근성
   - 예약/운영 상태
   - 카테고리 다양성

2. 플랜B 충분도 지수
   - 같은 자치구 대체안 수
   - 인접 자치구 대체안 수
   - 유사 카테고리 대체 가능성
   - 같은 연령대 적합성
   - 저비용/실내 대체안 여부

3. 이용장벽 지수
   - 유료 비율
   - 사전예약 의존도
   - 연령 제한 강도
   - 규칙 복잡성 또는 규칙 가시성 부족

단, 지표는 탐색적 지표임을 명확히 표기한다. 실제 정책 판단에는 추가 검증이 필요하다는 한계도 남긴다.

## 5. 핵심 시각화

반드시 아래 5개 시각화를 구현하라.

1. 빈 주말 캘린더
   - 52주 × 자치구
   - 색상: 선택가능도
   - 목적: 언제, 어디서 아이체험 선택권이 비는지 표시

2. 플랜B 충분도 지도/타일맵
   - 자치구별 플랜B 충분도
   - 목적: 1순위 체험이 어려울 때 대체안이 남는 지역과 사라지는 지역 표시

3. 연령별 블라인드 스팟
   - 4~6세 / 7~9세 / 10~12세 비교
   - 목적: 특정 연령대가 구조적으로 배제되는 지역 확인

4. 선택가능도 × 플랜B 충분도 2×2 매트릭스
   - 목적: 자치구 유형화

5. 이용장벽 분해 차트
   - 비용, 예약, 연령 제한, 규칙 가시성 요소 분해
   - 목적: “있어도 고르기 어려운” 이유 설명

## 6. 디자인 방향

- 공공기관식 촌스러운 표 나열을 피한다.
- 흔한 SaaS 대시보드 KPI 카드도 피한다.
- 지도·캘린더·매트릭스 중심의 시그니처 뷰를 먼저 보여준다.
- 카드형 추천 UI는 보조로만 둔다.
- Streamlit 기본 느낌은 CSS로 줄인다.

## 7. 최종 산출 문서

작업 후 다음 문서를 반드시 작성 또는 업데이트하라.

- `docs/data_audit.md`
- `docs/metrics_result_summary.md`
- `docs/visualization_interpretation.md`
- `docs/ppt_source_notes.md`

이 문서들은 이후 NotebookLM 또는 PPT 제작에 입력할 근거 자료가 된다.

이제 샘플 파이프라인 실행부터 시작하라.
