from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.cache import write_service_registry
from src.api.config import load_api_config
from src.api.seoul_openapi import SeoulOpenApiError, call_seoul_openapi, detect_service_root, extract_rows

PUBLIC_RESERVATION_CANDIDATES = [
    "ListPublicReservation",
    "ListPublicReservationDetail",
    "ListPublicReservationCulture",
    "ListPublicReservationEducation",
    "ListPublicReservationSport",
    "ListPublicReservationInstitution",
    "ListPublicReservationAll",
]

CULTURE_EVENT_CANDIDATES = ["culturalEventInfo"]


def _result_info(payload: dict[str, Any], root_key: str | None = None) -> tuple[str, str]:
    result = payload.get("RESULT")
    if not isinstance(result, dict) and root_key and isinstance(payload.get(root_key), dict):
        result = payload[root_key].get("RESULT")
    if isinstance(result, dict):
        return str(result.get("CODE", "")), str(result.get("MESSAGE", ""))
    return "", ""


def _field_sample(rows: list[dict[str, Any]], limit: int = 12) -> str:
    if not rows:
        return ""
    return ", ".join(list(rows[0].keys())[:limit])


def check_service(service_name: str, group: str) -> dict[str, Any]:
    checked_at = datetime.now().isoformat(timespec="seconds")
    try:
        payload = call_seoul_openapi(service_name, start=1, end=5, timeout=20)
        root_key, _ = detect_service_root(payload, service_name)
        rows = extract_rows(payload, service_name)
        code, message = _result_info(payload, root_key)
        return {
            "group": group,
            "service_name": service_name,
            "ok": True,
            "root_key": root_key,
            "row_count_sample": len(rows),
            "result_code": code,
            "message": message,
            "fields": _field_sample(rows),
            "checked_at": checked_at,
        }
    except Exception as exc:
        return {
            "group": group,
            "service_name": service_name,
            "ok": False,
            "root_key": "",
            "row_count_sample": 0,
            "result_code": "",
            "message": str(exc),
            "fields": "",
            "checked_at": checked_at,
        }


def markdown_report(results: list[dict[str, Any]], registry: dict[str, Any]) -> str:
    generated_at = datetime.now().isoformat(timespec="seconds")
    lines = [
        "# 서울 OpenAPI 연결 진단 보고서",
        "",
        f"진단 시각: {generated_at}",
        "",
        "본 보고서는 API 키 값을 출력하거나 저장하지 않는다. 성공한 서비스명만 이후 live data pipeline에서 사용한다.",
        "",
        "## 요약",
        "",
        f"- 성공한 공공서비스예약 서비스명: {', '.join(registry.get('public_reservation_services', [])) or '없음'}",
        f"- 성공한 문화행사 서비스명: {', '.join(registry.get('culture_event_services', [])) or '없음'}",
        f"- 서비스 레지스트리: `data/cache/api_service_registry.json`",
        "",
        "## 서비스별 진단 결과",
        "",
        "| 그룹 | 서비스명 | 결과 | 루트 키 | 샘플 row 수 | RESULT 코드 | 메시지 | 대표 필드 |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for item in results:
        status = "성공" if item["ok"] else "실패"
        message = str(item.get("message", "")).replace("\n", " / ").replace("|", "/")
        fields = str(item.get("fields", "")).replace("|", "/")
        lines.append(
            f"| {item['group']} | `{item['service_name']}` | {status} | `{item.get('root_key', '')}` | "
            f"{item.get('row_count_sample', 0)} | `{item.get('result_code', '')}` | {message} | {fields} |"
        )
    lines.extend([
        "",
        "## 사용 원칙",
        "",
        "- 서울 OpenAPI는 한 번에 최대 1,000건씩 호출하고, 1,000건 초과 데이터는 `1~1000`, `1001~2000` 방식으로 나누어 호출한다.",
        "- 공공서비스예약 데이터는 SVCID가 있으면 `https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id={SVCID}` 형식의 공식 예약 상세 URL로 연결한다.",
        "- 문화행사 데이터는 예약상태가 명확하지 않을 수 있으므로 공식 출처 링크 확인 필요 또는 참여 가능성으로 표시한다.",
        "- 실제 회차별 잔여석과 최종 신청 가능 여부는 공식 예약/출처 페이지에서 확인해야 한다.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    config = load_api_config()
    if not config.has_seoul_key:
        print("SEOUL_OPENAPI_KEY가 없어 진단을 중단합니다. .env에 키를 설정하세요.")
        return 2

    results: list[dict[str, Any]] = []
    for service in PUBLIC_RESERVATION_CANDIDATES:
        results.append(check_service(service, "public_reservation"))
    for service in CULTURE_EVENT_CANDIDATES:
        results.append(check_service(service, "culture_event"))

    registry = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "public_reservation_services": [r["service_name"] for r in results if r["group"] == "public_reservation" and r["ok"]],
        "culture_event_services": [r["service_name"] for r in results if r["group"] == "culture_event" and r["ok"]],
        "diagnostics": results,
    }
    registry_file = write_service_registry(registry)

    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    report_path = docs_dir / "api_connection_report.md"
    report_path.write_text(markdown_report(results, registry), encoding="utf-8")

    print("서울 OpenAPI 연결 진단 완료")
    print(f"- report: {report_path}")
    print(f"- registry: {registry_file}")
    print("| group | service | ok | root | rows |")
    print("|---|---|---|---|---:|")
    for item in results:
        print(f"| {item['group']} | {item['service_name']} | {item['ok']} | {item.get('root_key', '')} | {item.get('row_count_sample', 0)} |")

    if not registry["public_reservation_services"] and not registry["culture_event_services"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
