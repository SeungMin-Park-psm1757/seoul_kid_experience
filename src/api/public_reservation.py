from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .cache import read_json_cache, read_service_registry, today_cache_file, write_json_cache
from .seoul_openapi import SeoulOpenApiError, fetch_all_rows

PUBLIC_RESERVATION_SERVICES = [
    "ListPublicReservation",
    "ListPublicReservationDetail",
    "ListPublicReservationCulture",
    "ListPublicReservationEducation",
    "ListPublicReservationSport",
    "ListPublicReservationInstitution",
    "ListPublicReservationAll",
]


def fetch_public_reservations(service_name: str, start: int = 1, end: int = 1000) -> list[dict[str, Any]]:
    if end - start + 1 > 1000:
        raise SeoulOpenApiError("서울 OpenAPI는 한 번에 최대 1,000건까지만 요청합니다.")
    return fetch_all_rows(service_name, max_rows=end, page_size=end - start + 1)[start - 1:end]


def _registered_public_services() -> list[str]:
    registry = read_service_registry()
    services = registry.get("public_reservation_services") or []
    return [str(service) for service in services if service] or PUBLIC_RESERVATION_SERVICES


def fetch_public_reservation_live(force_refresh: bool = False) -> pd.DataFrame:
    """서울시 공공서비스예약 API 실데이터를 수집해 DataFrame으로 반환한다."""
    payload = collect_public_reservations(force_refresh=force_refresh)
    return pd.DataFrame(payload.get("records", []))


def collect_public_reservations(
    services: list[str] | None = None,
    *,
    force_refresh: bool = False,
    page_size: int = 1000,
    max_records_per_service: int = 5000,
) -> dict[str, Any]:
    cache_path = None if force_refresh else today_cache_file("public_reservation_live")
    if cache_path:
        payload = read_json_cache(cache_path)
        payload["cache_path"] = str(cache_path)
        payload["from_cache"] = True
        return payload

    collected: list[dict[str, Any]] = []
    service_results: list[dict[str, Any]] = []
    errors: list[str] = []
    selected_services = services or _registered_public_services()
    for service_name in selected_services:
        service_rows: list[dict[str, Any]] = []
        try:
            rows = fetch_all_rows(service_name, max_rows=max_records_per_service, page_size=page_size)
            for row in rows:
                copied = dict(row)
                copied["_source_service"] = service_name
                copied["_api_collected_at"] = datetime.now().isoformat(timespec="seconds")
                service_rows.append(copied)
        except SeoulOpenApiError as exc:
            errors.append(str(exc))
            service_results.append({"service_name": service_name, "ok": False, "count": 0, "error": str(exc)})
            continue

        collected.extend(service_rows)
        service_results.append({"service_name": service_name, "ok": True, "count": len(service_rows), "error": ""})

    payload = {
        "data_mode": "api",
        "source": "public_reservation",
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "records": collected,
        "service_results": service_results,
        "errors": errors,
        "used_services": selected_services,
        "from_cache": False,
    }
    path = write_json_cache("public_reservation_live", payload)
    payload["cache_path"] = str(path)
    return payload
