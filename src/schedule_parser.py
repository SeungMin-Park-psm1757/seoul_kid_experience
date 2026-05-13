from __future__ import annotations

import re
from datetime import date
from typing import Any

import pandas as pd

DAY_TO_CODE = {
    "월": "mon",
    "화": "tue",
    "수": "wed",
    "목": "thu",
    "금": "fri",
    "토": "sat",
    "일": "sun",
}
CODE_TO_DAY = {value: key for key, value in DAY_TO_CODE.items()}
DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_CODES = {"mon", "tue", "wed", "thu", "fri"}
WEEKEND_CODES = {"sat", "sun"}

DAILY_KEYWORDS = ["매일", "상시", "연중", "상설", "자유관람", "운영시간", "행사기간 내", "기간 중", "전시기간", "관람 가능"]
WEEKDAY_ONLY_KEYWORDS = ["평일", "평일주간", "평일야간", "주중"]
WEEKEND_KEYWORDS = ["주말", "공휴일", "주말 및 공휴일", "주말·공휴일"]
CLOSED_DAY_RE = re.compile(r"([월화수목금토일])\s*(?:요일)?\s*(?:휴관|휴무|휴장|공연\s*없음|제외|미운영)")
DAY_RANGE_RE = re.compile(r"([월화수목금토일])\s*(?:~|-|–|—)\s*([월화수목금토일])")
DAY_LIST_RE = re.compile(r"([월화수목금토일](?:\s*[,/·ㆍ]\s*[월화수목금토일])+)") 
DAY_LONG_RE = re.compile(r"([월화수목금토일])요일")
DAY_PAREN_RE = re.compile(r"\(([월화수목금토일])\)")
DAY_CONTEXT_RE = re.compile(r"(?<![가-힣])([월화수목금토일])\s*(?:오전|오후|[0-2]?\d\s*[:시]|매주|운영|공연|체험|프로그램)")

SCHEDULE_BADGE = {
    "exact_date_match": "날짜 일치",
    "same_weekend_match": "같은 주말",
    "recurring_day_match": "운영 요일 일치",
    "date_range_possible": "운영 가능",
    "schedule_unknown_check_needed": "공식 확인 필요",
    "weekday_only_excluded": "요일 불일치",
    "weekend_mismatch_excluded": "요일 불일치",
    "ended_excluded": "종료",
}


def _row_get(row: dict[str, Any] | pd.Series, key: str, default: Any = "") -> Any:
    try:
        value = row.get(key, default)
    except AttributeError:
        value = default
    return default if pd.isna(value) else value


def _compact_text(*values: Any) -> str:
    return " ".join(str(value or "") for value in values if value is not None and not pd.isna(value)).strip()


def _schedule_text(row: dict[str, Any] | pd.Series) -> str:
    keys = [
        "title", "time_text", "target_text", "rule_summary", "category", "venue",
        "raw_SVCNM", "raw_MINCLASSNM", "raw_MAXCLASSNM", "raw_PRO_TIME", "raw_DATE",
        "raw_PROGRAM", "raw_ETC_DESC", "raw_SVCOPNBGNDT", "raw_SVCOPNENDDT",
    ]
    values = [_row_get(row, key, "") for key in keys]
    if hasattr(row, "items"):
        values.extend(value for key, value in row.items() if str(key).startswith("raw_") and key not in keys)
    return _compact_text(*values)


def _expand_day_range(start: str, end: str) -> list[str]:
    codes = list(DAY_TO_CODE.values())
    start_code = DAY_TO_CODE[start]
    end_code = DAY_TO_CODE[end]
    start_idx = codes.index(start_code)
    end_idx = codes.index(end_code)
    if start_idx <= end_idx:
        return codes[start_idx : end_idx + 1]
    return codes[start_idx:] + codes[: end_idx + 1]


def _append_day(days: list[str], code: str) -> None:
    if code not in days:
        days.append(code)


def _parse_explicit_days(text: str) -> tuple[list[str], str]:
    days: list[str] = []
    raw_tokens: list[str] = []
    closed_days = {DAY_TO_CODE[match.group(1)] for match in CLOSED_DAY_RE.finditer(text)}
    parse_text = CLOSED_DAY_RE.sub(" ", text)

    if any(keyword in parse_text for keyword in WEEKDAY_ONLY_KEYWORDS):
        for code in ["mon", "tue", "wed", "thu", "fri"]:
            _append_day(days, code)
        raw_tokens.append("평일")
    if any(keyword in parse_text for keyword in WEEKEND_KEYWORDS):
        for code in ["sat", "sun"]:
            _append_day(days, code)
        raw_tokens.append("주말")
        if "공휴일" in parse_text:
            _append_day(days, "holiday")

    for match in DAY_RANGE_RE.finditer(parse_text):
        raw_tokens.append(match.group(0))
        for code in _expand_day_range(match.group(1), match.group(2)):
            _append_day(days, code)

    for match in DAY_LIST_RE.finditer(parse_text):
        token = match.group(1)
        raw_tokens.append(token)
        for char in re.findall(r"[월화수목금토일]", token):
            _append_day(days, DAY_TO_CODE[char])

    for regex in (DAY_LONG_RE, DAY_PAREN_RE, DAY_CONTEXT_RE):
        for match in regex.finditer(parse_text):
            raw_tokens.append(match.group(0))
            _append_day(days, DAY_TO_CODE[match.group(1)])

    days = [day for day in days if day not in closed_days]
    return sorted(days, key=lambda code: DAY_ORDER.index(code) if code in DAY_ORDER else 99), ", ".join(dict.fromkeys(raw_tokens))


def _date_values(row: dict[str, Any] | pd.Series) -> tuple[pd.Timestamp | pd.NaT, pd.Timestamp | pd.NaT]:
    start = pd.to_datetime(_row_get(row, "date_start", None), errors="coerce")
    end = pd.to_datetime(_row_get(row, "date_end", None), errors="coerce")
    if pd.isna(end):
        end = start
    return start, end


def _selected_weekend(selected_date: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    selected = pd.Timestamp(selected_date).normalize()
    if selected.weekday() <= 4:
        start = selected + pd.Timedelta(days=5 - selected.weekday())
    else:
        start = selected - pd.Timedelta(days=selected.weekday() - 5)
    return start, start + pd.Timedelta(days=1)


def parse_schedule_text(row: dict[str, Any] | pd.Series) -> dict[str, Any]:
    text = _schedule_text(row)
    days, days_raw = _parse_explicit_days(text)
    daily_signal = any(keyword in text for keyword in DAILY_KEYWORDS)
    start, end = _date_values(row)
    one_day = pd.notna(start) and pd.notna(end) and start.normalize() == end.normalize()

    if daily_signal and not days:
        days = ["daily"]
        days_raw = "매일/상시"

    regular_days = {day for day in days if day in DAY_ORDER}
    if days == ["daily"]:
        schedule_type = "always_open" if any(keyword in text for keyword in ["상시", "연중", "상설", "자유관람"]) else "date_range_daily"
        confidence = "medium"
    elif regular_days == WEEKDAY_CODES:
        schedule_type = "weekday_only"
        confidence = "high"
    elif regular_days and regular_days.issubset(WEEKDAY_CODES):
        schedule_type = "recurring_weekdays"
        confidence = "high"
    elif regular_days and regular_days.issubset(WEEKEND_CODES):
        schedule_type = "weekend_only" if regular_days == WEEKEND_CODES else "recurring_weekends"
        confidence = "high"
    elif regular_days:
        schedule_type = "recurring_weekdays"
        confidence = "high"
    elif one_day:
        schedule_type = "exact_date"
        confidence = "medium"
    else:
        schedule_type = "unknown_schedule"
        confidence = "low"

    return {
        "schedule_text_raw": text,
        "schedule_days_raw": days_raw,
        "schedule_days_norm": days or ["unknown"],
        "schedule_type": schedule_type,
        "schedule_confidence": confidence,
    }


def classify_schedule_for_selected_date(row: dict[str, Any] | pd.Series, selected_date: date) -> dict[str, Any]:
    parsed = parse_schedule_text(row)
    selected_ts = pd.Timestamp(selected_date).normalize()
    selected_weekday = DAY_ORDER[selected_ts.weekday()]
    selected_is_weekend = selected_weekday in WEEKEND_CODES
    start, end = _date_values(row)
    if pd.notna(start):
        start = start.normalize()
    if pd.notna(end):
        end = end.normalize()

    selected_in_range = pd.notna(start) and pd.notna(end) and start <= selected_ts <= end
    weekend_start, weekend_end = _selected_weekend(selected_date)
    weekend_overlaps = pd.notna(start) and pd.notna(end) and start <= weekend_end and end >= weekend_start
    ended = pd.notna(end) and end < selected_ts
    days = parsed["schedule_days_norm"]
    regular_days = {day for day in days if day in DAY_ORDER}

    eligible = False
    match_level = "schedule_unknown_check_needed"
    reason = "운영 요일을 확인할 수 없어 공식 링크 확인이 필요한 후보로 분류했습니다."

    if ended:
        match_level = "ended_excluded"
        reason = "선택한 날짜 기준 이미 종료된 후보입니다."
    elif "daily" in days:
        eligible = bool(selected_in_range or (pd.isna(start) and pd.isna(end)))
        match_level = "recurring_day_match" if eligible else "weekend_mismatch_excluded"
        reason = "" if eligible else "운영 기간이 선택 날짜와 맞지 않습니다."
    elif regular_days:
        if selected_weekday in regular_days and selected_in_range:
            eligible = True
            match_level = "recurring_day_match"
            reason = ""
        elif selected_is_weekend and regular_days & WEEKEND_CODES and weekend_overlaps:
            eligible = True
            match_level = "same_weekend_match"
            reason = ""
        elif selected_is_weekend and regular_days and regular_days.issubset(WEEKDAY_CODES):
            match_level = "weekday_only_excluded"
            day_text = "·".join(CODE_TO_DAY[day] for day in DAY_ORDER if day in regular_days)
            reason = f"이 프로그램은 {day_text} 운영으로 표시되어 선택한 주말과 맞지 않습니다."
        else:
            match_level = "weekend_mismatch_excluded"
            day_text = "·".join(CODE_TO_DAY[day] for day in DAY_ORDER if day in regular_days)
            reason = f"이 프로그램은 {day_text} 운영으로 표시되어 선택한 날짜와 맞지 않습니다."
    elif parsed["schedule_type"] == "exact_date":
        if selected_in_range:
            eligible = True
            match_level = "exact_date_match"
            reason = ""
        elif selected_is_weekend and weekend_overlaps:
            eligible = True
            match_level = "same_weekend_match"
            reason = ""
        else:
            match_level = "weekend_mismatch_excluded"
            reason = "해당 일자가 선택한 날짜와 맞지 않습니다."
    elif selected_in_range:
        match_level = "schedule_unknown_check_needed"
        reason = "운영 기간에는 포함되지만 실제 운영 요일이 불명확해 기본 추천에서 제외했습니다."

    is_weekday_only = parsed["schedule_type"] == "weekday_only" or (bool(regular_days) and regular_days.issubset(WEEKDAY_CODES))
    is_weekend_eligible = "daily" in days or bool(regular_days & WEEKEND_CODES) or parsed["schedule_type"] in {"always_open", "date_range_daily"}
    if selected_is_weekend and match_level == "weekday_only_excluded":
        reason = reason or "선택한 날짜가 주말이라 평일 전용 프로그램은 제외했습니다."

    return {
        **parsed,
        "selected_date_weekday": selected_weekday,
        "selected_date_is_weekend": selected_is_weekend,
        "schedule_match_level": match_level,
        "is_weekend_eligible": bool(is_weekend_eligible),
        "is_weekday_only": bool(is_weekday_only),
        "is_selected_date_eligible": bool(eligible),
        "schedule_filter_reason": reason,
    }
