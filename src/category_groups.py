from __future__ import annotations

from collections.abc import Iterable


CATEGORY_GROUPS: dict[str, tuple[str, ...]] = {
    "교육/체험": ("교육/체험", "교육체험", "공예/취미", "미술제작"),
    "서울형키즈카페": ("서울형키즈카페",),
    "공원/숲": ("공원탐방", "산림여가", "도시농업"),
    "자연/과학": ("자연/과학",),
    "전시/관람": ("전시/미술", "전시/관람", "전시실"),
    "공연/문화행사": ("문화행사", "축제-문화/예술", "축제-전통/역사", "축제-자연/경관", "축제-시민화합", "축제-관광/체육", "축제-기타"),
    "농장체험": ("농장체험",),
    "역사": ("역사",),
    "스포츠/놀이": ("스포츠", "테니스장", "풋살장", "축구장", "농구장", "피클볼장", "체육관", "족구장", "야구장", "배드민턴장", "골프장", "다목적경기장", "배구장", "탁구장", "수영장", "운동장"),
    "기타": ("기타", "민원 등 기타", "주민공유공간"),
}

PARENT_DEFAULT_INTERESTS = (
    "교육/체험",
    "서울형키즈카페",
    "공원/숲",
    "자연/과학",
    "전시/관람",
    "공연/문화행사",
    "농장체험",
    "역사",
    "기타",
)


def display_for_raw_category(raw_category: object) -> str:
    raw = str(raw_category or "").strip()
    for label, raw_values in CATEGORY_GROUPS.items():
        if raw in raw_values:
            return label
    return raw or "기타"


def available_interest_options(raw_categories: Iterable[object]) -> list[str]:
    available_raw = {str(category or "").strip() for category in raw_categories if str(category or "").strip()}
    grouped = [
        label
        for label, raw_values in CATEGORY_GROUPS.items()
        if any(raw in available_raw for raw in raw_values)
    ]
    return grouped or sorted(available_raw)


def raw_categories_for_interests(selected_interests: Iterable[object], raw_categories: Iterable[object]) -> tuple[str, ...]:
    available_raw = {str(category or "").strip() for category in raw_categories if str(category or "").strip()}
    selected = [str(interest or "").strip() for interest in selected_interests if str(interest or "").strip()]
    out: list[str] = []
    for interest in selected:
        raw_values = CATEGORY_GROUPS.get(interest, (interest,))
        for raw in raw_values:
            if raw in available_raw and raw not in out:
                out.append(raw)
    return tuple(out or sorted(available_raw))


def normalize_selected_interests(selected_values: Iterable[object], interest_options: Iterable[str]) -> list[str]:
    options = list(interest_options)
    option_set = set(options)
    normalized: list[str] = []
    for value in selected_values:
        display = display_for_raw_category(value)
        if display in option_set and display not in normalized:
            normalized.append(display)
    return normalized or [label for label in PARENT_DEFAULT_INTERESTS if label in option_set] or options
