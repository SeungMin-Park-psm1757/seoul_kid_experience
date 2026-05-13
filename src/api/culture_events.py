from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .cache import read_json_cache, read_service_registry, today_cache_file, write_json_cache
from .seoul_openapi import fetch_all_rows

CULTURE_EVENT_SERVICE = "culturalEventInfo"


def fetch_culture_events(start: int = 1, end: int = 1000) -> list[dict[str, Any]]:
    return fetch_all_rows(CULTURE_EVENT_SERVICE, max_rows=end, page_size=end - start + 1)[start - 1:end]


def _registered_culture_services() -> list[str]:
    registry = read_service_registry()
    services = registry.get("culture_event_services") or []
    return [str(service) for service in services if service] or [CULTURE_EVENT_SERVICE]


def fetch_culture_events_live(force_refresh: bool = False) -> pd.DataFrame:
    """서울시 문화행사 API 실데이터를 수집해 DataFrame으로 반환한다."""
    payload = collect_culture_events(force_refresh=force_refresh)
    return pd.DataFrame(payload.get("records", []))


def collect_culture_events(*, force_refresh: bool = False, page_size: int = 1000, max_records: int = 5000) -> dict[str, Any]:
    cache_path = None if force_refresh else today_cache_file("culture_events_live")
    if cache_path:
        payload = read_json_cache(cache_path)
        payload["cache_path"] = str(cache_path)
        payload["from_cache"] = True
        return payload

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    service_results: list[dict[str, Any]] = []
    selected_services = _registered_culture_services()
    for service_name in selected_services:
        service_rows: list[dict[str, Any]] = []
        try:
            for row in fetch_all_rows(service_name, max_rows=max_records, page_size=page_size):
                copied = dict(row)
                copied["_source_service"] = service_name
                copied["_api_collected_at"] = datetime.now().isoformat(timespec="seconds")
                service_rows.append(copied)
        except Exception as exc:
            errors.append(str(exc))
            service_results.append({"service_name": service_name, "ok": False, "count": 0, "error": str(exc)})
            continue
        rows.extend(service_rows)
        service_results.append({"service_name": service_name, "ok": True, "count": len(service_rows), "error": ""})

    payload = {
        "data_mode": "api",
        "source": "culture_events",
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "records": rows,
        "service_results": service_results,
        "errors": errors,
        "used_services": selected_services,
        "from_cache": False,
    }
    path = write_json_cache("culture_events_live", payload)
    payload["cache_path"] = str(path)
    return payload
