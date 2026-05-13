from __future__ import annotations

import json
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

from .config import AGE_GROUPS, DISTRICT_TILE_POSITIONS, FIGURES_DIR, SEOUL_DISTRICTS, SEOUL_GEOJSON


def setup_korean_font() -> None:
    candidates = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"]
    available = {font.name for font in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def _ensure_outdir(out_dir: Path = FIGURES_DIR) -> None:
    setup_korean_font()
    out_dir.mkdir(parents=True, exist_ok=True)


def make_empty_weekend_calendar(weekly: pd.DataFrame, age_group: str = "7-9세", out_dir: Path = FIGURES_DIR) -> Path:
    _ensure_outdir(out_dir)
    subset = weekly[weekly["age_group"] == age_group]
    pivot = subset.pivot(index="district", columns="week", values="choice_index").reindex(SEOUL_DISTRICTS)
    fig, ax = plt.subplots(figsize=(16, 7))
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlGnBu", vmin=0, vmax=100)
    ax.set_title(f"빈 주말 캘린더 - {age_group}", fontsize=16, pad=14)
    ax.set_xlabel("2026년 주차")
    ax.set_ylabel("서울 자치구")
    ax.set_xticks(np.arange(0, 52, 4))
    ax.set_xticklabels([str(i) for i in range(1, 53, 4)])
    ax.set_yticks(np.arange(len(SEOUL_DISTRICTS)))
    ax.set_yticklabels(SEOUL_DISTRICTS, fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02).set_label("선택가능도")
    if pivot.size:
        threshold = np.nanpercentile(pivot.values, 20)
        for y in range(pivot.shape[0]):
            for x in range(pivot.shape[1]):
                value = pivot.iloc[y, x]
                if pd.notna(value) and value <= threshold:
                    ax.scatter(x, y, s=3, color="black", alpha=0.45)
    out_path = out_dir / "07_empty_weekend_calendar.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    # Backward-compatible filename.
    legacy = out_dir / "01_empty_weekend_calendar.png"
    if legacy != out_path:
        legacy.write_bytes(out_path.read_bytes())
    return out_path


def _feature_rings(feature: dict) -> list[list[list[float]]]:
    geometry = feature.get("geometry", {})
    coordinates = geometry.get("coordinates", [])
    if geometry.get("type") == "Polygon":
        return [coordinates[0]]
    if geometry.get("type") == "MultiPolygon":
        return [polygon[0] for polygon in coordinates if polygon]
    return []


def _ring_center(ring: list[list[float]]) -> tuple[float, float]:
    xs = [point[0] for point in ring]
    ys = [point[1] for point in ring]
    return float(np.mean(xs)), float(np.mean(ys))


def _draw_planb_geojson_map(subset: pd.DataFrame, age_group: str, out_dir: Path) -> Path:
    geojson = json.loads(SEOUL_GEOJSON.read_text(encoding="utf-8"))
    values = subset.set_index("district")["planb_index"].to_dict()
    patches, patch_values, label_points = [], [], {}
    for feature in geojson["features"]:
        district = feature.get("properties", {}).get("name")
        rings = _feature_rings(feature)
        for ring in rings:
            patches.append(Polygon(ring, closed=True))
            patch_values.append(float(values.get(district, 0)))
        if rings:
            label_points[district] = _ring_center(rings[0])

    fig, ax = plt.subplots(figsize=(10.5, 10.5))
    collection = PatchCollection(patches, cmap=plt.get_cmap("YlGn"), edgecolor="#4d5a51", linewidth=0.8)
    collection.set_array(np.array(patch_values))
    collection.set_clim(0, 100)
    ax.add_collection(collection)
    xs = [point[0] for patch in patches for point in patch.get_xy()]
    ys = [point[1] for patch in patches for point in patch.get_xy()]
    ax.set_xlim(min(xs) - 0.015, max(xs) + 0.015)
    ax.set_ylim(min(ys) - 0.015, max(ys) + 0.015)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"플랜B 충분도 지도 - {age_group}", fontsize=16, pad=16)
    for district, (x, y) in label_points.items():
        value = values.get(district)
        if value is None:
            continue
        ax.text(x, y, f"{district}\n{value:.0f}", ha="center", va="center", fontsize=8, weight="bold")
    fig.colorbar(collection, ax=ax, fraction=0.034, pad=0.018).set_label("플랜B 충분도")
    out_path = out_dir / "08_planb_map.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    (out_dir / "02_planb_tilemap.png").write_bytes(out_path.read_bytes())
    return out_path


def _draw_planb_fallback_tilemap(subset: pd.DataFrame, age_group: str, out_dir: Path) -> Path:
    subset = subset.set_index("district")
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_title(f"플랜B 충분도 타일맵 - {age_group}", fontsize=16, pad=14)
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(7.5, -0.5)
    ax.axis("off")
    cmap = plt.get_cmap("YlGn")
    for district, (r, c) in DISTRICT_TILE_POSITIONS.items():
        value = float(subset.loc[district, "planb_index"]) if district in subset.index else 0
        rect = plt.Rectangle((c, r), 0.92, 0.82, facecolor=cmap(value / 100), edgecolor="#555555", linewidth=0.7)
        ax.add_patch(rect)
        ax.text(c + 0.46, r + 0.33, district, ha="center", va="center", fontsize=9, weight="bold")
        ax.text(c + 0.46, r + 0.58, f"{value:.0f}", ha="center", va="center", fontsize=9)
    out_path = out_dir / "08_planb_map.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    (out_dir / "02_planb_tilemap.png").write_bytes(out_path.read_bytes())
    return out_path


def make_planb_tilemap(metrics: pd.DataFrame, age_group: str = "7-9세", out_dir: Path = FIGURES_DIR) -> Path:
    _ensure_outdir(out_dir)
    subset = metrics[metrics["age_group"] == age_group].copy()
    # Static PPT export should be fast and reliable in synced workspaces; the app keeps the interactive map.
    return _draw_planb_fallback_tilemap(subset, age_group, out_dir)


def make_age_blindspot_heatmap(metrics: pd.DataFrame, out_dir: Path = FIGURES_DIR) -> Path:
    _ensure_outdir(out_dir)
    pivot = metrics.pivot(index="district", columns="age_group", values="choice_index").reindex(SEOUL_DISTRICTS)
    pivot = pivot[[c for c in AGE_GROUPS if c in pivot.columns]]
    fig, ax = plt.subplots(figsize=(8, 9))
    im = ax.imshow(pivot.values, aspect="auto", cmap="PuBuGn", vmin=0, vmax=100)
    ax.set_title("연령별 블라인드 스팟", fontsize=15, pad=12)
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=11)
    ax.set_yticks(np.arange(len(SEOUL_DISTRICTS)))
    ax.set_yticklabels(SEOUL_DISTRICTS, fontsize=9)
    for y in range(pivot.shape[0]):
        for x in range(pivot.shape[1]):
            ax.text(x, y, f"{pivot.iloc[y, x]:.0f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02).set_label("선택가능도")
    out_path = out_dir / "09_age_blindspot.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    (out_dir / "03_age_blindspot_heatmap.png").write_bytes(out_path.read_bytes())
    return out_path


def make_choice_planb_matrix(metrics: pd.DataFrame, age_group: str = "7-9세", out_dir: Path = FIGURES_DIR) -> Path:
    _ensure_outdir(out_dir)
    subset = metrics[metrics["age_group"] == age_group].copy()
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(subset["choice_index"], subset["planb_index"], s=90, alpha=0.78)
    for _, row in subset.iterrows():
        ax.text(row["choice_index"] + 0.8, row["planb_index"] + 0.8, row["district"], fontsize=8)
    ax.axvline(subset["choice_index"].median(), linestyle="--", linewidth=1)
    ax.axhline(subset["planb_index"].median(), linestyle="--", linewidth=1)
    ax.set_xlabel("선택가능도")
    ax.set_ylabel("플랜B 충분도")
    ax.set_title(f"선택가능도 x 플랜B 매트릭스 - {age_group}", fontsize=16, pad=14)
    ax.set_xlim(0, 105)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.22)
    out_path = out_dir / "10_policy_summary.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    (out_dir / "04_choice_planb_matrix.png").write_bytes(out_path.read_bytes())
    return out_path


def make_barrier_decomposition(metrics: pd.DataFrame, age_group: str = "7-9세", out_dir: Path = FIGURES_DIR) -> Path:
    _ensure_outdir(out_dir)
    subset = metrics[metrics["age_group"] == age_group].sort_values("barrier_index", ascending=False).head(10)
    components = ["paid_share", "reservation_dependency", "age_restriction_intensity", "rule_complexity"]
    labels = ["비용", "예약 의존", "연령 제한", "규칙 명확성"]
    fig, ax = plt.subplots(figsize=(12, 7))
    bottom = np.zeros(len(subset))
    for comp, label in zip(components, labels):
        values = subset[comp].values * 100
        ax.bar(subset["district"], values, bottom=bottom, label=label)
        bottom += values
    ax.set_title(f"이용장벽 분해 - {age_group}", fontsize=16, pad=14)
    ax.set_ylabel("상대 점수")
    ax.legend(loc="upper right")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", alpha=0.22)
    out_path = out_dir / "05_barrier_decomposition.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return out_path


def save_all_visualizations(weekly: pd.DataFrame, metrics: pd.DataFrame, out_dir: Path = FIGURES_DIR) -> list[Path]:
    return [
        make_empty_weekend_calendar(weekly, out_dir=out_dir),
        make_planb_tilemap(metrics, out_dir=out_dir),
        make_age_blindspot_heatmap(metrics, out_dir=out_dir),
        make_choice_planb_matrix(metrics, out_dir=out_dir),
        make_barrier_decomposition(metrics, out_dir=out_dir),
    ]
