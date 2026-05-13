from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AGE_GROUPS, NEIGHBOR_DISTRICTS, SEOUL_DISTRICTS
from .normalize_status import is_available_norm

LOW_COST_TYPES = {"무료", "저비용"}


def _minmax(series: pd.Series) -> pd.Series:
    series = series.fillna(0).astype(float)
    low, high = series.min(), series.max()
    if high == low:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - low) / (high - low)


def _compatible(df: pd.DataFrame, age_min: int, age_max: int) -> pd.DataFrame:
    return df[(df["age_min"] <= age_max) & (df["age_max"] >= age_min)].copy()


def _is_available(row: pd.Series) -> bool:
    if "reservation_status_norm" in row:
        return is_available_norm(row["reservation_status_norm"])
    text = str(row.get("status", ""))
    return any(key in text for key in ["지금 신청 가능", "상시", "마감 임박", "접수중", "예약가능"]) and "마감" not in text


def _rule_complexity_score(row: pd.Series) -> float:
    text = " ".join(str(row.get(c, "")) for c in ["rule_summary", "no_show_rule", "cancel_rule"])
    score = 0.0
    if "확인 필요" in text or "공식 출처" in text:
        score += 0.35
    if "취소" in text or "기한" in text:
        score += 0.20
    if "노쇼" in text or "미참여" in text or "제한" in text:
        score += 0.25
    if len(text) > 70:
        score += 0.20
    return min(score, 1.0)


def _prepare(programs: pd.DataFrame) -> pd.DataFrame:
    out = programs.copy()
    out["week"] = pd.to_numeric(out.get("week", 0), errors="coerce").fillna(0).astype(int)
    out["age_min"] = pd.to_numeric(out["age_min"], errors="coerce").fillna(0).astype(int)
    out["age_max"] = pd.to_numeric(out["age_max"], errors="coerce").fillna(99).astype(int)
    out["is_available"] = out.apply(_is_available, axis=1)
    out["is_low_cost"] = out["fee_type"].isin(LOW_COST_TYPES) | pd.to_numeric(out.get("fee", 0), errors="coerce").fillna(0).eq(0)
    out["is_indoor"] = out["indoor_outdoor"].astype(str).str.contains("실내|혼합", regex=True)
    out["is_paid"] = ~out["fee_type"].isin(["무료"])
    out["reservation_required"] = out.get("reservation_required", False).fillna(False).astype(bool)
    out["rule_complexity"] = out.apply(_rule_complexity_score, axis=1)
    return out


def compute_weekly_choice_metrics(programs: pd.DataFrame, population: pd.DataFrame | None = None) -> pd.DataFrame:
    programs = _prepare(programs)
    rows = []
    for age_label, (a_min, a_max) in AGE_GROUPS.items():
        compatible = _compatible(programs, a_min, a_max)
        grouped = compatible.groupby(["district", "week"], dropna=False).agg(
            program_count=("program_id", "count"),
            available_count=("is_available", "sum"),
            low_cost_share=("is_low_cost", "mean"),
            indoor_share=("is_indoor", "mean"),
            category_diversity=("category", "nunique"),
        ).reset_index()
        grid = pd.MultiIndex.from_product([SEOUL_DISTRICTS, range(1, 53)], names=["district", "week"]).to_frame(index=False)
        part = grid.merge(grouped, on=["district", "week"], how="left")
        part["age_group"] = age_label
        part["program_count"] = part["program_count"].fillna(0).astype(int)
        part["available_count"] = part["available_count"].fillna(0).astype(int)
        part["low_cost_share"] = part["low_cost_share"].fillna(0.0)
        part["indoor_share"] = part["indoor_share"].fillna(0.0)
        part["category_diversity"] = part["category_diversity"].fillna(0).astype(int)
        part["availability_share"] = np.where(part["program_count"].gt(0), part["available_count"] / part["program_count"], 0.0)
        rows.extend(part.to_dict("records"))

    df = pd.DataFrame(rows)
    parts = []
    for _, part in df.groupby("age_group"):
        part = part.copy()
        part["count_scaled"] = _minmax(part["program_count"])
        part["diversity_scaled"] = _minmax(part["category_diversity"])
        part["choice_index"] = 100 * (
            0.35 * part["count_scaled"]
            + 0.20 * part["availability_share"]
            + 0.15 * part["low_cost_share"]
            + 0.10 * part["indoor_share"]
            + 0.20 * part["diversity_scaled"]
        )
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def compute_district_age_metrics(programs: pd.DataFrame, population: pd.DataFrame) -> pd.DataFrame:
    programs = _prepare(programs)
    rows = []
    for age_label, (a_min, a_max) in AGE_GROUPS.items():
        for district in SEOUL_DISTRICTS:
            local = _compatible(programs[programs["district"] == district], a_min, a_max)
            neighbors = NEIGHBOR_DISTRICTS.get(district, [])
            neighbor_df = _compatible(programs[programs["district"].isin(neighbors)], a_min, a_max)
            pop_row = population[(population["district"] == district) & (population["age_group"] == age_label)]
            pop = int(pop_row["child_population"].iloc[0]) if len(pop_row) else 1
            program_count = len(local)
            available = local[local["is_available"]]
            category_diversity = local["category"].nunique() if program_count else 0
            age_span = (local["age_max"] - local["age_min"]).clip(lower=0) if program_count else pd.Series(dtype=float)

            rows.append({
                "district": district,
                "age_group": age_label,
                "child_population": pop,
                "program_count": program_count,
                "available_count": len(available),
                "closed_count": int(local.get("is_full_or_closed", pd.Series(False, index=local.index)).sum()) if program_count else 0,
                "programs_per_1000_children": (program_count / max(pop, 1)) * 1000,
                "category_diversity": category_diversity,
                "availability_share": float(local["is_available"].mean()) if program_count else 0,
                "low_cost_share": float(local["is_low_cost"].mean()) if program_count else 0,
                "indoor_share": float(local["is_indoor"].mean()) if program_count else 0,
                "local_alt_count": len(available),
                "neighbor_alt_count": len(neighbor_df[neighbor_df["is_available"]]),
                "paid_share": float(local["is_paid"].mean()) if program_count else 0,
                "reservation_dependency": float(local["reservation_required"].mean()) if program_count else 0,
                "age_restriction_intensity": float((age_span <= 2).mean()) if program_count else 0,
                "rule_complexity": float(local["rule_complexity"].mean()) if program_count else 0,
            })

    df = pd.DataFrame(rows)
    parts = []
    for _, part in df.groupby("age_group"):
        part = part.copy()
        part["count_scaled"] = _minmax(part["program_count"])
        part["per1000_scaled"] = _minmax(part["programs_per_1000_children"])
        part["diversity_scaled"] = _minmax(part["category_diversity"])
        part["local_alt_scaled"] = _minmax(part["local_alt_count"])
        part["neighbor_alt_scaled"] = _minmax(part["neighbor_alt_count"])
        part["choice_index"] = 100 * (
            0.30 * part["count_scaled"]
            + 0.20 * part["per1000_scaled"]
            + 0.15 * part["low_cost_share"]
            + 0.10 * part["indoor_share"]
            + 0.15 * part["diversity_scaled"]
            + 0.10 * part["availability_share"]
        )
        part["planb_index"] = 100 * (
            0.35 * part["local_alt_scaled"]
            + 0.25 * part["neighbor_alt_scaled"]
            + 0.15 * part["diversity_scaled"]
            + 0.15 * part["low_cost_share"]
            + 0.10 * part["indoor_share"]
        )
        part["barrier_index"] = 100 * (
            0.30 * part["paid_share"]
            + 0.25 * part["reservation_dependency"]
            + 0.20 * part["age_restriction_intensity"]
            + 0.25 * part["rule_complexity"]
        )
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def classify_district_type(row: pd.Series, choice_median: float, planb_median: float) -> str:
    high_choice = row["choice_index"] >= choice_median
    high_planb = row["planb_index"] >= planb_median
    if high_choice and high_planb:
        return "A 선택 풍부 / 플랜B 풍부"
    if high_choice and not high_planb:
        return "B 선택 풍부 / 플랜B 부족"
    if not high_choice and high_planb:
        return "C 선택 부족 / 플랜B 보완 가능"
    return "D 선택 부족 / 플랜B 부족"


def add_district_types(metrics: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, part in metrics.groupby("age_group"):
        part = part.copy()
        cm = part["choice_index"].median()
        pm = part["planb_index"].median()
        part["district_type"] = part.apply(classify_district_type, axis=1, choice_median=cm, planb_median=pm)
        out.append(part)
    return pd.concat(out, ignore_index=True)
