from __future__ import annotations

from datetime import date

import pandas as pd


def weekend_bounds(selected_day: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    day = pd.Timestamp(selected_day)
    if day.weekday() <= 4:
        saturday = day + pd.Timedelta(days=5 - day.weekday())
    else:
        saturday = day - pd.Timedelta(days=day.weekday() - 5)
    sunday = saturday + pd.Timedelta(days=1)
    return saturday.normalize(), sunday.normalize()


def classify_date_match(start, end, selected_day: date) -> str:
    start_ts = pd.to_datetime(start, errors="coerce")
    end_ts = pd.to_datetime(end, errors="coerce")
    if pd.isna(start_ts):
        return "not_for_selected_date"
    if pd.isna(end_ts):
        end_ts = start_ts

    selected_ts = pd.Timestamp(selected_day).normalize()
    start_day = start_ts.normalize()
    end_day = end_ts.normalize()
    weekend_start, weekend_end = weekend_bounds(selected_day)

    if end_day < selected_ts:
        return "not_for_selected_date"
    if start_day <= selected_ts <= end_day:
        return "exact_date"
    if start_day <= weekend_end and end_day >= weekend_start:
        return "same_weekend"

    gap = min(abs((start_day - selected_ts).days), abs((end_day - selected_ts).days))
    if gap <= 7:
        return "near_7_days"
    if gap <= 30:
        return "wider_option"
    return "not_for_selected_date"


__all__ = ["weekend_bounds", "classify_date_match"]
