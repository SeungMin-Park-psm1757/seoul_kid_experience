# 추천 실패 감사: 실데이터 전환 후 부적합 후보 노출 원인

작성일: 2026-05-13

## 감사 목적

서울시 OpenAPI live 데이터 전환 후 부모용 추천 화면에 청년·성인·반려견·평일 전용 프로그램이 섞일 수 있는 원인을 확인했다. 이 문서는 수정 전 원인을 남기고, 이후 하드필터와 큐레이션 뷰 개선의 기준으로 사용한다.

## 확인된 문제

1. 대상연령이 `제한없음` 또는 파싱 실패일 때 `0~99세`로 처리되어 7세 아이 조건을 통과할 수 있었다.
2. `청년`, `성인`, `자녀는 동석불가`, `반려견` 같은 대상층 문구가 추천 점수에서 별도 배제 조건으로 쓰이지 않았다.
3. 제목이나 시간 문구에 `평일`, `월~금`, `수요일` 등이 있어도 주말 검색에서 절대 제외되지 않았다.
4. 실데이터 카테고리 정렬이 `강당`, `강의실`, `골프장`처럼 부모용 추천과 먼 항목부터 잡히면서 기본 관심분야가 왜곡될 수 있었다.
5. 첫 화면이 “전체 후보 수”를 강조해 큐레이션이 아니라 목록 탐색처럼 느껴질 수 있었다.
6. 대체 후보가 “진짜 막혔을 때 갈 만한 곳”이 아니라 같은 조건을 느슨하게 만족하는 목록처럼 작동했다.

## 기술적 원인

기존 `src/recommend.py`는 `age_fit`, `date_match_level`, `available_now`를 계산했지만 대상층과 요일을 별도 하드필터로 분리하지 않았다. 특히 `age_min=0`, `age_max=99`인 행은 실제 대상 문맥과 무관하게 넓은 연령 적합 후보로 취급될 수 있었다.

또한 `add_recommendation_features()` 내부에서 모든 행마다 `plan_b_candidates()`를 다시 호출해 실데이터 6천 건 이상에서 성능 병목이 생겼다. 이는 추천 품질 문제와 별개로 부모 화면 응답성을 떨어뜨릴 수 있는 구조였다.

## 수정 방향

- 대상층 필드: `target_audience_raw`, `target_audience_norm`, `target_audience_confidence`, `child_suitability`, `child_suitability_reason`, `hard_filter_reason`
- 요일 필드: `weekday_raw`, `weekday_norm`, `is_weekend_available`, `is_weekday_only`, `date_weekday_match`, `date_filter_reason`
- 대체 후보 필드: `alternative_type`, `walk_in_likelihood`, `reservation_friction`, `backup_reason`
- 예약 난이도 필드: `reservation_difficulty`, `reservation_difficulty_reason`, `difficulty_confidence`, `historical_pattern_available`

부모용 추천, 오늘의 추천, Top 5, 대체 후보에는 `child_suitability=eligible`, `date_weekday_match=True`, `is_weekday_only=False`, `reservation_status_norm`이 마감/종료가 아닌 후보만 들어가야 한다.

## 검증 질문

- 청년정책 네트워크가 7세 추천에 들어가지 않는가?
- 반려견 산책교실이 아이체험 대체 후보에 들어가지 않는가?
- 어린이 동물보호교육은 반려동물 단어가 있어도 제외되지 않는가?
- 평일 전용 프로그램은 주말 추천과 대체 후보에서 제외되는가?
- 첫 화면은 Top 1과 Top 5 중심이며 큰 후보 수가 주인공이 되지 않는가?
