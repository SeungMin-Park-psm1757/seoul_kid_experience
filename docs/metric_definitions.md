# 지표 정의서

이 지표들은 정책 판단을 위한 확정 통계가 아니라, 공공데이터를 바탕으로 탐색적으로 구성한 **시각화 지표**다. 실제 제출자료에는 “탐색적 지표”임을 명시하고, 데이터 한계도 함께 적는다.

## 1. 선택가능도 지수

### 정의
특정 자치구·연령대·주말 시점에서 아이가 실제로 선택할 수 있는 공공체험의 정도.

### 구성 요소
- `compatible_count_scaled`: 연령 조건에 맞고 주말 이용 가능한 프로그램 수의 정규화 값
- `per_1000_children_scaled`: 아동 1천 명당 선택 가능한 프로그램 수의 정규화 값
- `free_low_cost_share`: 무료 또는 저비용 프로그램 비율
- `indoor_share`: 실내 프로그램 비율
- `category_diversity_scaled`: 체험 카테고리 다양성
- `availability_share`: 예약 가능/운영 중 상태 비율

### 예시 산식
```text
선택가능도 = 0.30 * compatible_count_scaled
          + 0.20 * per_1000_children_scaled
          + 0.15 * free_low_cost_share
          + 0.10 * indoor_share
          + 0.15 * category_diversity_scaled
          + 0.10 * availability_share
```

## 2. 플랜B 충분도 지수

### 정의
1순위 체험이 마감·거리·연령 문제로 어려울 때, 대체 가능한 공공체험이 얼마나 남는가.

### 구성 요소
- 같은 자치구 대체안 수
- 인접 자치구 대체안 수
- 같은 연령대 적합성
- 유사 카테고리 여부
- 무료/저비용 대체 가능성
- 실내 대체 가능성

### 예시 산식
```text
플랜B 충분도 = 0.35 * local_alt_scaled
            + 0.25 * neighbor_alt_scaled
            + 0.15 * category_diversity_scaled
            + 0.15 * free_low_cost_share
            + 0.10 * indoor_share
```

## 3. 이용장벽 지수

### 정의
공공체험이 존재하더라도 실제 선택을 어렵게 만드는 장벽의 정도. 점수가 높을수록 장벽이 큼.

### 구성 요소
- `paid_share`: 유료 프로그램 비율
- `reservation_dependency`: 사전예약 의존 비율
- `age_restriction_intensity`: 연령 제한이 좁은 프로그램 비율
- `rule_complexity`: 이용규칙/취소규칙/노쇼규칙 텍스트 복잡성 또는 명시 여부

### 예시 산식
```text
이용장벽 = 0.30 * paid_share
        + 0.25 * reservation_dependency
        + 0.20 * age_restriction_intensity
        + 0.25 * rule_complexity
```

## 레드팀 주의사항

- 실시간 잔여석 지표로 과장하지 않는다.
- 노쇼 발생률은 분석하지 않는다.
- 규칙 복잡성은 “규칙 가시성/텍스트 복잡성”으로만 제시한다.
- 지표 가중치는 임시이며, 민감도 분석 또는 가중치 변경 가능성을 언급한다.
# 부모용 추천/시각화 지표 보강

## 날짜 매칭 단계

- `exact_weekend`: 선택 날짜 당일 또는 같은 주말 후보. 부모용 홈 기본 추천 최상위 노출 대상.
- `near_weekend`: 선택 날짜 기준 ±7일 후보. "이번 주말 인근 후보"로 표시.
- `month_extension`: 선택 날짜 기준 ±30일 후보. 기본 추천이 부족할 때 "확장 후보"로 분리 표시.
- `future_reference`: 30일 초과 미래 후보. 기본 추천, 비교, 플랜B 기본값에서는 제외하고 추후 예정 참고로만 사용.

## 상태 우선순위

1. 예약 가능
2. 상시 운영 또는 현장 참여 가능
3. 마감임박
4. 접수 예정
5. 확인 필요
6. 마감

## 부모용 추천 점수 구성

추천 점수는 화면에 숫자로 직접 노출하지 않고, 카드의 `추천 이유` 문장으로 설명한다.

- `status_score`: 현재 신청 또는 이용 가능성
- `date_match_score`: 이번 주말과의 날짜 근접성
- `age_fit_score`: 아이 나이와 대상연령의 적합성
- `distance_score`: 자치구 간 상대거리 기반 이동 부담
- `fee_score`: 무료 또는 저비용 여부
- `indoor_score`: 실내 또는 혼합 활동 여부
- `interest_match_score`: 관심분야 필터 일치 여부
- `rule_clarity_score`: 이용규칙/취소/노쇼 정보의 명확성
- `planb_score`: 같은 자치구, 인접 자치구, 유사 카테고리 대체안 존재 여부

## 이동시간 표현

이동시간은 실제 교통 API 기반 시간이 아니다. 앱에서는 `추정 40~50분`, `이동 난이도: 보통`, `자치구 간 상대거리 기반`으로 표현한다.

## 조건 완화 퍼널

조건 완화 퍼널은 후보 부족의 원인을 설명하기 위한 부모용·정책용 공통 시각화다.

단계는 다음과 같다.

1. 내 조건 그대로
2. 날짜 ±7일 허용
3. 인접 자치구 허용
4. 유료 포함
5. 실외 포함
6. 관심분야 전체 허용

각 단계는 후보 수와 이전 단계 대비 증가분을 보여준다.

## 부모용 큐레이션 하드필터 지표

- `child_suitability`: `eligible`, `excluded`, `review_needed`로 구분한다. 청년·성인·반려견·조직 모집은 부모용 추천에서 제외한다.
- `target_audience_norm`: `child`, `family`, `infant`, `elementary`, `teen`, `youth`, `adult`, `senior`, `pet`, `organization`, `general_public`, `unknown` 중 하나다.
- `date_weekday_match`: 선택한 날짜의 요일과 프로그램 운영 요일이 맞는지 나타낸다. 주말 선택 시 평일 전용은 제외한다.
- `reservation_friction`: `low`, `medium`, `high`, `unknown`으로 예약 부담을 나타낸다.
- `reservation_difficulty`: `easy`, `medium`, `hard`, `unknown`으로 공개 상태 기반 예약 난이도 신호를 나타낸다.
- `hard_filter_reason`: 추천에서 제외된 핵심 이유다. 부모용 홈의 “지금은 추천하지 않은 이유”에 사용한다.
