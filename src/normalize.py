from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .api.detail_page_parser import reservation_detail_url
from .config import DATA_PROCESSED, DATA_RAW, DATA_SAMPLE, UNIFIED_COLUMNS
from .normalize_status import normalize_reservation_status


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def read_json_with_fallback(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    if isinstance(payload, dict):
        for key in ("row", "records", "data", "items"):
            if isinstance(payload.get(key), list):
                return pd.DataFrame(payload[key])
        return pd.json_normalize(payload)
    return pd.DataFrame()


def _coalesce(row: pd.Series | dict[str, Any], keys: list[str], default: Any = "") -> Any:
    for key in keys:
        if key in row:
            value = row[key]
            if pd.notna(value) and str(value).strip() != "":
                return value
    return default


def parse_age_range(text: object) -> tuple[int, int, str]:
    raw = str(text or "").strip()
    numbers = [int(n) for n in re.findall(r"\d+", raw)]
    if not numbers:
        if any(key in raw for key in ["초등", "어린이", "아동", "가족"]):
            return 4, 12, raw or "어린이"
        return 0, 99, raw or "전체/확인 필요"
    if len(numbers) == 1:
        age = numbers[0]
        return age, age, raw
    return min(numbers[0], numbers[1]), max(numbers[0], numbers[1]), raw


def parse_fee(raw: object) -> int:
    text = str(raw or "")
    if any(key in text for key in ["무료", "무 료", "0원"]):
        return 0
    numbers = re.findall(r"\d[\d,]*", text)
    if not numbers:
        return 0
    return int(numbers[0].replace(",", ""))


def infer_fee_type(raw: object) -> str:
    fee = parse_fee(raw)
    text = str(raw or "")
    if fee == 0 or "무료" in text:
        return "무료"
    if fee <= 5000:
        return "저비용"
    return "유료"


def infer_indoor_outdoor(raw: object, category: object = "") -> str:
    text = f"{raw or ''} {category or ''}"
    if any(key in text for key in ["숲", "공원", "야외", "산책", "생태"]):
        return "실외"
    if any(key in text for key in ["실내", "도서관", "박물관", "미술관", "키즈카페", "공연", "센터"]):
        return "실내"
    return "확인 필요"


def _week_from_date(value: object) -> int:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return 0
    return int(ts.isocalendar().week)


def _district_from_text(row: pd.Series | dict[str, Any]) -> str:
    value = _coalesce(row, ["district", "GUNAME", "SIGUN", "자치구", "지역", "구", "?먯튂援?"], "")
    if value:
        return str(value).strip()
    address = str(_coalesce(row, ["address", "ADDR", "PLACE", "장소", "주소"], ""))
    match = re.search(r"([가-힣]+구)", address)
    return match.group(1) if match else "확인 필요"


def _reservation_url(row: pd.Series | dict[str, Any], fallback: str = "") -> tuple[str, str]:
    svcid = str(_coalesce(row, ["SVCID", "SVC_ID", "rsv_svc_id", "program_id"], "")).strip()
    detail = reservation_detail_url(svcid) if svcid else ""
    source_url = str(_coalesce(row, ["SVCURL", "HOMEPAGE", "ORG_LINK", "MAIN_IMG", "URL", "source_url", "detail_url"], fallback)).strip()
    if not source_url and detail:
        source_url = detail
    return source_url, detail or source_url


def ensure_unified_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "program_id" not in out.columns and "id" in out.columns:
        out["program_id"] = out["id"]
    if "id" not in out.columns and "program_id" in out.columns:
        out["id"] = out["program_id"]
    if "reservation_status_raw" not in out.columns and "status_label" in out.columns:
        out["reservation_status_raw"] = out["status_label"]

    for idx, row in out.iterrows():
        raw_status = row.get("reservation_status_raw", row.get("status_label", "확인 필요"))
        status = normalize_reservation_status(raw_status)
        if pd.isna(out.at[idx, "reservation_status_norm"]) if "reservation_status_norm" in out.columns else True:
            out.at[idx, "reservation_status_norm"] = status.norm
        if "availability_group" not in out.columns or pd.isna(out.at[idx, "availability_group"]):
            out.at[idx, "availability_group"] = status.group
        if "available_now" not in out.columns or pd.isna(out.at[idx, "available_now"]):
            out.at[idx, "available_now"] = status.available_now
        if "is_full_or_closed" not in out.columns or pd.isna(out.at[idx, "is_full_or_closed"]):
            out.at[idx, "is_full_or_closed"] = status.is_full_or_closed
        if "availability_confidence" not in out.columns or pd.isna(out.at[idx, "availability_confidence"]):
            out.at[idx, "availability_confidence"] = status.confidence

    defaults = {
        "source_service": "manual",
        "address": "",
        "lat": pd.NA,
        "lng": pd.NA,
        "target_text": "",
        "time_text": "확인 필요",
        "fee": 0,
        "fee_type": "확인 필요",
        "indoor_outdoor": "확인 필요",
        "date_match_level": "미계산",
        "source_url": "",
        "detail_url": "",
        "rule_summary": "공식 출처 확인 필요",
        "cancel_rule": "공식 출처 확인 필요",
        "no_show_rule": "공식 출처 확인 필요",
        "family_fit": "공식 출처 확인 필요",
        "preparation_note": "공식 출처 확인 필요",
        "data_confidence": "링크 확인 필요",
        "recommendation_reason": "필터 적용 후 자동 생성",
        "caution_note": "실제 예약 가능 여부와 상세 규정은 공식 출처에서 최종 확인하세요.",
        "last_api_update": datetime.now().isoformat(timespec="seconds"),
        "reservation_required": False,
    }
    for column, default in defaults.items():
        if column not in out.columns:
            out[column] = default
        else:
            out[column] = out[column].fillna(default)

    out["age_min"] = pd.to_numeric(out.get("age_min", 0), errors="coerce").fillna(0).astype(int)
    out["age_max"] = pd.to_numeric(out.get("age_max", 99), errors="coerce").fillna(99).astype(int)
    if "age_label" not in out.columns:
        out["age_label"] = out.apply(lambda r: f"{r['age_min']}-{r['age_max']}세", axis=1)
    out["fee"] = pd.to_numeric(out["fee"], errors="coerce").fillna(0).astype(int)
    out["week"] = out.get("week", out["date_start"].apply(_week_from_date) if "date_start" in out.columns else 0)
    out["week"] = pd.to_numeric(out["week"], errors="coerce").fillna(0).astype(int)
    out["status"] = out.get("status", out["availability_group"])
    out["status_label"] = out.get("status_label", out["availability_group"])

    for column in UNIFIED_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    return out.reindex(columns=UNIFIED_COLUMNS + [c for c in out.columns if c not in UNIFIED_COLUMNS])


def normalize_generic(df: pd.DataFrame, source_name: str = "manual") -> pd.DataFrame:
    rows = []
    for idx, row in df.iterrows():
        title = _coalesce(row, ["title", "SVCNM", "TITLE", "CODENAME", "프로그램명", "행사명", "서비스명", "?쒕퉬?ㅻ챸"], f"{source_name} 프로그램")
        category = _coalesce(row, ["category", "MINCLASSNM", "MAXCLASSNM", "CODENAME", "분류", "카테고리"], source_name)
        district = _district_from_text(row)
        venue = _coalesce(row, ["venue", "PLACENM", "PLACE", "FAC_NAME", "장소", "시설명", "?μ냼"], district)
        address = _coalesce(row, ["address", "ADDR", "ROAD_ADDR", "X", "주소"], "")
        target_text = _coalesce(row, ["target_text", "USETGTINFO", "USE_TRGT", "이용대상", "대상", "?댁슜???"], "")
        age_min, age_max, age_label = parse_age_range(target_text)
        fee_raw = _coalesce(row, ["fee", "PAYATNM", "USE_FEE", "이용요금", "요금", "?댁슜?붽툑"], "무료")
        date_start = _coalesce(row, ["date_start", "SVCOPNBGNDT", "RCPTBGNDT", "STRTDATE", "DATE", "시작일", "?쒖옉??"], "")
        date_end = _coalesce(row, ["date_end", "SVCOPNENDDT", "RCPTENDDT", "END_DATE", "ENDDATE", "종료일"], date_start)
        raw_status = _coalesce(row, ["reservation_status_raw", "SVCSTATNM", "status", "status_label", "상태", "?쒕퉬?ㅼ긽??"], "확인 필요")
        status = normalize_reservation_status(raw_status)
        source_url, detail_url = _reservation_url(row)
        program_id = str(_coalesce(row, ["program_id", "SVCID", "SVC_ID", "id"], f"{source_name}-{idx + 1}"))

        rows.append({
            "program_id": program_id,
            "source": source_name,
            "source_service": source_name,
            "title": title,
            "category": category,
            "district": district,
            "venue": venue,
            "address": address,
            "lat": _coalesce(row, ["lat", "LAT", "Y", "위도"], pd.NA),
            "lng": _coalesce(row, ["lng", "LNG", "X", "경도"], pd.NA),
            "age_min": age_min,
            "age_max": age_max,
            "age_label": age_label,
            "target_text": target_text,
            "date_start": date_start,
            "date_end": date_end,
            "time_text": _coalesce(row, ["time_text", "SVCOPNTIME", "TIME", "시간"], "확인 필요"),
            "fee": parse_fee(fee_raw),
            "fee_type": infer_fee_type(fee_raw),
            "indoor_outdoor": infer_indoor_outdoor(venue, category),
            "reservation_status_raw": raw_status,
            "reservation_status_norm": status.norm,
            "availability_group": status.group,
            "available_now": status.available_now,
            "is_full_or_closed": status.is_full_or_closed,
            "date_match_level": "미계산",
            "source_url": source_url,
            "detail_url": detail_url,
            "rule_summary": _coalesce(row, ["rule_summary", "NOTICE", "DTLCONT", "안내", "주의사항"], "공식 출처 확인 필요"),
            "cancel_rule": "공식 출처 확인 필요",
            "no_show_rule": "공식 출처 확인 필요",
            "family_fit": "공식 출처 확인 필요",
            "preparation_note": "공식 출처 확인 필요",
            "data_confidence": "원천 파일 매핑",
            "availability_confidence": status.confidence,
            "recommendation_reason": "필터 적용 후 자동 생성",
            "caution_note": "실제 예약 가능 여부와 상세 규정은 공식 출처에서 최종 확인하세요.",
            "last_api_update": datetime.now().isoformat(timespec="seconds"),
            "id": program_id,
            "week": _week_from_date(date_start),
            "status": status.group,
            "status_label": status.group,
            "reservation_required": bool(source_url),
        })
    return ensure_unified_columns(pd.DataFrame(rows))


def load_sample_unified() -> pd.DataFrame:
    path = DATA_SAMPLE / "unified_programs_sample.csv"
    if not path.exists():
        from .sample_data import save_sample_data
        save_sample_data()
    return ensure_unified_columns(pd.read_csv(path))


def load_sample_population() -> pd.DataFrame:
    path = DATA_SAMPLE / "district_child_population_sample.csv"
    if not path.exists():
        from .sample_data import save_sample_data
        save_sample_data()
    return pd.read_csv(path)


def load_and_normalize_raw(raw_dir: Path = DATA_RAW) -> pd.DataFrame:
    frames = []
    for path in raw_dir.glob("*"):
        if path.name == ".gitkeep" or path.suffix.lower() not in {".csv", ".json"}:
            continue
        source_name = path.stem
        df = read_csv_with_fallback(path) if path.suffix.lower() == ".csv" else read_json_with_fallback(path)
        frames.append(normalize_generic(df, source_name=source_name))
    if not frames:
        raise FileNotFoundError("data/raw에 CSV 또는 JSON 파일이 없습니다. --sample 옵션을 사용하거나 원본 파일을 넣어주세요.")
    return ensure_unified_columns(pd.concat(frames, ignore_index=True))


def save_processed_unified(df: pd.DataFrame, out_dir: Path = DATA_PROCESSED) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "unified_programs.csv"
    ensure_unified_columns(df).to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path
