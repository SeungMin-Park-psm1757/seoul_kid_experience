import pytest

from src.api.config import load_api_config
from src.api.seoul_openapi import fetch_service_page


def test_culture_event_api_returns_rows_when_key_exists():
    config = load_api_config()
    if not config.has_seoul_key:
        pytest.skip("SEOUL_OPENAPI_KEY is not configured")

    page = fetch_service_page("culturalEventInfo", start=1, end=1)

    assert page.rows
    assert isinstance(page.rows[0], dict)
