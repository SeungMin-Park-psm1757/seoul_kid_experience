from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import pandas as pd

from .config import NEIGHBOR_DISTRICTS, SEOUL_DISTRICTS
from .curation_rules import enrich_curation_fields
from .normalize_date import classify_date_match, weekend_bounds
from .normalize_status import AVAILABLE_NORMS, FULL_OR_CLOSED_NORMS, status_priority
from .schedule_parser import SCHEDULE_BADGE, classify_schedule_for_selected_date

DATE_SCORE = {
    "exact_date": 30,
    "same_weekend": 24,
    "near_7_days": 12,
    "wider_option": 4,
    "not_for_selected_date": 0,
}

DATE_BADGE = {
    "exact_date": "날짜 일치",
    "same_weekend": "같은 주말",
    "near_7_days": "±7일",
    "wider_option": "조건 확장",
    "not_for_selected_date": "선택 날짜와 다름",
}

SCHEDULE_SCORE = {
    "exact_date_match": 30,
    "recurring_day_match": 28,
    "date_range_possible": 24,
    "same_weekend_match": 22,
    "schedule_unknown_check_needed": 0,
    "weekday_only_excluded": 0,
    "weekend_mismatch_excluded": 0,
    "ended_excluded": 0,
}

SCHEDULE_RANK = {
    "exact_date_match": 1,
    "recurring_day_match": 2,
    "date_range_possible": 2,
    "same_weekend_match": 3,
    "schedule_unknown_check_needed": 8,
    "weekday_only_excluded": 9,
    "weekend_mismatch_excluded": 9,
    "ended_excluded": 9,
}

LOW_COST_TYPES = {"무료", "저비용"}
ACTIONABLE_NORMS = {"available", "always_available", "closing_soon"}
EXPLICIT_CHILD_CONTEXT = [
    "어린이", "아동", "초등", "초등학생", "유아", "가족", "부모", "보호자", "키즈", "아이",
]
HEAVY_TOPIC_KEYWORDS = [
    "5.18", "5·18", "광주", "민주화", "증언", "증인", "참사", "학살", "고문", "폭력",
    "전쟁", "죽음", "희생", "추모", "사망", "재난", "범죄", "난민", "홀로코스트",
]
ADULT_CULTURE_KEYWORDS = [
    "북콘서트", "북토크", "작가와의 만남", "문예", "문학", "인문학", "강연", "특강",
    "세미나", "포럼", "토론", "대담", "강좌", "심포지엄",
]


@dataclass(frozen=True)
class ParentFilters:
    child_age: int
    origin: str
    selected_day: date
    max_travel: int
    fee_types: tuple[str, ...]
    indoor_types: tuple[str, ...]
    categories: tuple[str, ...]
    grade: str = ""


def district_travel_minutes(origin: str, destination: str) -> int:
    if origin == destination:
        return 15
    if destination in NEIGHBOR_DISTRICTS.get(origin, []):
        return 28
    try:
        gap = abs(SEOUL_DISTRICTS.index(origin) - SEOUL_DISTRICTS.index(destination))
    except ValueError:
        gap = 6
    return min(80, 24 + gap * 4)


def travel_range_label(minutes: int) -> str:
    lower = max(10, int(minutes // 10 * 10))
    upper = min(95, lower + 10)
    return f"추정 {lower}~{upper}분"


def travel_difficulty(minutes: int) -> str:
    if minutes <= 25:
        return "낮음"
    if minutes <= 50:
        return "보통"
    return "높음"


def _availability_score(norm: str) -> int:
    return {
        "available": 40,
        "always_available": 36,
        "closing_soon": 30,
        "soon_open": 12,
        "unknown": 8,
        "full": 0,
        "closed": 0,
        "ended": 0,
    }.get(norm, 8)


def _age_score(row: pd.Series, child_age: int) -> int:
    if row.get("age_fit", False):
        if row.get("target_audience_norm") == "general_public" and int(row.get("age_min", 0)) <= 0 and int(row.get("age_max", 99)) >= 90:
            return 6
        span = max(1, row["age_max"] - row["age_min"])
        return 15 if span <= 4 else 12
    return 0


def _target_priority(row: pd.Series) -> int:
    norm = str(row.get("target_audience_norm", "unknown"))
    if norm in {"child", "family", "elementary", "infant"}:
        return 1
    if norm == "teen":
        return 2
    if norm == "general_public":
        return 3
    return 9


def _distance_score(minutes: int, max_travel: int) -> int:
    if minutes > max_travel:
        return 0
    return max(2, int(10 * (1 - minutes / max(max_travel, 1))))


def _fee_score(row: pd.Series) -> int:
    return 5 if row.get("fee_type") in LOW_COST_TYPES or int(row.get("fee", 0)) == 0 else 0


def _indoor_score(row: pd.Series, filters: ParentFilters) -> int:
    indoor = str(row.get("indoor_outdoor", ""))
    if indoor in filters.indoor_types:
        return 5
    return 0


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _row_text(row: pd.Series) -> str:
    fields = [
        "title", "target_text", "age_label", "category", "venue", "rule_summary",
        "source", "raw_SVCNM", "raw_CODENAME", "raw_PROGRAM", "raw_ETC_DESC",
    ]
    return " ".join(str(row.get(field, "") or "") for field in fields)


def assess_child_content(row: pd.Series, child_age: int) -> dict[str, object]:
    text = _row_text(row)
    has_explicit_child = _has_any(text, EXPLICIT_CHILD_CONTEXT)
    broad_age = int(row.get("age_min", 0)) <= 0 and int(row.get("age_max", 99)) >= 90
    broad_target = str(row.get("target_text", "")) in {"누구나", "제한없음", "전체", "일반"} or row.get("target_audience_norm") == "general_public"

    if child_age <= 9 and _has_any(text, HEAVY_TOPIC_KEYWORDS) and not has_explicit_child:
        return {
            "child_content_fit": False,
            "content_difficulty": "hard",
            "child_content_reason": "주제가 초등 저학년에게 무거울 수 있어 기본 추천에서 제외했습니다.",
            "content_filter_reason": "아이 난이도 높음",
        }

    if broad_target and broad_age and not has_explicit_child:
        if _has_any(text, ADULT_CULTURE_KEYWORDS) or row.get("source") == "서울문화행사":
            return {
                "child_content_fit": False,
                "content_difficulty": "adult_or_general",
                "child_content_reason": "누구나 대상이지만 어린이/가족 맥락이 없어 기본 추천에서 제외했습니다.",
                "content_filter_reason": "어린이 맥락 부족",
            }
        return {
            "child_content_fit": False,
            "content_difficulty": "review_needed",
            "child_content_reason": "연령 제한 없음만으로는 아이에게 맞는지 판단하기 어려워 공식 확인 필요로 분리했습니다.",
            "content_filter_reason": "어린이 맥락 확인 필요",
        }

    return {
        "child_content_fit": True,
        "content_difficulty": "child_friendly" if has_explicit_child else "normal",
        "child_content_reason": "아이/가족 맥락을 확인했습니다." if has_explicit_child else "",
        "content_filter_reason": "",
    }


def _grade_to_num(grade: str) -> int | None:
    match = re.search(r"초\s*([1-6])", str(grade or ""))
    return int(match.group(1)) if match else None


def assess_grade_fit(row: pd.Series, grade: str) -> dict[str, object]:
    grade_num = _grade_to_num(grade)
    if grade_num is None:
        return {"grade_fit": True, "grade_min": None, "grade_max": None, "grade_filter_reason": ""}

    text = _row_text(row)
    patterns = [
        r"(?:초등|초등학교|초)?\s*([1-6])\s*[~\-–]\s*([1-6])\s*학년",
        r"(?:초등|초등학교|초)?\s*([1-6])\s*학년\s*[~\-–]\s*(?:초등|초등학교|초)?\s*([1-6])\s*학년",
        r"([1-6])\s*[~\-–]\s*([1-6])\s*학년",
    ]
    grade_min = grade_max = None
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            grade_min = int(match.group(1))
            grade_max = int(match.group(2))
            break

    if grade_min is None:
        single = re.search(r"(?:초등|초등학교|초)\s*([1-6])\s*학년", text)
        if single:
            grade_min = grade_max = int(single.group(1))

    if grade_min is None:
        return {"grade_fit": True, "grade_min": None, "grade_max": None, "grade_filter_reason": ""}

    if grade_min <= grade_num <= grade_max:
        return {"grade_fit": True, "grade_min": grade_min, "grade_max": grade_max, "grade_filter_reason": ""}

    return {
        "grade_fit": False,
        "grade_min": grade_min,
        "grade_max": grade_max,
        "grade_filter_reason": f"{grade_min}~{grade_max}학년 대상이라 현재 {grade} 조건과 맞지 않습니다.",
    }


def _normalize_series_title(title: object) -> str:
    text = str(title or "").lower()
    text = re.sub(r"\[[^\]]*(?:월|화|수|목|금|토|일|주말|\d{1,2}[./-]\d{1,2})[^\]]*\]", " ", text)
    text = re.sub(r"\((?:월|화|수|목|금|토|일|,|·|ㆍ|/|\s|주말|공휴일|\d|[.~:시분오전후-])+\)", " ", text)
    text = re.sub(r"20\d{2}년", " ", text)
    text = re.sub(r"\d{1,2}\s*월", " ", text)
    text = re.sub(r"\d{1,2}[./-]\d{1,2}(?:\s*[~–—-]\s*\d{1,2}[./-]\d{1,2})?", " ", text)
    text = re.sub(r"\bno\.?\s*\d+\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\d+\s*차", " ", text)
    text = re.sub(r"정원\s*\d+\s*명|대기자\s*\d+\s*명", " ", text)
    text = re.sub(r"[\[\](){}『』〈〉\"'“”‘’]", " ", text)
    text = re.sub(r"[^0-9a-z가-힣]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def make_series_key(row: pd.Series) -> str:
    venue = str(row.get("venue", "") or "").strip()
    category = str(row.get("category", "") or "").strip()
    normalized = _normalize_series_title(row.get("title", ""))
    return "|".join([venue, category, normalized])


def dedupe_recommendation_series(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "series_key" not in df.columns:
        return df
    return df.drop_duplicates("series_key", keep="first")


def recommendation_reason(row: pd.Series) -> str:
    if row.get("child_suitability") == "excluded":
        return row.get("child_suitability_reason", "아이 대상이 아니라 추천에서 제외했습니다.")
    if not row.get("child_content_fit", True):
        return row.get("child_content_reason", "아이에게 맞는 내용인지 확인이 필요해 기본 추천에서 제외했습니다.")
    if not row.get("grade_fit", True):
        return row.get("grade_filter_reason", "학년 조건이 맞지 않아 기본 추천에서 제외했습니다.")
    if not row.get("is_selected_date_eligible", row.get("date_weekday_match", True)):
        return row.get("schedule_filter_reason") or row.get("date_filter_reason", "선택한 날짜와 운영 요일이 맞지 않습니다.")
    norm = row.get("reservation_status_norm", "unknown")
    if norm == "soon_open":
        return "현재 접수 예정 상태라 바로 신청 후보에서는 제외하고, 예약 시작일 확인이 필요합니다."
    if norm in FULL_OR_CLOSED_NORMS:
        return f"{row.get('availability_group', '마감')} 상태라 기본 추천에서 제외했습니다."
    if norm == "unknown":
        return "상태 정보가 불완전해 공식 링크 확인이 필요한 후보입니다."

    parts = []
    if norm == "available":
        parts.append("지금 신청 가능한 후보")
    elif norm == "always_available":
        parts.append("신청 절차가 비교적 간단한 후보")
    elif norm == "closing_soon":
        parts.append("마감 임박이라 먼저 확인할 후보")

    if int(row.get("age_min", 0)) <= 0 and int(row.get("age_max", 99)) >= 90:
        parts.append("대상 제한 없음")
    else:
        parts.append(f"{int(row['age_min'])}-{int(row['age_max'])}세 대상")
    schedule_level = row.get("schedule_match_level", "")
    if schedule_level == "exact_date_match":
        parts.append("선택한 날짜 운영")
    elif schedule_level == "recurring_day_match":
        parts.append("선택한 요일 운영")
    elif schedule_level == "same_weekend_match":
        parts.append("같은 주말 운영")
    elif row.get("date_match_level") == "near_7_days":
        parts.append("선택 날짜와 가까운 일정")
    if row.get("fee_type") in LOW_COST_TYPES:
        parts.append(row.get("fee_type"))
    if row.get("indoor_outdoor") in {"실내", "혼합"}:
        parts.append("실내/날씨 대안")
    if row.get("reservation_friction") == "low":
        parts.append("신청 부담 낮음")
    if int(row.get("travel_minutes", 99)) <= 35:
        parts.append("출발지 기준 가까움")
    return ", ".join(parts[:5]) + "입니다."


def caution_note(row: pd.Series) -> str:
    notes = ["회차별 잔여석과 신청 가능 여부는 공식 예약/출처 링크에서 최종 확인하세요"]
    if row.get("schedule_match_level") == "schedule_unknown_check_needed":
        notes.insert(0, "운영 요일이 불명확해 공식 링크 확인이 필요합니다")
    if not row.get("is_selected_date_eligible", True):
        notes.insert(0, str(row.get("schedule_filter_reason", "선택 날짜와 운영 요일이 맞지 않습니다")))
    if row.get("reservation_status_norm") == "closing_soon":
        notes.insert(0, "마감 임박 상태라 조기 종료될 수 있습니다")
    if row.get("reservation_status_norm") == "unknown":
        notes.insert(0, "예약상태가 불완전합니다")
    if row.get("date_match_level") == "wider_option":
        notes.insert(0, "선택 날짜 기준 30일 이내 확장 후보입니다")
    if row.get("date_match_level") == "not_for_selected_date":
        notes.insert(0, "선택 날짜와 맞지 않아 기본 추천에서 제외될 수 있습니다")
    if row.get("reservation_difficulty") == "hard":
        notes.insert(0, "마감 위험이 높습니다")
    if row.get("child_suitability") != "eligible":
        notes.insert(0, str(row.get("child_suitability_reason", "대상 조건 확인 필요")))
    if not row.get("child_content_fit", True):
        notes.insert(0, str(row.get("child_content_reason", "아이에게 맞는 내용인지 확인이 필요합니다")))
    if not row.get("grade_fit", True):
        notes.insert(0, str(row.get("grade_filter_reason", "학년 조건 확인 필요")))
    if not str(row.get("source_url", "")).strip():
        notes.insert(0, "공식 링크가 없어 확인 필요로 표시했습니다")
    return " · ".join(notes) + "."


def add_recommendation_features(programs: pd.DataFrame, filters: ParentFilters) -> pd.DataFrame:
    df = programs.copy()
    if df.empty:
        return df
    curation_columns = {
        "target_audience_norm", "child_suitability", "child_suitability_reason",
        "hard_filter_reason", "is_weekend_available", "is_weekday_only",
        "date_weekday_match", "date_filter_reason", "reservation_friction",
        "reservation_difficulty",
    }
    if not curation_columns.issubset(df.columns):
        df = enrich_curation_fields(df, filters.selected_day)
    df["program_id"] = df.get("program_id", df.get("id", "")).astype(str)
    df["id"] = df.get("id", df["program_id"]).astype(str)
    df["date_start"] = pd.to_datetime(df["date_start"], errors="coerce")
    df["date_end"] = pd.to_datetime(df["date_end"], errors="coerce")
    df["fee"] = pd.to_numeric(df["fee"], errors="coerce").fillna(0).astype(int)
    df["age_min"] = pd.to_numeric(df["age_min"], errors="coerce").fillna(0).astype(int)
    df["age_max"] = pd.to_numeric(df["age_max"], errors="coerce").fillna(99).astype(int)
    df["reservation_status_norm"] = df.get("reservation_status_norm", "unknown").fillna("unknown")
    df["availability_group"] = df.get("availability_group", "확인 필요").fillna("확인 필요")
    df["status"] = df["availability_group"]
    df["status_label"] = df["availability_group"]
    df["series_key"] = df.apply(make_series_key, axis=1)

    # 실제 API에서는 date_start/date_end가 전체 운영 기간이고, 실제 회차
    # 요일은 제목/시간/원본 필드에 따로 들어가는 경우가 많다. 따라서
    # 선택 날짜 추천 가능 여부는 운영 요일 파서를 최우선으로 재계산한다.
    schedule_features = df.apply(
        lambda row: classify_schedule_for_selected_date(row, filters.selected_day),
        axis=1,
        result_type="expand",
    )
    for column in schedule_features.columns:
        df[column] = schedule_features[column]
    df["date_weekday_match"] = df["is_selected_date_eligible"].fillna(False).astype(bool)
    df["date_filter_reason"] = df["schedule_filter_reason"].fillna("")

    df["travel_minutes"] = df["district"].apply(lambda district: district_travel_minutes(filters.origin, district))
    df["travel_range"] = df["travel_minutes"].apply(travel_range_label)
    df["travel_difficulty"] = df["travel_minutes"].apply(travel_difficulty)
    raw_age_fit = (df["age_min"] <= filters.child_age) & (filters.child_age <= df["age_max"])
    broad_age = df["age_min"].le(0) & df["age_max"].ge(90)
    def text_column(name: str) -> pd.Series:
        if name in df.columns:
            return df[name].fillna("").astype(str)
        return pd.Series("", index=df.index, dtype="object")

    audience_text = text_column("title") + " " + text_column("target_text") + " " + text_column("age_label")
    infant_only_for_elementary = (
        df["target_audience_norm"].eq("infant")
        & (filters.child_age >= 7)
        & ~audience_text.str.contains("초등|초등학생|가족|부모|보호자", regex=True, na=False)
    )
    institution_group_only = (
        audience_text.str.contains("유아 단체|어린이집|유치원|기관", regex=True, na=False)
        & ~audience_text.str.contains("초등|초등학생|가족|개인|부모|보호자", regex=True, na=False)
    )
    df["age_fit"] = (
        raw_age_fit
        & df["child_suitability"].eq("eligible")
        & (~broad_age | df["target_audience_norm"].isin(["child", "family", "infant", "elementary", "general_public"]))
        & ~infant_only_for_elementary
        & ~institution_group_only
    )
    mismatch = infant_only_for_elementary | institution_group_only
    df.loc[mismatch, "hard_filter_reason"] = "학년/대상 불일치"
    df.loc[mismatch, "child_suitability_reason"] = "유아 단체 또는 기관 대상이라 현재 학년 조건에서 제외했습니다."
    content_features = df.apply(lambda row: assess_child_content(row, filters.child_age), axis=1, result_type="expand")
    for column in content_features.columns:
        df[column] = content_features[column]
    content_mismatch = ~df["child_content_fit"].fillna(True).astype(bool)
    df.loc[content_mismatch & df["hard_filter_reason"].fillna("").eq(""), "hard_filter_reason"] = df.loc[
        content_mismatch & df["hard_filter_reason"].fillna("").eq(""),
        "content_filter_reason",
    ]
    grade_features = df.apply(lambda row: assess_grade_fit(row, filters.grade), axis=1, result_type="expand")
    for column in grade_features.columns:
        df[column] = grade_features[column]
    grade_mismatch = ~df["grade_fit"].fillna(True).astype(bool)
    df.loc[grade_mismatch & df["hard_filter_reason"].fillna("").eq(""), "hard_filter_reason"] = "학년 조건 불일치"
    df["date_match_level"] = df.apply(lambda row: classify_date_match(row["date_start"], row["date_end"], filters.selected_day), axis=1)
    df["date_match_badge"] = (
        df["schedule_match_level"].map(SCHEDULE_BADGE)
        .fillna(df["date_match_level"].map(DATE_BADGE))
        .fillna("확인 필요")
    )
    df["available_now"] = df["reservation_status_norm"].isin(AVAILABLE_NORMS)
    df["is_full_or_closed"] = df["reservation_status_norm"].isin(FULL_OR_CLOSED_NORMS)
    df["parent_eligible"] = (
        df["child_suitability"].eq("eligible")
        & df["child_content_fit"].fillna(True).astype(bool)
        & df["grade_fit"].fillna(True).astype(bool)
        & df["is_selected_date_eligible"].fillna(False).astype(bool)
        & ~df["is_weekday_only"].fillna(False).astype(bool)
        & ~df["reservation_status_norm"].isin({"full", "closed", "ended"})
    )
    df["is_actionable"] = (
        df["reservation_status_norm"].isin(ACTIONABLE_NORMS)
        & df["is_selected_date_eligible"].fillna(False).astype(bool)
        & ~df["date_match_level"].isin(["not_for_selected_date"])
        & df["parent_eligible"]
        & df["source_url"].fillna("").astype(str).str.len().gt(0)
    )
    df["is_free_or_low"] = df["fee_type"].isin(LOW_COST_TYPES) | df["fee"].eq(0)
    df["is_indoor"] = df["indoor_outdoor"].isin(["실내", "혼합"])
    df["interest_match"] = df["category"].isin(filters.categories)
    df["status_priority"] = df["reservation_status_norm"].map(status_priority).fillna(5).astype(int)
    df["date_rank"] = df["schedule_match_level"].map(SCHEDULE_RANK).fillna(9).astype(int)
    df["availability_score"] = df["reservation_status_norm"].map(_availability_score).fillna(8).astype(float)
    df["date_score"] = df["schedule_match_level"].map(SCHEDULE_SCORE).fillna(0).astype(float)
    df["age_score"] = df.apply(lambda row: _age_score(row, filters.child_age), axis=1)
    df["target_priority"] = df.apply(_target_priority, axis=1)
    df["distance_score"] = df["travel_minutes"].apply(lambda minutes: _distance_score(minutes, filters.max_travel))
    df["fee_score"] = df.apply(_fee_score, axis=1)
    df["indoor_score"] = df.apply(lambda row: _indoor_score(row, filters), axis=1)
    df["recommend_score"] = (
        df["availability_score"] + df["date_score"] + df["age_score"]
        + df["distance_score"] + df["fee_score"] + df["indoor_score"]
    )
    # Avoid per-row Plan B recomputation on live API data. Detailed Plan B is
    # calculated only for the selected card; this score is a lightweight signal.
    actionable_pool = (
        df["age_fit"]
        & df["is_actionable"]
        & df["is_selected_date_eligible"].fillna(False).astype(bool)
        & df["date_match_level"].isin(["exact_date", "same_weekend"])
    )
    df["_planb_pool_count"] = df[actionable_pool].groupby("category")["program_id"].transform("count")
    df["planb_score"] = df["_planb_pool_count"].fillna(0).clip(upper=10).astype(int) * 10
    df["recommendation_reason"] = df.apply(recommendation_reason, axis=1)
    df["caution_note"] = df.apply(caution_note, axis=1)
    return df


def sort_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.sort_values(
        ["date_rank", "status_priority", "target_priority", "recommend_score", "travel_minutes"],
        ascending=[True, True, True, False, True],
    )


def filter_recommendations(enriched: pd.DataFrame, filters: ParentFilters, *, include_extension: bool = False) -> pd.DataFrame:
    if enriched.empty:
        return enriched
    allowed_dates = {"exact_date", "same_weekend"}
    if include_extension:
        allowed_dates.update({"near_7_days", "wider_option"})
    out = enriched[
        enriched["age_fit"]
        & enriched["is_actionable"]
        & enriched["is_selected_date_eligible"].fillna(False).astype(bool)
        & enriched["date_match_level"].isin(allowed_dates)
        & enriched["travel_minutes"].le(filters.max_travel)
        & enriched["fee_type"].isin(filters.fee_types)
        & enriched["indoor_outdoor"].isin(filters.indoor_types)
        & enriched["category"].isin(filters.categories)
    ].copy()
    return dedupe_recommendation_series(sort_recommendations(out))


def closed_or_uncertain_candidates(enriched: pd.DataFrame, filters: ParentFilters) -> pd.DataFrame:
    if enriched.empty:
        return enriched
    out = enriched[
        enriched["age_fit"]
        & enriched["date_match_level"].isin(["exact_date", "same_weekend", "near_7_days", "wider_option", "not_for_selected_date"])
        & (
            enriched["is_full_or_closed"]
            | enriched["reservation_status_norm"].isin(["unknown", "soon_open", "ended"])
            | enriched["date_match_level"].isin(["not_for_selected_date"])
            | enriched["child_suitability"].isin(["excluded", "review_needed"])
            | ~enriched["date_weekday_match"]
        )
    ].copy()
    def excluded_reason(row: pd.Series) -> str:
        if row.get("visited_excluded", False):
            return "이미 가본 곳으로 표시되어 현재 추천에서 제외했습니다."
        if not row.get("child_content_fit", True):
            return row.get("child_content_reason", "아이에게 맞는 내용인지 확인이 필요해 기본 추천에서 제외했습니다.")
        if not row.get("grade_fit", True):
            return row.get("grade_filter_reason", "학년 조건이 맞지 않아 기본 추천에서 제외했습니다.")
        if not row.get("is_selected_date_eligible", True):
            return row.get("schedule_filter_reason") or row.get("date_filter_reason", "선택 날짜와 운영 요일이 맞지 않습니다.")
        if row.get("child_suitability") in {"excluded", "review_needed"}:
            return row.get("child_suitability_reason", "아이 나이 또는 대상 조건이 맞지 않습니다.")
        if row.get("reservation_status_norm") in FULL_OR_CLOSED_NORMS | {"ended"}:
            return f"{row.get('availability_group', '마감/종료')} 상태라 오늘의 추천에서 제외했습니다."
        if row.get("reservation_status_norm") in {"unknown", "soon_open"}:
            return f"{row.get('availability_group', '확인 필요')} 상태라 공식 링크 확인이 필요한 후보입니다."
        return f"{row.get('availability_group', '확인 필요')} 상태라 기본 추천에서 분리했습니다."

    out["excluded_reason"] = out.apply(excluded_reason, axis=1)
    return sort_recommendations(out)


def available_now_candidates(enriched: pd.DataFrame, filters: ParentFilters) -> pd.DataFrame:
    return filter_recommendations(enriched, filters, include_extension=False)


def plan_b_candidates(enriched: pd.DataFrame, selected: pd.Series, filters: ParentFilters, limit: int = 5) -> pd.DataFrame:
    if enriched.empty:
        return enriched
    neighbors = set(NEIGHBOR_DISTRICTS.get(str(selected.get("district")), []))
    selected_id = str(selected.get("program_id", selected.get("id", "")))
    out = enriched[
        enriched["program_id"].astype(str).ne(selected_id)
        & enriched["series_key"].astype(str).ne(str(selected.get("series_key", "")))
        & enriched["age_fit"]
        & enriched["is_actionable"]
        & enriched["is_selected_date_eligible"].fillna(False).astype(bool)
        & enriched["date_match_level"].isin(["exact_date", "same_weekend"])
        & enriched["fee_type"].isin(filters.fee_types)
        & enriched["indoor_outdoor"].isin(filters.indoor_types)
        & enriched["reservation_friction"].isin(["low", "medium"])
    ].copy()
    if out.empty:
        return out
    out["same_category"] = out["category"].eq(selected.get("category"))
    out["near_place"] = out["district"].eq(selected.get("district")) | out["district"].isin(neighbors)
    out["travel_increase"] = (out["travel_minutes"] - int(selected.get("travel_minutes", 0))).clip(lower=0)
    out["planb_reason"] = out.apply(lambda row: planb_reason(row, selected), axis=1)
    sorted_out = out.sort_values(
        ["date_rank", "reservation_friction", "status_priority", "near_place", "same_category", "travel_increase", "recommend_score"],
        ascending=[True, True, True, False, False, True, False],
    )
    return dedupe_recommendation_series(sorted_out).head(limit)


def planb_reason(row: pd.Series, selected: pd.Series) -> str:
    if selected.get("reservation_status_norm") in FULL_OR_CLOSED_NORMS | {"soon_open", "unknown"} and row.get("available_now"):
        return f"원 후보는 {selected.get('availability_group')}이지만, 이 후보는 {row.get('availability_group')} 상태입니다."
    if row.get("reservation_friction") == "low":
        return "첫 후보가 막히면, 신청 부담이 비교적 낮은 대안입니다."
    if row.get("source") == "서울문화행사":
        return "예약형은 아니지만 행사기간 내 참여 가능성이 있어 대체 후보로 적합합니다."
    if row.get("category") == selected.get("category"):
        return f"같은 {row.get('category')} 분야이며, 이번 주말 신청 가능한 대체안입니다."
    if row.get("district") == selected.get("district"):
        return "같은 자치구의 대체안이라 이동 부담이 작습니다."
    return "같은 날짜권·연령 조건에 맞는 대체 후보입니다."


def condition_relaxation_counts(programs: pd.DataFrame, filters: ParentFilters) -> pd.DataFrame:
    base = add_recommendation_features(programs, filters)
    steps: list[dict[str, float | int | str]] = []

    def count_for(label: str, mask: pd.Series) -> None:
        if "series_key" in base.columns:
            count = int(base.loc[mask, "series_key"].nunique())
        else:
            count = int(mask.sum())
        prev = int(steps[-1]["candidate_count"]) if steps else 0
        increase = count - prev
        rate = 0.0 if prev == 0 else (increase / prev) * 100
        steps.append({"step": label, "candidate_count": count, "increase": increase, "increase_rate": rate})

    common = base["age_fit"] & base["is_actionable"] & base["travel_minutes"].le(filters.max_travel)
    base_mask = (
        common
        & base["date_match_level"].eq("exact_date")
        & base["fee_type"].isin(filters.fee_types)
        & base["indoor_outdoor"].isin(filters.indoor_types)
        & base["category"].isin(filters.categories)
    )
    count_for("내 조건 그대로", base_mask)

    mask = (
        common
        & base["date_match_level"].isin(["exact_date", "same_weekend", "near_7_days"])
        & base["fee_type"].isin(filters.fee_types)
        & base["indoor_outdoor"].isin(filters.indoor_types)
        & base["category"].isin(filters.categories)
    )
    count_for("날짜 ±7일 허용", mask)

    neighbor_set = set(NEIGHBOR_DISTRICTS.get(filters.origin, [])) | {filters.origin}
    mask = mask | (
        base["age_fit"]
        & base["is_actionable"]
        & base["date_match_level"].isin(["exact_date", "same_weekend", "near_7_days"])
        & base["district"].isin(neighbor_set)
        & base["fee_type"].isin(filters.fee_types)
        & base["indoor_outdoor"].isin(filters.indoor_types)
        & base["category"].isin(filters.categories)
    )
    count_for("인접 자치구 허용", mask)

    mask = mask | (
        common
        & base["date_match_level"].isin(["exact_date", "same_weekend", "near_7_days"])
        & base["indoor_outdoor"].isin(filters.indoor_types)
        & base["category"].isin(filters.categories)
    )
    count_for("유료 포함", mask)

    mask = mask | (
        common
        & base["date_match_level"].isin(["exact_date", "same_weekend", "near_7_days"])
        & base["category"].isin(filters.categories)
    )
    count_for("실외 포함", mask)

    mask = mask | (
        common
        & base["date_match_level"].isin(["exact_date", "same_weekend", "near_7_days"])
    )
    count_for("관심분야 전체 허용", mask)
    return pd.DataFrame(steps)


def best_relaxation_comment(funnel: pd.DataFrame) -> str:
    if funnel.empty or len(funnel) < 2:
        return "조건 완화 효과를 계산할 후보가 부족합니다."
    best = funnel.iloc[1:].sort_values("increase", ascending=False).iloc[0]
    prev_idx = max(0, int(best.name) - 1)
    prev = funnel.iloc[prev_idx]["candidate_count"]
    if int(best["increase"]) <= 0:
        return "현재 조건에서는 조건을 완화해도 후보 증가가 크지 않습니다."
    return f"{best['step']} 단계에서 후보가 {int(prev)}개에서 {int(best['candidate_count'])}개로 가장 크게 늘어납니다."
