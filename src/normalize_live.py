from __future__ import annotations

import pandas as pd

from .build_all import normalize_culture_event_records, normalize_public_reservation_records
from .normalize import ensure_unified_columns


def normalize_live_records(public_reservation_records: list[dict], culture_event_records: list[dict]) -> pd.DataFrame:
    public_df = normalize_public_reservation_records(public_reservation_records)
    culture_df = normalize_culture_event_records(culture_event_records)
    return ensure_unified_columns(pd.concat([public_df, culture_df], ignore_index=True))


__all__ = ["normalize_live_records", "normalize_public_reservation_records", "normalize_culture_event_records"]
