from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_CACHE = PROJECT_ROOT / "data" / "cache"
DATA_REFERENCE = PROJECT_ROOT / "data" / "reference"
DATA_SAMPLE = PROJECT_ROOT / "data" / "sample"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
PPT_ASSETS_DIR = PROJECT_ROOT / "outputs" / "ppt_assets"
SEOUL_GEOJSON = DATA_REFERENCE / "seoul_municipalities_geo_simple.json"

SEOUL_DISTRICTS = [
    "종로구", "중구", "용산구", "성동구", "광진구",
    "동대문구", "중랑구", "성북구", "강북구", "도봉구",
    "노원구", "은평구", "서대문구", "마포구", "양천구",
    "강서구", "구로구", "금천구", "영등포구", "동작구",
    "관악구", "서초구", "강남구", "송파구", "강동구",
]

AGE_GROUPS = {
    "4-6세": (4, 6),
    "7-9세": (7, 9),
    "10-12세": (10, 12),
}

NEIGHBOR_DISTRICTS = {
    "종로구": ["중구", "서대문구", "성북구"],
    "중구": ["종로구", "용산구", "성동구"],
    "용산구": ["중구", "마포구", "동작구", "서초구"],
    "성동구": ["중구", "광진구", "동대문구", "강남구"],
    "광진구": ["성동구", "동대문구", "송파구", "강동구"],
    "동대문구": ["성북구", "중랑구", "광진구", "성동구"],
    "중랑구": ["동대문구", "노원구", "광진구"],
    "성북구": ["종로구", "강북구", "동대문구"],
    "강북구": ["도봉구", "노원구", "성북구"],
    "도봉구": ["강북구", "노원구"],
    "노원구": ["도봉구", "강북구", "중랑구"],
    "은평구": ["서대문구", "마포구"],
    "서대문구": ["은평구", "종로구", "마포구"],
    "마포구": ["은평구", "서대문구", "용산구", "영등포구", "강서구"],
    "양천구": ["강서구", "구로구", "영등포구"],
    "강서구": ["양천구", "마포구", "구로구"],
    "구로구": ["양천구", "금천구", "영등포구", "강서구"],
    "금천구": ["구로구", "관악구"],
    "영등포구": ["마포구", "양천구", "구로구", "동작구"],
    "동작구": ["영등포구", "관악구", "서초구", "용산구"],
    "관악구": ["동작구", "금천구", "서초구"],
    "서초구": ["강남구", "동작구", "관악구", "용산구"],
    "강남구": ["서초구", "송파구", "성동구"],
    "송파구": ["강남구", "강동구", "광진구"],
    "강동구": ["송파구", "광진구"],
}

DISTRICT_TILE_POSITIONS = {
    "은평구": (0, 1), "도봉구": (0, 4), "노원구": (0, 5),
    "강북구": (1, 3), "중랑구": (1, 6),
    "서대문구": (2, 1), "종로구": (2, 3), "성북구": (2, 4), "동대문구": (2, 5),
    "마포구": (3, 0), "중구": (3, 3), "성동구": (3, 5), "광진구": (3, 6),
    "강서구": (4, 0), "용산구": (4, 3), "송파구": (4, 6), "강동구": (4, 7),
    "양천구": (5, 1), "영등포구": (5, 2), "동작구": (5, 3), "서초구": (5, 5), "강남구": (5, 6),
    "구로구": (6, 2), "금천구": (6, 3), "관악구": (6, 4),
}

UNIFIED_COLUMNS = [
    "program_id", "source", "source_service", "title", "category", "district", "venue", "address",
    "lat", "lng", "age_min", "age_max", "age_label", "target_text", "date_start", "date_end",
    "time_text", "fee", "fee_type", "indoor_outdoor", "reservation_status_raw",
    "reservation_status_norm", "availability_group", "available_now", "is_full_or_closed",
    "date_match_level", "source_url", "detail_url", "rule_summary", "cancel_rule", "no_show_rule",
    "family_fit", "preparation_note", "data_confidence", "availability_confidence",
    "recommendation_reason", "caution_note", "last_api_update",
    "target_audience_raw", "target_audience_norm", "target_audience_confidence",
    "child_suitability", "child_suitability_reason", "hard_filter_reason",
    "weekday_raw", "weekday_norm", "is_weekend_available", "is_weekday_only",
    "date_weekday_match", "date_filter_reason",
    "alternative_type", "walk_in_likelihood", "reservation_friction", "backup_reason",
    "reservation_difficulty", "reservation_difficulty_reason", "difficulty_confidence",
    "historical_pattern_available",
    # Backward-compatible aliases used by older metrics/tests.
    "id", "week", "status", "status_label", "reservation_required",
]
