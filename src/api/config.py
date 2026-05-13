from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.config import PROJECT_ROOT


@dataclass(frozen=True)
class ApiConfig:
    seoul_openapi_key: str
    neis_api_key: str
    schoolinfo_api_key: str
    kakao_rest_api_key: str
    naver_client_id: str
    naver_client_secret: str

    @property
    def has_seoul_key(self) -> bool:
        return bool(self.seoul_openapi_key and self.seoul_openapi_key.upper() != "NONE")

    @property
    def has_neis_key(self) -> bool:
        return bool(self.neis_api_key and self.neis_api_key.upper() != "NONE")

    @property
    def has_schoolinfo_key(self) -> bool:
        return bool(self.schoolinfo_api_key and self.schoolinfo_api_key.upper() != "NONE")


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_api_config() -> ApiConfig:
    _load_dotenv(PROJECT_ROOT / ".env")
    return ApiConfig(
        seoul_openapi_key=os.getenv("SEOUL_OPENAPI_KEY", "").strip(),
        neis_api_key=os.getenv("NEIS_API_KEY", "").strip(),
        schoolinfo_api_key=os.getenv("SCHOOLINFO_API_KEY", "").strip(),
        kakao_rest_api_key=os.getenv("KAKAO_REST_API_KEY", "").strip(),
        naver_client_id=os.getenv("NAVER_CLIENT_ID", "").strip(),
        naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", "").strip(),
    )
