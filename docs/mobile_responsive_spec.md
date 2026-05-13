# 모바일 반응형 레이아웃 규격

작성일: 2026-05-13

## 목표

360px~430px 폭의 휴대폰 화면에서도 제목, 필터, 버튼, 카드가 잘리지 않고 한 열 흐름으로 읽히도록 구성한다. 데스크톱에서는 최대 1080px 중앙 정렬을 유지한다.

## 상단 영역

상단은 세 요소만 노출한다.

1. 작은 데이터 상태 배지
2. 질문형 제목: `이번 주말, 우리 아이 어디 갈까?`
3. 짧은 설명: `서울 공공데이터로 날짜·나이·지역·비용 조건에 맞는 아이체험을 먼저 추려봅니다.`

영문 장식 헤더, decorative badge, 중복 제목은 사용자 화면에서 제거한다.

## CSS 기준

- `.block-container`: `max-width: min(1080px, 100%)`
- safe-area: `padding-top: max(24px, env(safe-area-inset-top))`
- 제목: `line-height: 1.3`, `white-space: normal`, `overflow: visible`
- 모바일: `@media (max-width: 760px)`에서 버튼과 카드 CTA는 full-width 또는 세로 배치
- 멀티선택 칩: `flex-wrap: wrap`
- 가로 스크롤은 기본적으로 만들지 않는다.

## 필터 레이아웃

- 모바일에서는 Streamlit column이 자연스럽게 세로로 쌓이도록 둔다.
- 관심분야는 4열 grid 안에 넣지 않고 항상 전체 폭 영역으로 둔다.
- 관심분야 선택 항목이 많아도 칩이 여러 줄로 보이도록 select 내부 overflow를 완화한다.

## 버튼 규격

- 필터 하단 primary CTA: `추천 결과 보기`
- 필터 하단 secondary CTA: `조건 초기화`
- 필터 하단 설정 CTA: `이미 가본 곳 제외 설정`
- 모바일에서 Streamlit 버튼은 full-width로 표시한다.

## 카드 규격

모든 카드에는 최소 다음 CTA를 둔다.

- 공식 링크에서 확인
- 상세 보기 또는 왜 제외됐는지 보기
- 대체 후보 보기
- 이미 가본 곳으로 표시 또는 제외하기

## 검증 폭

수동 확인 권장 폭:

- 360px
- 390px
- 430px
- 768px
- 1024px
