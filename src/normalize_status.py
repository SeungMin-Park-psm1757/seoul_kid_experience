from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatusInfo:
    norm: str
    group: str
    available_now: bool
    is_full_or_closed: bool
    confidence: str


STATUS_GROUPS = {
    "available": "지금 신청 가능",
    "always_available": "신청 부담 낮음",
    "soon_open": "접수 예정",
    "closing_soon": "마감 임박",
    "full": "예약 마감",
    "closed": "접수 종료",
    "ended": "행사 종료",
    "unknown": "확인 필요",
}

AVAILABLE_NORMS = {"available", "always_available", "closing_soon"}
FULL_OR_CLOSED_NORMS = {"full", "closed", "ended"}


def normalize_reservation_status(raw_status: object) -> StatusInfo:
    text = str(raw_status or "").strip()
    compact = text.replace(" ", "")
    if not compact or compact.lower() in {"nan", "none", "null"}:
        return StatusInfo("unknown", STATUS_GROUPS["unknown"], False, False, "링크 확인 필요")

    if any(key in compact for key in ["행사종료", "이용종료"]):
        norm = "ended"
    elif any(key in compact for key in ["접수종료", "종료"]):
        norm = "closed"
    elif "마감임박" in compact:
        norm = "closing_soon"
    elif any(key in compact for key in ["접수마감", "예약마감", "정원마감", "마감"]):
        norm = "full"
    elif any(key in compact for key in ["접수예정", "예약예정", "예정"]):
        norm = "soon_open"
    elif any(key in compact for key in ["상시", "현장", "자유이용", "자유관람"]):
        norm = "always_available"
    elif any(key in compact for key in ["접수중", "예약가능", "이용가능", "신청가능"]):
        norm = "available"
    elif any(key in compact for key in ["참여가능성있음", "예약/참여링크확인"]):
        norm = "always_available"
    else:
        norm = "unknown"

    group = STATUS_GROUPS[norm]
    available_now = norm in AVAILABLE_NORMS
    is_full_or_closed = norm in FULL_OR_CLOSED_NORMS
    confidence = "API 확인" if norm != "unknown" else "링크 확인 필요"
    return StatusInfo(norm, group, available_now, is_full_or_closed, confidence)


def status_priority(norm: str) -> int:
    return {
        "available": 1,
        "always_available": 2,
        "closing_soon": 3,
        "soon_open": 4,
        "unknown": 5,
        "full": 6,
        "closed": 7,
        "ended": 8,
    }.get(str(norm), 5)


def is_available_norm(norm: object) -> bool:
    return str(norm) in AVAILABLE_NORMS


def is_closed_norm(norm: object) -> bool:
    return str(norm) in FULL_OR_CLOSED_NORMS
