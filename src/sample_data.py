from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from .config import AGE_GROUPS, DATA_SAMPLE, SEOUL_DISTRICTS, UNIFIED_COLUMNS
from .normalize_status import normalize_reservation_status

CATEGORIES = ["과학", "미술", "역사", "자연", "공연", "놀이", "체육", "독서"]
SOURCES = ["공공서비스예약", "서울문화포털", "서울형 키즈카페", "구립도서관", "박물관·미술관"]

PROGRAM_TEMPLATES = {
    "과학": ["어린이 과학 실험실", "생활과학 탐구교실", "로봇과 코딩 체험", "별빛 천문 관찰교실"],
    "미술": ["가족 미술 워크숍", "어린이 그림책 미술관", "창의 만들기 체험", "우리동네 색채 아틀리에"],
    "역사": ["어린이 박물관 탐험", "역사문화 탐방 프로그램", "한양도성 이야기 산책", "전통문화 체험교실"],
    "자연": ["주말 숲 체험 교실", "어린이 생태 관찰 교실", "공원 자연탐험 시간", "가족 곤충 관찰교실"],
    "공연": ["가족 공연 체험", "어린이 음악극 관람", "토요 인형극 극장", "무대 뒤 예술 체험"],
    "놀이": ["서울형 키즈카페 놀이시간", "창의 놀이랩", "가족 보드게임 체험", "움직임 놀이교실"],
    "체육": ["어린이 생활체육 교실", "가족 클라이밍 체험", "토요 뉴스포츠 교실", "공원 신체활동 프로그램"],
    "독서": ["도서관 창의 독서교실", "그림책 상상 워크숍", "어린이 작가와의 만남", "가족 책놀이 시간"],
}

VENUE_BY_SOURCE = {
    "공공서비스예약": ["공공서비스센터", "청소년문화의집", "주민문화센터"],
    "서울문화포털": ["문화예술회관", "가족문화센터", "생활문화센터"],
    "서울형 키즈카페": ["서울형 키즈카페", "공동육아 놀이공간", "아이맘센터"],
    "구립도서관": ["구립도서관", "어린이도서관", "작은도서관"],
    "박물관·미술관": ["어린이박물관", "구립미술관", "역사전시관"],
}

DISTRICT_CENTERS = {
    "종로구": (37.5735, 126.9789), "중구": (37.5638, 126.9976), "용산구": (37.5326, 126.9905),
    "성동구": (37.5633, 127.0371), "광진구": (37.5385, 127.0823), "동대문구": (37.5744, 127.0396),
    "중랑구": (37.6063, 127.0925), "성북구": (37.5894, 127.0167), "강북구": (37.6396, 127.0257),
    "도봉구": (37.6688, 127.0471), "노원구": (37.6542, 127.0568), "은평구": (37.6027, 126.9291),
    "서대문구": (37.5791, 126.9368), "마포구": (37.5663, 126.9019), "양천구": (37.5170, 126.8665),
    "강서구": (37.5509, 126.8495), "구로구": (37.4955, 126.8875), "금천구": (37.4569, 126.8955),
    "영등포구": (37.5264, 126.8962), "동작구": (37.5124, 126.9393), "관악구": (37.4784, 126.9516),
    "서초구": (37.4837, 127.0324), "강남구": (37.5172, 127.0473), "송파구": (37.5145, 127.1059),
    "강동구": (37.5301, 127.1238),
}

TIME_TEXTS = ["10:00-11:30", "10:00-12:00", "13:00-15:00", "14:00-16:00", "오전", "오후", "상시"]
AGE_PATTERNS = [(4, 6), (5, 7), (6, 9), (7, 9), (8, 12), (10, 12), (4, 12)]
STATUS_POOL = [
    "접수중", "예약가능", "상시이용", "마감임박", "접수예정", "접수마감", "예약마감", "확인 필요"
]


def _week_from_date(value: object) -> int:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return 0
    return int(ts.isocalendar().week)


def _sample_date(i: int, rng: random.Random) -> date:
    base = date(2026, 5, 2)
    offsets = [-1, 0, 1, 2, 3, 5, 7, -6, 12, 18, 24, 31, 45, 70]
    return base + timedelta(days=offsets[i % len(offsets)] + rng.choice([0, 0, 1, -1]))


def _fee_for(i: int) -> tuple[int, str]:
    if i % 5 in {0, 1, 2}:
        return 0, "무료"
    if i % 5 == 3:
        return 3000, "저비용"
    return 12000, "유료"


def generate_sample_programs(n: int = 180, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    updated = datetime.now().isoformat(timespec="seconds")

    for i in range(n):
        district = SEOUL_DISTRICTS[i % len(SEOUL_DISTRICTS)]
        category = CATEGORIES[i % len(CATEGORIES)]
        source = SOURCES[i % len(SOURCES)]
        title = rng.choice(PROGRAM_TEMPLATES[category])
        venue = f"{district} {rng.choice(VENUE_BY_SOURCE[source])}"
        age_min, age_max = AGE_PATTERNS[i % len(AGE_PATTERNS)]
        start = _sample_date(i, rng)
        end = start if i % 6 else start + timedelta(days=rng.choice([1, 2, 7]))
        fee, fee_type = _fee_for(i)
        raw_status = STATUS_POOL[i % len(STATUS_POOL)]
        if i < 18:
            district = ["마포구", "서대문구", "용산구", "영등포구", "은평구", "강서구"][i % 6]
            category = ["과학", "미술", "독서", "놀이", "공연", "자연"][i % 6]
            source = ["공공서비스예약", "구립도서관", "서울형 키즈카페"][i % 3]
            title = PROGRAM_TEMPLATES[category][i % len(PROGRAM_TEMPLATES[category])]
            venue = f"{district} {VENUE_BY_SOURCE[source][i % len(VENUE_BY_SOURCE[source])]}"
            age_min, age_max = [(6, 9), (7, 9), (5, 8)][i % 3]
            start = date(2026, 5, 2) + timedelta(days=[0, 1, -1, 3, 6, 7][i % 6])
            end = start
            fee, fee_type = [(0, "무료"), (3000, "저비용"), (0, "무료")][i % 3]
            raw_status = ["접수중", "예약가능", "상시이용", "마감임박", "접수마감", "확인 필요"][i % 6]
        status = normalize_reservation_status(raw_status)
        lat, lng = DISTRICT_CENTERS[district]
        program_id = f"SAMPLE-{i + 1:04d}"
        detail_url = f"https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id={program_id}"
        reservation_required = source in {"공공서비스예약", "서울형 키즈카페"}

        row = {
            "program_id": program_id,
            "source": source,
            "source_service": "sample_fallback",
            "title": title,
            "category": category,
            "district": district,
            "venue": venue,
            "address": f"서울특별시 {district} 샘플로 {100 + i}",
            "lat": lat + float(np_rng.normal(0, 0.006)),
            "lng": lng + float(np_rng.normal(0, 0.006)),
            "age_min": age_min,
            "age_max": age_max,
            "age_label": f"{age_min}-{age_max}세",
            "target_text": f"{age_min}-{age_max}세 어린이 및 보호자",
            "date_start": start.isoformat(),
            "date_end": end.isoformat(),
            "time_text": TIME_TEXTS[i % len(TIME_TEXTS)],
            "fee": fee,
            "fee_type": fee_type,
            "indoor_outdoor": ["실내", "실외", "혼합"][i % 3],
            "reservation_status_raw": raw_status,
            "reservation_status_norm": status.norm,
            "availability_group": status.group,
            "available_now": status.available_now,
            "is_full_or_closed": status.is_full_or_closed,
            "date_match_level": "미계산",
            "source_url": detail_url if reservation_required else "https://data.seoul.go.kr/",
            "detail_url": detail_url,
            "rule_summary": "보호자 동반 권장, 회차별 정원과 세부 규정은 공식 링크에서 확인",
            "cancel_rule": "취소 가능 기한은 프로그램별로 다르므로 공식 링크 확인 필요",
            "no_show_rule": "미참여 시 향후 신청 제한 가능성이 있으므로 공식 규정 확인 필요",
            "family_fit": "보호자 동반 권장",
            "preparation_note": "물, 간식, 활동하기 편한 복장 권장",
            "data_confidence": "샘플",
            "availability_confidence": "샘플",
            "recommendation_reason": "필터 적용 후 자동 생성",
            "caution_note": "샘플 데이터입니다. 실제 예약 가능 여부는 공식 출처에서 확인해야 합니다.",
            "last_api_update": updated,
            "id": program_id,
            "week": _week_from_date(start),
            "status": status.group,
            "status_label": status.group,
            "reservation_required": reservation_required,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df.reindex(columns=UNIFIED_COLUMNS)


def generate_child_population_sample(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for district in SEOUL_DISTRICTS:
        base = rng.integers(9000, 36000)
        for age_group in AGE_GROUPS:
            factor = {"4-6세": 0.28, "7-9세": 0.36, "10-12세": 0.36}[age_group]
            rows.append({
                "district": district,
                "age_group": age_group,
                "child_population": int(base * factor + rng.integers(-900, 900)),
            })
    return pd.DataFrame(rows)


def save_sample_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    DATA_SAMPLE.mkdir(parents=True, exist_ok=True)
    programs = generate_sample_programs()
    population = generate_child_population_sample()
    programs.to_csv(DATA_SAMPLE / "unified_programs_sample.csv", index=False, encoding="utf-8-sig")
    population.to_csv(DATA_SAMPLE / "district_child_population_sample.csv", index=False, encoding="utf-8-sig")
    return programs, population


if __name__ == "__main__":
    save_sample_data()
