from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import DATA_CACHE


def cache_dir() -> Path:
    DATA_CACHE.mkdir(parents=True, exist_ok=True)
    return DATA_CACHE


def today_cache_file(prefix: str) -> Path | None:
    today = datetime.now().strftime("%Y%m%d")
    files = sorted(cache_dir().glob(f"{prefix}_{today}_*.json"), reverse=True)
    return files[0] if files else None


def read_json_cache(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_cache(prefix: str, payload: Any) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    path = cache_dir() / f"{prefix}_{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def registry_path() -> Path:
    return cache_dir() / "api_service_registry.json"


def read_service_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.exists():
        return {}
    return read_json_cache(path)


def write_service_registry(payload: dict[str, Any]) -> Path:
    path = registry_path()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
