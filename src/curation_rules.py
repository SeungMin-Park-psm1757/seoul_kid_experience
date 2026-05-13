from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd

EXCLUDE_AUDIENCE_KEYWORDS = {
    "youth": ["청년", "대학생", "취업", "창업", "면접", "서포터즈", "모니터링단"],
    "adult": ["성인", "직장인", "중장년", "강사", "활동가", "자원봉사", "교육생 모집"],
    "senior": ["어르신", "시니어", "노인", "노약자"],
    "pet": ["반려견", "반려동물", "강아지", "펫", "산책교실"],
    "organization": ["위원", "위원회", "네트워크", "정책참여", "모집"],
}

CHILD_CONTEXT_KEYWORDS = [
    "어린이", "아이", "아동", "초등", "초등학생", "유아", "가족", "부모", "보호자",
    "키즈", "동물보호교육", "체험", "박물관", "도서관", "놀이", "생태", "과학",
]

INFANT_KEYWORDS = ["유아", "영유아", "만3세", "만4세", "만5세", "만6세"]
ELEMENTARY_KEYWORDS = ["초등", "초등학생", "어린이"]
TEEN_KEYWORDS = ["청소년", "중학생", "고등학생"]
GENERAL_KEYWORDS = ["제한없음", "누구나", "전체", "일반"]

WEEKEND_KEYWORDS = ["토", "토요일", "일", "일요일", "토,일", "주말", "공휴일", "상시", "연중", "매일"]
WEEKDAY_ONLY_KEYWORDS = ["평일", "평일주간", "평일야간", "월~금", "월-금", "월요일", "화요일", "수요일", "목요일", "금요일", "주중"]

LOW_FRICTION_KEYWORDS = ["상시", "현장", "자유이용", "자유관람", "예약 불필요", "예약불필요", "연중", "매일"]
HARD_DIFFICULTY_KEYWORDS = ["마감임박", "접수마감", "예약마감", "정원마감", "잔여석 부족", "조기마감", "선착순", "대기", "소수정원"]


@dataclass(frozen=True)
class TargetClassification:
    raw: str
    norm: str
    confidence: str
    suitability: str
    reason: str
    hard_filter_reason: str


def compact_text(*values: object) -> str:
    return " ".join(str(value or "") for value in values if pd.notna(value)).strip()


def has_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def has_child_context(text: str) -> bool:
    return has_any(text, CHILD_CONTEXT_KEYWORDS)


def normalize_target_audience(title: object = "", target_text: object = "", category: object = "", venue: object = "", description: object = "", age_min: int | float | None = None, age_max: int | float | None = None) -> TargetClassification:
    raw = compact_text(title, target_text, category, venue, description)
    child_context = has_child_context(raw)
    explicit_child_context = has_any(raw, ["어린이", "아동", "초등", "초등학생", "유아", "가족", "키즈"])

    for candidate, keywords in EXCLUDE_AUDIENCE_KEYWORDS.items():
        if has_any(raw, keywords) and not (candidate == "pet" and explicit_child_context and "동물보호교육" in raw):
            return TargetClassification(raw, candidate, "high", "excluded", f"{candidate} 대상 문구가 있어 아이 추천에서 제외", f"대상층 불일치: {candidate}")

    # Child-context terms override pet words for cases like 어린이 동물보호교육.
    if child_context and ("동물보호교육" in raw or has_any(raw, ELEMENTARY_KEYWORDS + INFANT_KEYWORDS)):
        if has_any(raw, ELEMENTARY_KEYWORDS):
            norm = "elementary"
        elif has_any(raw, INFANT_KEYWORDS):
            norm = "infant"
        else:
            norm = "child"
    else:
        norm = ""
        if has_any(raw, INFANT_KEYWORDS):
            norm = "infant"
        elif has_any(raw, ELEMENTARY_KEYWORDS):
            norm = "elementary"
        elif "가족" in raw or "부모" in raw or "보호자" in raw:
            norm = "family"
        elif has_any(raw, TEEN_KEYWORDS):
            norm = "teen"
        elif has_any(raw, GENERAL_KEYWORDS):
            norm = "general_public"
        elif child_context:
            norm = "child"
        else:
            norm = "unknown"

    broad_age = False
    try:
        broad_age = int(age_min or 0) <= 0 and int(age_max or 99) >= 90
    except (TypeError, ValueError):
        broad_age = True

    if norm in {"youth", "adult", "senior", "pet", "organization", "teen"}:
        return TargetClassification(raw, norm, "high", "excluded", f"{norm} 대상 문구가 있어 아이 추천에서 제외", f"대상층 불일치: {norm}")
    if norm in {"child", "family", "elementary"}:
        return TargetClassification(raw, norm, "high", "eligible", "아동/가족/초등 맥락", "")
    if norm == "infant":
        return TargetClassification(raw, norm, "medium", "eligible", "유아 대상이며 나이 조건 확인 필요", "")
    if norm == "general_public" and child_context:
        return TargetClassification(raw, norm, "medium", "eligible", "제한없음이지만 아동/가족 체험 맥락", "")
    if norm == "unknown" and child_context and not broad_age:
        return TargetClassification(raw, "child", "medium", "eligible", "아동/가족 체험 맥락", "")
    if broad_age:
        return TargetClassification(raw, norm, "low", "review_needed", "제한없음 또는 0~99세라 아동 맥락 확인 필요", "대상층 확인 필요")
    return TargetClassification(raw, norm, "low", "review_needed", "아동 대상 여부가 불명확", "대상층 확인 필요")


def classify_weekday(title: object = "", date_text: object = "", time_text: object = "", description: object = "", target_text: object = "", selected_day: date | None = None) -> dict[str, object]:
    raw = compact_text(title, date_text, time_text, description, target_text)
    is_weekday_only = has_any(raw, WEEKDAY_ONLY_KEYWORDS)
    is_weekend_available = has_any(raw, WEEKEND_KEYWORDS)
    if "상시" in raw or "연중" in raw or "매일" in raw:
        is_weekday_only = False
        is_weekend_available = True
    weekday_norm = "unknown"
    if is_weekday_only:
        weekday_norm = "weekday_only"
    elif is_weekend_available:
        weekday_norm = "weekend_or_always"

    selected_is_weekend = selected_day is None or pd.Timestamp(selected_day).weekday() >= 5
    if selected_is_weekend:
        if is_weekday_only:
            return {
                "weekday_raw": raw,
                "weekday_norm": weekday_norm,
                "is_weekend_available": False,
                "is_weekday_only": True,
                "date_weekday_match": False,
                "date_filter_reason": "선택한 날짜가 주말이라 평일 전용 프로그램은 제외했습니다.",
            }
        if is_weekend_available:
            return {
                "weekday_raw": raw,
                "weekday_norm": weekday_norm,
                "is_weekend_available": True,
                "is_weekday_only": False,
                "date_weekday_match": True,
                "date_filter_reason": "",
            }
        # Date ranges that include the selected weekend can be recommended even
        # when the API does not expose explicit weekday words.
        date_tokens = re.findall(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", str(date_text))
        start_ts = pd.to_datetime(date_tokens[0] if date_tokens else None, errors="coerce")
        end_ts = pd.to_datetime(date_tokens[-1] if date_tokens else None, errors="coerce")
        if selected_day is not None and pd.notna(start_ts):
            if pd.isna(end_ts):
                end_ts = start_ts
            selected_ts = pd.Timestamp(selected_day).normalize()
            if selected_ts.weekday() <= 4:
                weekend_start = selected_ts + pd.Timedelta(days=5 - selected_ts.weekday())
            else:
                weekend_start = selected_ts - pd.Timedelta(days=selected_ts.weekday() - 5)
            weekend_end = weekend_start + pd.Timedelta(days=1)
            if start_ts.normalize() <= selected_ts <= end_ts.normalize() or (start_ts.normalize() <= weekend_end and end_ts.normalize() >= weekend_start):
                return {
                    "weekday_raw": raw,
                    "weekday_norm": "date_range_includes_selected_day",
                    "is_weekend_available": True,
                    "is_weekday_only": False,
                    "date_weekday_match": True,
                    "date_filter_reason": "",
                }
        return {
            "weekday_raw": raw,
            "weekday_norm": "unknown",
            "is_weekend_available": False,
            "is_weekday_only": False,
            "date_weekday_match": False,
            "date_filter_reason": "요일 정보가 불명확해 공식 링크에서 최종 확인이 필요합니다.",
        }

    return {
        "weekday_raw": raw,
        "weekday_norm": weekday_norm,
        "is_weekend_available": bool(is_weekend_available),
        "is_weekday_only": bool(is_weekday_only),
        "date_weekday_match": not is_weekday_only or not selected_is_weekend,
        "date_filter_reason": "",
    }


def classify_reservation_friction(row: pd.Series) -> dict[str, object]:
    text = compact_text(row.get("title"), row.get("reservation_status_raw"), row.get("availability_group"), row.get("category"), row.get("rule_summary"))
    norm = str(row.get("reservation_status_norm", "unknown"))
    category = str(row.get("category", ""))

    if norm in {"full", "closed", "ended"} or has_any(text, HARD_DIFFICULTY_KEYWORDS):
        friction = "high"
        difficulty = "hard"
        reason = "마감 또는 정원 위험 신호가 있습니다."
    elif norm == "closing_soon":
        friction = "high"
        difficulty = "hard"
        reason = "마감 임박 상태입니다."
    elif norm == "always_available" or has_any(text, LOW_FRICTION_KEYWORDS):
        friction = "low"
        difficulty = "easy"
        reason = "공식 링크 확인 후 이용 여부를 판단하기 쉬운 후보입니다."
    elif row.get("source") == "서울문화행사" or category in {"전시/미술", "전시/관람", "문화행사", "공원탐방", "산림여가"}:
        friction = "low"
        difficulty = "easy"
        reason = "문화행사 또는 공간형 후보라 신청 절차가 비교적 단순한 대안입니다."
    elif norm in {"available", "soon_open"}:
        friction = "medium"
        difficulty = "medium"
        reason = "공식 링크에서 회차와 신청 가능 여부 확인이 필요합니다."
    else:
        friction = "unknown"
        difficulty = "unknown"
        reason = "상태 정보가 불명확합니다."

    if norm == "always_available" or has_any(text, LOW_FRICTION_KEYWORDS):
        alt_type = "walk_in_or_always"
        walk_in = "high"
    elif row.get("source") == "서울문화행사":
        alt_type = "cultural_event"
        walk_in = "medium"
    elif category in {"전시/미술", "전시/관람", "공원탐방", "산림여가"}:
        alt_type = "public_space_or_facility"
        walk_in = "medium"
    elif norm == "available":
        alt_type = "same_day_reservation"
        walk_in = "low"
    else:
        alt_type = "fallback_check_needed"
        walk_in = "unknown"

    return {
        "alternative_type": alt_type,
        "walk_in_likelihood": walk_in,
        "reservation_friction": friction,
        "backup_reason": reason,
        "reservation_difficulty": difficulty,
        "reservation_difficulty_reason": reason,
        "difficulty_confidence": "공개 상태 기준" if difficulty != "unknown" else "확인 필요",
        "historical_pattern_available": False,
    }


def enrich_curation_fields(df: pd.DataFrame, selected_day: date | None = None) -> pd.DataFrame:
    out = df.copy()
    for column, default in {
        "target_audience_raw": "",
        "target_audience_norm": "unknown",
        "target_audience_confidence": "low",
        "child_suitability": "review_needed",
        "child_suitability_reason": "아동 대상 여부 확인 필요",
        "hard_filter_reason": "",
        "weekday_raw": "",
        "weekday_norm": "unknown",
        "is_weekend_available": False,
        "is_weekday_only": False,
        "date_weekday_match": False,
        "date_filter_reason": "",
        "alternative_type": "fallback_check_needed",
        "walk_in_likelihood": "unknown",
        "reservation_friction": "unknown",
        "backup_reason": "공식 링크 확인 필요",
        "reservation_difficulty": "unknown",
        "reservation_difficulty_reason": "공식 링크 확인 필요",
        "difficulty_confidence": "확인 필요",
        "historical_pattern_available": False,
    }.items():
        if column not in out.columns:
            out[column] = default

    for idx, row in out.iterrows():
        target = normalize_target_audience(
            row.get("title", ""),
            row.get("target_text", ""),
            row.get("category", ""),
            row.get("venue", ""),
            row.get("rule_summary", ""),
            row.get("age_min", 0),
            row.get("age_max", 99),
        )
        out.at[idx, "target_audience_raw"] = target.raw
        out.at[idx, "target_audience_norm"] = target.norm
        out.at[idx, "target_audience_confidence"] = target.confidence
        out.at[idx, "child_suitability"] = target.suitability
        out.at[idx, "child_suitability_reason"] = target.reason
        out.at[idx, "hard_filter_reason"] = target.hard_filter_reason

        weekday = classify_weekday(
            row.get("title", ""),
            compact_text(row.get("date_start", ""), row.get("date_end", "")),
            row.get("time_text", ""),
            row.get("rule_summary", ""),
            row.get("target_text", ""),
            selected_day,
        )
        for key, value in weekday.items():
            out.at[idx, key] = value

        friction = classify_reservation_friction(row)
        for key, value in friction.items():
            out.at[idx, key] = value

    return out


def is_parent_eligible(row: pd.Series) -> bool:
    return (
        row.get("child_suitability") == "eligible"
        and bool(row.get("date_weekday_match", False))
        and not bool(row.get("is_weekday_only", False))
        and str(row.get("reservation_status_norm", "unknown")) not in {"full", "closed", "ended"}
    )


def exclusion_bucket(row: pd.Series) -> str:
    reason = str(row.get("hard_filter_reason") or row.get("date_filter_reason") or "")
    norm = str(row.get("target_audience_norm", "unknown"))
    if row.get("child_suitability") == "excluded":
        if norm == "pet":
            return "반려동물 대상"
        if norm in {"adult", "youth", "senior", "organization", "teen"}:
            return "나이/대상 불일치"
    if row.get("is_weekday_only"):
        return "날짜/요일 불일치"
    if str(row.get("reservation_status_norm", "")) in {"full", "closed", "ended"}:
        return "신청 어려움"
    if row.get("child_suitability") == "review_needed" or "확인" in reason:
        return "확인 필요"
    return "기타"
