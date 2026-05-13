from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime

import pandas as pd

from .api.config import load_api_config
from .api.culture_events import collect_culture_events
from .api.detail_page_parser import parse_public_detail_page
from .api.public_reservation import collect_public_reservations
from .config import DATA_PROCESSED, FIGURES_DIR, PROJECT_ROOT
from .curation_rules import enrich_curation_fields
from .metrics import add_district_types, compute_district_age_metrics, compute_weekly_choice_metrics
from .normalize import (
    ensure_unified_columns,
    infer_fee_type,
    infer_indoor_outdoor,
    load_and_normalize_raw,
    load_sample_population,
    load_sample_unified,
    parse_age_range,
    parse_fee,
    save_processed_unified,
)
from .normalize_status import normalize_reservation_status
from .sample_data import save_sample_data
from .visualize import save_all_visualizations

META_PATH = DATA_PROCESSED / "data_collection_meta.json"


def _first(row: dict, keys: list[str], default: str = ""):
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return value
    return default


def _clean_text(value: object, limit: int = 260) -> str:
    text = str(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&amp;|&lt;|&gt;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "공식 출처 확인 필요"
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def _week(value) -> int:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return 0
    return int(ts.isocalendar().week)


def _source_url_from_reservation(row: dict) -> tuple[str, str]:
    svcid = str(_first(row, ["SVCID", "SVC_ID", "program_id"], "")).strip()
    detail_url = f"https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id={svcid}" if svcid else ""
    source_url = str(_first(row, ["SVCURL", "URL", "DETAIL_URL"], detail_url)).strip()
    return source_url or detail_url, detail_url or source_url


def _raw_prefix(row: dict) -> dict:
    keep = ["SVCID", "SVCNM", "MINCLASSNM", "MAXCLASSNM", "PLACENM", "SVCSTATNM", "RCPTBGNDT", "RCPTENDDT", "SVCOPNBGNDT", "SVCOPNENDDT", "X", "Y", "GUNAME"]
    return {f"raw_{key}": row.get(key, "") for key in keep if key in row}


def normalize_public_reservation_records(records: list[dict], *, parse_details: bool = False, detail_limit: int = 20) -> pd.DataFrame:
    rows = []
    now = datetime.now().isoformat(timespec="seconds")
    for idx, row in enumerate(records):
        title = _first(row, ["SVCNM", "TITLE", "서비스명"], "")
        if not str(title).strip():
            continue
        category = _first(row, ["MINCLASSNM", "MAXCLASSNM", "SVC_CLASS", "CATEGORY"], "공공체험")
        district = _first(row, ["GUNAME", "AREANM", "SIGUN", "자치구"], "확인 필요")
        venue = _first(row, ["PLACENM", "PLACE", "FAC_NAME"], district)
        address = _first(row, ["ADDR", "ROAD_ADDR"], "")
        target_text = _first(row, ["USETGTINFO", "USE_TRGT", "TARGET"], "어린이/가족")
        age_min, age_max, age_label = parse_age_range(target_text)
        fee_raw = _first(row, ["PAYATNM", "USE_FEE", "SVC_FEE"], "확인 필요")
        raw_status = _first(row, ["SVCSTATNM", "STATUS"], "확인 필요")
        status = normalize_reservation_status(raw_status)
        source_url, detail_url = _source_url_from_reservation(row)
        program_id = str(_first(row, ["SVCID", "SVC_ID"], f"reservation-{idx + 1}"))

        detail = {}
        if parse_details and detail_url and idx < detail_limit:
            detail = parse_public_detail_page(detail_url)

        base = {
            "program_id": program_id,
            "source": "공공서비스예약",
            "source_service": str(row.get("_source_service", "ListPublicReservation")),
            "title": title,
            "category": category,
            "district": district,
            "venue": venue,
            "address": address,
            "lat": _first(row, ["Y", "LAT"], pd.NA),
            "lng": _first(row, ["X", "LNG"], pd.NA),
            "age_min": age_min,
            "age_max": age_max,
            "age_label": age_label,
            "target_text": target_text,
            "date_start": _first(row, ["SVCOPNBGNDT", "RCPTBGNDT", "STRTDATE"], ""),
            "date_end": _first(row, ["SVCOPNENDDT", "RCPTENDDT", "ENDDATE"], ""),
            "time_text": _first(row, ["V_MIN", "SVCOPNTIME", "TIME"], "확인 필요"),
            "fee": parse_fee(fee_raw),
            "fee_type": infer_fee_type(fee_raw),
            "indoor_outdoor": infer_indoor_outdoor(f"{venue} {title}", category),
            "reservation_status_raw": raw_status,
            "reservation_status_norm": status.norm,
            "availability_group": status.group,
            "available_now": status.available_now,
            "is_full_or_closed": status.is_full_or_closed,
            "date_match_level": "미계산",
            "source_url": source_url,
            "detail_url": detail_url,
            "rule_summary": _clean_text(_first(row, ["DTLCONT", "NOTICE"], "공식 예약 페이지에서 회차별 규정 확인 필요")),
            "cancel_rule": detail.get("cancel_rule", "공식 예약 페이지에서 취소 규정 확인 필요"),
            "no_show_rule": detail.get("no_show_rule", "공식 예약 페이지에서 노쇼/미참여 규정 확인 필요"),
            "family_fit": detail.get("family_fit", "보호자 동반 여부 확인 필요"),
            "preparation_note": detail.get("preparation_note", "준비물 확인 필요"),
            "data_confidence": "API 확인",
            "availability_confidence": detail.get("availability_confidence", status.confidence),
            "recommendation_reason": "필터 적용 후 자동 생성",
            "caution_note": "회차별 잔여석과 신청 가능 여부는 공식 예약 페이지에서 최종 확인하세요.",
            "last_api_update": str(row.get("_api_collected_at", now)),
            "id": program_id,
            "week": _week(_first(row, ["SVCOPNBGNDT", "RCPTBGNDT"], "")),
            "status": status.group,
            "status_label": status.group,
            "reservation_required": True,
        }
        base.update(_raw_prefix(row))
        rows.append(base)
    return ensure_unified_columns(pd.DataFrame(rows))


def _culture_status(row: dict) -> tuple[str, str]:
    end = pd.to_datetime(_first(row, ["END_DATE", "ENDDATE", "DATE"], ""), errors="coerce")
    now = pd.Timestamp.now().normalize()
    link = str(_first(row, ["ORG_LINK", "HOMEPAGE", "URL"], "")).strip()
    fee_raw = str(_first(row, ["USE_FEE", "USE_TRGT", "FEE"], ""))
    if pd.notna(end) and end.normalize() < now:
        return "행사종료", "ended"
    if link:
        return "예약/참여 링크 확인", "always_available"
    if "무료" in fee_raw and (pd.isna(end) or end.normalize() >= now):
        return "참여 가능성 있음", "always_available"
    return "확인 필요", "unknown"


def normalize_culture_event_records(records: list[dict]) -> pd.DataFrame:
    rows = []
    now = datetime.now().isoformat(timespec="seconds")
    for idx, row in enumerate(records):
        raw_status, _ = _culture_status(row)
        status = normalize_reservation_status(raw_status)
        title = _first(row, ["TITLE", "CODENAME", "행사명"], "")
        if not str(title).strip():
            continue
        category = _first(row, ["CODENAME", "MAIN_IMG", "분류"], "문화행사")
        target_text = _first(row, ["USE_TRGT", "이용대상"], "어린이/가족")
        age_min, age_max, age_label = parse_age_range(target_text)
        fee_raw = _first(row, ["USE_FEE", "이용요금"], "확인 필요")
        source_url = _first(row, ["ORG_LINK", "HOMEPAGE", "URL"], "")
        program_id = f"culture-{_first(row, ['TITLE'], idx + 1)}"
        rows.append({
            "program_id": program_id,
            "source": "서울문화행사",
            "source_service": str(row.get("_source_service", "culturalEventInfo")),
            "title": title,
            "category": category,
            "district": _first(row, ["GUNAME", "SIGNGU", "자치구"], "확인 필요"),
            "venue": _first(row, ["PLACE", "장소"], "확인 필요"),
            "address": _first(row, ["PLACE", "ADDR"], ""),
            "lat": _first(row, ["LAT", "Y"], pd.NA),
            "lng": _first(row, ["LOT", "LNG", "X"], pd.NA),
            "age_min": age_min,
            "age_max": age_max,
            "age_label": age_label,
            "target_text": target_text,
            "date_start": _first(row, ["STRTDATE", "START_DATE", "DATE"], ""),
            "date_end": _first(row, ["END_DATE", "ENDDATE"], ""),
            "time_text": _first(row, ["TIME", "행사시간"], "확인 필요"),
            "fee": parse_fee(fee_raw),
            "fee_type": infer_fee_type(fee_raw),
            "indoor_outdoor": infer_indoor_outdoor(_first(row, ["PLACE"], ""), category),
            "reservation_status_raw": raw_status,
            "reservation_status_norm": status.norm,
            "availability_group": status.group,
            "available_now": status.available_now,
            "is_full_or_closed": status.is_full_or_closed,
            "date_match_level": "미계산",
            "source_url": source_url,
            "detail_url": source_url,
            "rule_summary": "문화행사는 예약상태가 제공되지 않을 수 있어 공식 링크 확인 필요",
            "cancel_rule": "공식 출처 확인 필요",
            "no_show_rule": "공식 출처 확인 필요",
            "family_fit": "이용대상 문구 확인 필요",
            "preparation_note": "공식 출처 확인 필요",
            "data_confidence": "API 확인",
            "availability_confidence": status.confidence,
            "recommendation_reason": "필터 적용 후 자동 생성",
            "caution_note": "문화행사는 회차별 예약 가능 여부가 없을 수 있으므로 공식 링크에서 최종 확인하세요.",
            "last_api_update": str(row.get("_api_collected_at", now)),
            "id": program_id,
            "week": _week(_first(row, ["STRTDATE", "START_DATE"], "")),
            "status": status.group,
            "status_label": status.group,
            "reservation_required": bool(source_url),
        })
    out = ensure_unified_columns(pd.DataFrame(rows))
    for column in ["TITLE", "CODENAME", "GUNAME", "PLACE", "STRTDATE", "END_DATE", "USE_TRGT", "USE_FEE", "ORG_LINK"]:
        raw_col = f"raw_{column}"
        if raw_col not in out.columns:
            values = [record.get(column, "") for record in records[:len(out)]]
            out[raw_col] = values + [""] * max(0, len(out) - len(values))
    return out


def collect_api_programs(*, force_refresh: bool = False, parse_details: bool = False) -> tuple[pd.DataFrame, dict]:
    reservation_payload = collect_public_reservations(force_refresh=force_refresh)
    culture_payload = collect_culture_events(force_refresh=force_refresh)
    reservation_df = normalize_public_reservation_records(reservation_payload.get("records", []), parse_details=parse_details)
    culture_df = normalize_culture_event_records(culture_payload.get("records", []))
    programs = ensure_unified_columns(pd.concat([reservation_df, culture_df], ignore_index=True))
    meta = {
        "data_mode": "api",
        "last_api_call": datetime.now().isoformat(timespec="seconds"),
        "public_reservation_count": int(len(reservation_df)),
        "culture_event_count": int(len(culture_df)),
        "public_reservation_services": reservation_payload.get("service_results", []),
        "culture_event_services": culture_payload.get("service_results", []),
        "cache_paths": [reservation_payload.get("cache_path", ""), culture_payload.get("cache_path", "")],
        "errors": reservation_payload.get("errors", []) + culture_payload.get("errors", []),
    }
    return programs, meta


def write_collection_meta(meta: dict) -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _rate(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    return float(series.mean() * 100)


def add_quality_meta(meta: dict, programs: pd.DataFrame) -> dict:
    out = dict(meta)
    sample_like_count = int(programs.get("data_confidence", pd.Series("", index=programs.index)).astype(str).str.contains("샘플", na=False).sum())
    api_like_count = int(programs.get("data_confidence", pd.Series("", index=programs.index)).astype(str).str.contains("API", na=False).sum())
    if sample_like_count and api_like_count:
        out["data_mode"] = "mixed_error"
        out.setdefault("errors", []).append("샘플 데이터와 API 데이터가 섞였습니다. 캐시를 비우고 다시 수집하세요.")
    out.update({
        "record_count": int(len(programs)),
        "sample_like_count": sample_like_count,
        "api_like_count": api_like_count,
        "age_parse_success_rate": _rate((programs["age_min"].notna()) & (programs["age_max"].notna())),
        "date_parse_success_rate": _rate(pd.to_datetime(programs["date_start"], errors="coerce").notna()),
        "coordinate_rate": _rate(programs["lat"].notna() & programs["lng"].notna()),
        "status_known_rate": _rate(~programs["reservation_status_norm"].isin(["unknown"])),
        "detail_parse_success_rate": _rate(programs.get("detail_parse_status", pd.Series("", index=programs.index)).eq("ok")) if len(programs) else 0.0,
        "closed_or_full_count": int(programs["is_full_or_closed"].fillna(False).astype(bool).sum()),
        "official_link_rate": _rate(programs["source_url"].fillna("").astype(str).str.len().gt(0)),
    })
    return out


def write_data_quality_summary(programs: pd.DataFrame, meta: dict) -> pd.DataFrame:
    summary = pd.DataFrame([
        {"metric": "data_mode", "value": meta.get("data_mode", "")},
        {"metric": "last_api_call", "value": meta.get("last_api_call", "")},
        {"metric": "public_reservation_count", "value": meta.get("public_reservation_count", 0)},
        {"metric": "culture_event_count", "value": meta.get("culture_event_count", 0)},
        {"metric": "record_count", "value": len(programs)},
        {"metric": "age_parse_success_rate", "value": meta.get("age_parse_success_rate", 0)},
        {"metric": "date_parse_success_rate", "value": meta.get("date_parse_success_rate", 0)},
        {"metric": "coordinate_rate", "value": meta.get("coordinate_rate", 0)},
        {"metric": "status_known_rate", "value": meta.get("status_known_rate", 0)},
        {"metric": "official_link_rate", "value": meta.get("official_link_rate", 0)},
        {"metric": "closed_or_full_count", "value": meta.get("closed_or_full_count", 0)},
    ])
    summary.to_csv(DATA_PROCESSED / "data_quality_summary.csv", index=False, encoding="utf-8-sig")
    return summary


def create_api_snapshot(programs: pd.DataFrame, metrics: pd.DataFrame, quality: pd.DataFrame, meta: dict) -> None:
    if meta.get("data_mode") != "api":
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    snapshot_dir = PROJECT_ROOT / "data" / "snapshots" / f"api_snapshot_{stamp}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    programs.to_csv(snapshot_dir / "unified_programs.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(snapshot_dir / "policy_metrics.csv", index=False, encoding="utf-8-sig")
    quality.to_csv(snapshot_dir / "data_quality_summary.csv", index=False, encoding="utf-8-sig")
    source_meta = DATA_PROCESSED / "data_collection_meta.json"
    if source_meta.exists():
        shutil.copy2(source_meta, snapshot_dir / "data_collection_meta.json")
    representative = metrics[metrics["age_group"].eq("7-9세")].copy()
    low_choice = ", ".join(representative.sort_values("choice_index").head(3)["district"]) if not representative.empty else "확인 필요"
    low_planb = ", ".join(representative.sort_values("planb_index").head(3)["district"]) if not representative.empty else "확인 필요"
    closed = ", ".join(representative.sort_values("closed_count", ascending=False).head(3)["district"]) if not representative.empty else "확인 필요"
    (snapshot_dir / "README.md").write_text(
        "# API 수집 스냅샷\n\n"
        f"- 수집 시각: {meta.get('last_api_call', '')}\n"
        f"- 사용 API: 공공서비스예약, 서울문화행사\n"
        f"- 공공서비스예약 수집 건수: {meta.get('public_reservation_count', 0):,}건\n"
        f"- 문화행사 수집 건수: {meta.get('culture_event_count', 0):,}건\n"
        f"- 통합 후보 수: {len(programs):,}건\n\n"
        "## 주요 인사이트 3개\n\n"
        f"1. 7~9세 기준 선택가능도 하위 자치구: {low_choice}\n"
        f"2. 7~9세 기준 플랜B 부족 자치구: {low_planb}\n"
        f"3. 마감 또는 확인 필요 후보가 많은 자치구: {closed}\n\n"
        "## 한계\n\n"
        "본 결과물은 서울시 OpenAPI와 공개 출처 링크를 기반으로 후보를 탐색하는 시각화 도구입니다. "
        "실제 회차별 잔여석과 최종 신청 가능 여부는 공식 예약/출처 페이지에서 확인해야 합니다.\n",
        encoding="utf-8",
    )


def write_summary_docs(metrics: pd.DataFrame, weekly: pd.DataFrame, sample: bool) -> None:
    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    representative_age = "7-9세"
    m = metrics[metrics["age_group"] == representative_age].copy()
    top_closed = m.sort_values("closed_count", ascending=False).head(5)
    bottom_planb = m.sort_values("planb_index").head(5)
    (docs_dir / "metrics_result_summary.md").write_text(
        "# 지표 결과 요약\n\n"
        f"데이터 모드: {'샘플' if sample else 'API/원천 데이터'}\n\n"
        f"- 선택가능도 하위 자치구: {', '.join(m.sort_values('choice_index').head(3)['district'])}\n"
        f"- 플랜B 부족 자치구: {', '.join(bottom_planb.head(3)['district'])}\n"
        f"- 마감/예약불가 후보가 많은 자치구: {', '.join(top_closed.head(3)['district'])}\n\n"
        "이 지표는 공개 데이터 기반 탐색 지표이며, 회차별 실제 잔여석을 보장하지 않습니다.\n",
        encoding="utf-8",
    )


def build(sample: bool = False, *, force_refresh: bool = False, parse_details: bool = False) -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    config = load_api_config()
    meta: dict

    if sample:
        save_sample_data()
        programs = load_sample_unified()
        meta = {
            "data_mode": "sample",
            "last_api_call": "",
            "public_reservation_count": 0,
            "culture_event_count": 0,
            "errors": ["사용자가 샘플 빌드를 선택했습니다."],
        }
    elif config.has_seoul_key:
        try:
            programs, meta = collect_api_programs(force_refresh=force_refresh, parse_details=parse_details)
            if programs.empty:
                raise RuntimeError("API 수집 결과가 비어 있습니다.")
        except Exception as exc:
            save_sample_data()
            programs = load_sample_unified()
            meta = {
                "data_mode": "sample",
                "last_api_call": datetime.now().isoformat(timespec="seconds"),
                "public_reservation_count": 0,
                "culture_event_count": 0,
                "errors": [f"API 수집 실패로 샘플 fallback 사용: {exc}"],
            }
    else:
        save_sample_data()
        programs = load_sample_unified()
        meta = {
            "data_mode": "sample",
            "last_api_call": "",
            "public_reservation_count": 0,
            "culture_event_count": 0,
            "errors": ["SEOUL_OPENAPI_KEY가 없어 샘플 데이터 fallback을 사용했습니다."],
        }

    programs = ensure_unified_columns(enrich_curation_fields(programs))
    save_processed_unified(programs)
    if meta.get("data_mode") == "api":
        programs.to_csv(DATA_PROCESSED / "unified_programs_live.csv", index=False, encoding="utf-8-sig")
    population = load_sample_population()
    weekly = compute_weekly_choice_metrics(programs, population)
    metrics = add_district_types(compute_district_age_metrics(programs, population))
    weekly_path = DATA_PROCESSED / "weekly_choice_metrics.csv"
    metrics_path = DATA_PROCESSED / "district_age_metrics.csv"
    weekly.to_csv(weekly_path, index=False, encoding="utf-8-sig")
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    try:
        save_all_visualizations(weekly, metrics)
    except Exception as exc:
        meta.setdefault("errors", []).append(f"PPT용 정책 이미지 생성 실패: {exc}")
    meta = add_quality_meta(meta, programs)
    write_summary_docs(metrics, weekly, sample=meta.get("data_mode") == "sample")
    write_collection_meta(meta)
    quality = write_data_quality_summary(programs, meta)
    create_api_snapshot(programs, metrics, quality, meta)

    print("Build complete.")
    print(f"- data_mode: {meta.get('data_mode')}")
    print(f"- programs: {DATA_PROCESSED / 'unified_programs.csv'}")
    print(f"- weekly: {weekly_path}")
    print(f"- metrics: {metrics_path}")
    print(f"- meta: {META_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="Generate and use sample data")
    parser.add_argument("--force-refresh", action="store_true", help="Ignore same-day API cache")
    parser.add_argument("--parse-details", action="store_true", help="Best-effort parse a limited number of public detail pages")
    args = parser.parse_args()
    build(sample=args.sample, force_refresh=args.force_refresh, parse_details=args.parse_details)


if __name__ == "__main__":
    main()
