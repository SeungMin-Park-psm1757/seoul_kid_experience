from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from .config import load_api_config

BASE_URL = "http://openapi.seoul.go.kr:8088/{key}/json/{service}/{start}/{end}/"
MAX_PAGE_SIZE = 1000


class SeoulOpenApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class SeoulApiPage:
    service_name: str
    rows: list[dict[str, Any]]
    total_count: int | None
    raw: dict[str, Any]


def _result_message(payload: dict[str, Any]) -> str:
    result = payload.get("RESULT")
    if isinstance(result, dict):
        message = result.get("MESSAGE") or result.get("CODE") or result
        return str(message)
    for value in payload.values():
        if isinstance(value, dict) and isinstance(value.get("RESULT"), dict):
            message = value["RESULT"].get("MESSAGE") or value["RESULT"].get("CODE") or value["RESULT"]
            return str(message)
    return "응답에서 row를 찾지 못했습니다."


def detect_service_root(payload: dict[str, Any], service_name: str | None = None) -> tuple[str, dict[str, Any]]:
    if service_name and isinstance(payload.get(service_name), dict):
        return service_name, payload[service_name]
    for key, value in payload.items():
        if isinstance(value, dict) and ("row" in value or "list_total_count" in value):
            return key, value
    if "RESULT" in payload:
        raise SeoulOpenApiError(_result_message(payload))
    raise SeoulOpenApiError("응답 루트 키를 자동 탐지하지 못했습니다.")


def extract_rows(response_json: dict[str, Any], service_name: str) -> list[dict[str, Any]]:
    """응답에서 row 리스트를 안전하게 추출한다. 루트 키가 다르면 자동 탐지한다."""
    _, body = detect_service_root(response_json, service_name)
    rows = body.get("row") or []
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        raise SeoulOpenApiError(f"{service_name} row 형식이 리스트가 아닙니다.")
    return [row for row in rows if isinstance(row, dict)]


def _extract_payload(service_name: str, payload: dict[str, Any]) -> SeoulApiPage:
    root_key, body = detect_service_root(payload, service_name)
    rows = extract_rows(payload, service_name)
    total = body.get("list_total_count")
    try:
        total_count = int(total) if total is not None else None
    except (TypeError, ValueError):
        total_count = None
    return SeoulApiPage(service_name=root_key, rows=list(rows), total_count=total_count, raw=payload)


def call_seoul_openapi(service_name: str, start: int = 1, end: int = 1000, extra_path: str | None = None, api_key: str | None = None, timeout: int = 20) -> dict[str, Any]:
    """서울 OpenAPI를 호출하고 JSON dict를 반환한다. 키는 절대 로그에 출력하지 않는다."""
    if start < 1 or end < start:
        raise SeoulOpenApiError("OpenAPI 호출 범위가 올바르지 않습니다.")
    if end - start + 1 > MAX_PAGE_SIZE:
        raise SeoulOpenApiError("서울 OpenAPI는 한 번에 최대 1,000건까지만 요청합니다.")
    config = load_api_config()
    key = api_key or config.seoul_openapi_key
    if not key:
        raise SeoulOpenApiError("SEOUL_OPENAPI_KEY가 없습니다.")
    url = BASE_URL.format(key=quote(key), service=quote(service_name), start=start, end=end)
    if extra_path:
        url = url.rstrip("/") + "/" + "/".join(quote(part) for part in extra_path.strip("/").split("/") if part) + "/"
    try:
        with urlopen(url, timeout=timeout) as response:
            text = response.read().decode("utf-8")
    except HTTPError as exc:
        raise SeoulOpenApiError(f"{service_name} HTTP 오류: {exc.code}") from exc
    except URLError as exc:
        raise SeoulOpenApiError(f"{service_name} 네트워크 오류: {exc.reason}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SeoulOpenApiError(f"{service_name} JSON 파싱 실패") from exc
    if not isinstance(payload, dict):
        raise SeoulOpenApiError(f"{service_name} JSON 응답이 객체가 아닙니다.")
    return payload


def fetch_service_page(service_name: str, start: int = 1, end: int = 1000, api_key: str | None = None, timeout: int = 20) -> SeoulApiPage:
    payload = call_seoul_openapi(service_name, start=start, end=end, api_key=api_key, timeout=timeout)
    return _extract_payload(service_name, payload)


def fetch_all_rows(service_name: str, max_rows: int = 5000, page_size: int = 1000) -> list[dict[str, Any]]:
    """1,000건 단위로 페이징 호출한다."""
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    rows: list[dict[str, Any]] = []
    start = 1
    total_count: int | None = None
    while start <= max_rows:
        end = min(start + page_size - 1, max_rows)
        page = fetch_service_page(service_name, start=start, end=end)
        if total_count is None:
            total_count = page.total_count
        if not page.rows:
            break
        rows.extend(page.rows)
        if total_count is not None and end >= total_count:
            break
        if len(page.rows) < page_size:
            break
        start = end + 1
    return rows[:max_rows]
