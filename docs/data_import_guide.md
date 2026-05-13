# 실제 서울 데이터 교체 가이드

## 기본 흐름

1. 서울 공공데이터 원본을 `data/raw/`에 CSV 또는 JSON으로 저장한다.
2. 파일명은 데이터 출처를 알 수 있게 지정한다.
3. `python -m src.build_all`을 실행한다.
4. `data/processed/unified_programs.csv`의 필수 컬럼과 데이터 품질 패널을 확인한다.

## 통합 필수 컬럼

- `id`
- `title`
- `source`
- `category`
- `district`
- `venue`
- `age_min`
- `age_max`
- `age_label`
- `fee`
- `fee_type`
- `indoor_outdoor`
- `date_start`
- `date_end`
- `time_text`
- `status_label`
- `reservation_required`
- `rule_summary`
- `no_show_rule`
- `cancel_rule`
- `family_fit`
- `lat`
- `lng`
- `source_url`
- `data_confidence`
- `date_match_level`
- `recommendation_reason`
- `caution_note`

## 데이터셋별 매핑 가이드

### 공공서비스예약 정보

- 프로그램명: `서비스명`, `SVCNM`
- 장소: `장소`, `PLACENM`
- 자치구: `자치구`, `AREANM`
- 대상연령: `이용대상`, `USETGTINFO`
- 예약상태: `서비스상태`, `SVCSTATNM`
- 신청/운영 날짜: `RCPTBGNDT`, `RCPTENDDT`, `SVCOPNBGNDT`, `SVCOPNENDDT`
- 원문 링크: `SVCURL`

### 서울시 문화행사 정보

- 프로그램명: `행사명`, `TITLE`
- 카테고리: `분류`, `CODENAME`
- 장소: `장소`, `PLACE`
- 날짜: `STRTDATE`, `END_DATE`
- 요금: `USE_FEE`
- 원문 링크: `ORG_LINK`, `MAIN_IMG` 또는 상세 URL

### 서울형 키즈카페 시설현황정보

- 시설명: `시설명`
- 자치구: `자치구`
- 주소/좌표: 주소, 위도, 경도
- 대상연령: 운영 기준 또는 원문 안내
- 이용규칙: 회차, 보호자 동반, 예약 여부

### 서울시 문화공간/박물관·미술관 정보

- 공간명: `시설명`, `문화공간명`
- 분류: 박물관, 미술관, 문화공간
- 자치구/주소/좌표
- 운영시간과 관람료
- 상세 링크

### 자치구별 아동 인구 또는 관련 통계

- 자치구
- 연령대 또는 나이
- 아동 인구 수
- 기준연도

이 데이터는 `district_age_metrics.csv`의 인구 대비 프로그램 수와 접근성 지표 계산에 사용한다.

## 매핑 보강 위치

실제 컬럼명이 기본 후보와 다르면 `src/normalize.py`의 `normalize_generic()` 함수에서 `_coalesce()` 후보 컬럼명을 추가한다.

## 검수 체크리스트

- 프로그램명이 숫자형 더미명처럼 보이지 않는가?
- 날짜가 파싱되어 `week`가 계산되는가?
- 대상연령이 `age_min`, `age_max`로 변환되는가?
- 예약상태가 `예약 가능`, `상시 운영`, `마감임박`, `접수 예정`, `확인 필요`, `마감` 중 하나로 해석 가능한가?
- 원문 링크가 비어 있으면 카드에서 `확인 필요`로 보이는가?
- 좌표가 없을 때 지도에서 후보가 누락될 수 있음을 설명하는가?
