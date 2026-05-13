from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.build_all import META_PATH, build
from src.category_groups import (
    PARENT_DEFAULT_INTERESTS,
    available_interest_options,
    display_for_raw_category,
    normalize_selected_interests,
    raw_categories_for_interests,
)
from src.config import AGE_GROUPS, DATA_PROCESSED, FIGURES_DIR, SEOUL_DISTRICTS, SEOUL_GEOJSON
from src.visualize import setup_korean_font
from src.recommend import (
    DATE_BADGE,
    ParentFilters,
    add_recommendation_features,
    available_now_candidates,
    best_relaxation_comment,
    closed_or_uncertain_candidates,
    condition_relaxation_counts,
    filter_recommendations,
    plan_b_candidates,
    sort_recommendations,
)

st.set_page_config(
    page_title="서울 데이터 기반 아이체험 큐레이터",
    page_icon="D",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
body { background: #f7f3ea; }
.block-container { padding: max(24px, env(safe-area-inset-top)) 16px 2.8rem 16px; max-width: min(1080px, 100%); }
.hero-title { font-size: clamp(1.72rem, 5vw, 2.15rem); line-height: 1.3; font-weight: 900; color: #20231d; margin: .12rem 0 .42rem 0; word-break: keep-all; overflow: visible; white-space: normal; text-overflow: clip; }
.hero-sub { font-size: .98rem; color: #5a5e55; max-width: 1040px; word-break: keep-all; }
.parent-panel { border: 1px solid #ded3bf; border-radius: 18px; padding: 1rem; background: linear-gradient(135deg, #fffdf7 0%, #f4efe4 100%); box-shadow: 0 10px 28px rgba(69, 55, 32, .06); overflow: visible; }
.action-panel { border: 1px solid #d8c7a9; border-radius: 16px; background: #fffaf0; padding: .85rem .95rem; margin: .85rem 0; }
.action-title { font-weight: 900; color: #1f251d; margin-bottom: .42rem; }
.action-link { display: inline-block; margin: .18rem .28rem .18rem 0; padding: .45rem .68rem; border-radius: 999px; background: #365f53; color: #fff !important; text-decoration: none; font-weight: 850; font-size: .86rem; }
.data-badge { display: inline-block; border: 1px solid #d8c7a9; border-radius: 999px; padding: .28rem .64rem; background: #fffaf0; color: #5d4420; font-weight: 850; font-size: .82rem; margin-bottom: .7rem; }
.summary-card { border: 1px solid #ded3bf; border-radius: 14px; padding: .78rem .85rem; background: #fffdf8; min-height: 92px; }
.summary-label { color: #727264; font-size: .78rem; margin-bottom: .24rem; }
.summary-value { color: #20231d; font-size: 1.45rem; font-weight: 900; }
.program-card { border: 1px solid #d9d0bf; border-radius: 16px; padding: .78rem .88rem; background: #fffdf8; margin-bottom: .68rem; box-shadow: 0 7px 18px rgba(38, 31, 20, .045); overflow: visible; }
.program-title { font-size: 1.03rem; font-weight: 900; color: #1f251d; margin-bottom: .2rem; word-break: keep-all; }
.program-meta { color: #606457; font-size: .84rem; margin-bottom: .42rem; word-break: keep-all; }
.pill { display: inline-block; border-radius: 999px; padding: .16rem .48rem; margin: .10rem .10rem .10rem 0; background: #edf0df; color: #39402f; font-weight: 760; font-size: .74rem; }
.pill-good { background: #dcefdc; color: #21532f; }
.pill-warn { background: #f5e3c2; color: #744a11; }
.pill-bad { background: #f2d8d1; color: #79351f; }
.pill-blue { background: #dfe8f3; color: #243e5d; }
.reason-box { border-left: 4px solid #5e7b61; padding: .5rem .66rem; background: #fffaf0; color: #3d4138; margin: .42rem 0; border-radius: 0 12px 12px 0; font-size: .88rem; }
.caution-box { border-left: 4px solid #b87b43; padding: .5rem .66rem; background: #fff7ed; color: #5f3b20; margin: .42rem 0; border-radius: 0 12px 12px 0; font-size: .86rem; }
.soft-note { color: #68695f; font-size: .86rem; word-break: keep-all; }
.status-strip { border: 1px solid #ded3bf; border-radius: 14px; padding: .72rem .86rem; background: #fffdf8; color: #3f433a; margin: .78rem 0 .86rem 0; }
.result-preview { border: 2px solid #668b6f; border-radius: 18px; padding: 1rem; background: linear-gradient(135deg, #f8fff4 0%, #fffaf0 100%); margin: .95rem 0 1rem 0; box-shadow: 0 12px 30px rgba(66, 92, 55, .09); }
.result-preview-title { font-size: 1.08rem; font-weight: 950; color: #1f251d; margin-bottom: .28rem; word-break: keep-all; }
.result-preview-meta { color: #4f5b48; font-size: .9rem; line-height: 1.55; word-break: keep-all; }
.next-step-card { border: 1px dashed #cdbb99; border-radius: 15px; padding: .85rem .95rem; background: #fffdf8; margin: .9rem 0; color: #5f604f; }
.rule-card { border: 1px solid #ded3bf; border-radius: 14px; padding: .75rem; background: #fffdf8; min-height: 128px; }
.rule-card h4 { margin: 0 0 .35rem 0; font-size: .95rem; }
.rule-state { font-weight: 900; color: #275532; font-size: .82rem; }
.policy-brief-card { border: 1px solid #d9d0bf; border-radius: 14px; padding: .86rem .92rem; background: #fffefa; min-height: 188px; box-shadow: 0 4px 14px rgba(38, 31, 20, .035); }
.policy-brief-card h4 { margin: .1rem 0 .38rem 0; color: #20231d; font-size: 1rem; }
.policy-brief-card p { margin: .2rem 0; color: #555b4f; font-size: .86rem; line-height: 1.55; word-break: keep-all; }
.policy-reading-note { border-left: 4px solid #384f45; background: #f3f0e6; padding: .62rem .78rem; border-radius: 0 12px 12px 0; color: #31392f; margin: .6rem 0 .9rem 0; }
a.reserve-link, a.card-link-button { color: #225d50; font-weight: 850; text-decoration: none; }
a.card-link-button { display: inline-block; border: 1px solid #2f6557; border-radius: 10px; padding: .42rem .62rem; margin: .18rem .18rem .18rem 0; background: #fff; color: #1f5a4e !important; }
.mobile-note { color: #68695f; font-size: .84rem; margin-top: .3rem; }
[data-baseweb="select"] > div { min-height: 46px; height: auto; align-items: flex-start; overflow: visible; }
[data-baseweb="select"] [class*="ValueContainer"] { max-height: none; overflow: visible; flex-wrap: wrap; }
[data-testid="stVerticalBlock"] { overflow: visible; }
[data-testid="stHeader"] { background: transparent; height: 0; min-height: 0; }
[data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
[data-testid="stDecoration"] { display: none; }
@media (max-width: 760px) {
  .block-container { padding: max(20px, env(safe-area-inset-top)) .78rem 2.4rem .78rem; max-width: 100vw; }
  .hero-title { font-size: 1.64rem; line-height: 1.34; }
  .hero-sub { font-size: .92rem; line-height: 1.65; }
  .parent-panel, .status-strip, .program-card, .summary-card, .action-panel { border-radius: 14px; }
  .result-preview, .next-step-card { border-radius: 14px; padding: .82rem; }
  .action-link { display: block; text-align: center; margin: .32rem 0; }
  .program-title { font-size: .98rem; }
  .pill { font-size: .72rem; }
  div[data-testid="stHorizontalBlock"] { gap: .5rem; }
  .stButton button { width: 100%; }
  a.card-link-button { display: block; text-align: center; margin: .28rem 0; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
warnings.filterwarnings("ignore", message="Glyph .* missing from font")

PROGRAMS_PATH = DATA_PROCESSED / "unified_programs.csv"
METRICS_PATH = DATA_PROCESSED / "district_age_metrics.csv"
WEEKLY_PATH = DATA_PROCESSED / "weekly_choice_metrics.csv"
REQUIRED_PROGRAM_COLUMNS = {
    "program_id", "source", "source_service", "title", "category", "district", "venue", "address",
    "lat", "lng", "age_min", "age_max", "age_label", "target_text", "date_start", "date_end",
    "time_text", "fee", "fee_type", "indoor_outdoor", "reservation_status_raw",
    "reservation_status_norm", "availability_group", "available_now", "is_full_or_closed",
    "source_url", "detail_url", "rule_summary", "cancel_rule", "no_show_rule", "family_fit",
    "preparation_note", "data_confidence", "availability_confidence", "recommendation_reason",
    "caution_note", "last_api_update", "id", "week", "status", "status_label", "reservation_required",
}


@dataclass(frozen=True)
class DataStatus:
    mode: str
    updated_at: str
    public_reservation_count: int
    culture_event_count: int
    errors: tuple[str, ...]
    meta: dict


def next_saturday(today: date | None = None) -> date:
    base = today or date.today()
    return base + timedelta(days=(5 - base.weekday()) % 7)


def _file_timestamp(path: Path) -> str:
    if not path.exists():
        return "없음"
    return pd.Timestamp(path.stat().st_mtime, unit="s").strftime("%Y-%m-%d %H:%M")


def ensure_outputs() -> None:
    required = [PROGRAMS_PATH, METRICS_PATH, WEEKLY_PATH]
    if not all(path.exists() for path in required):
        build(sample=False)
        return
    try:
        columns = set(pd.read_csv(PROGRAMS_PATH, nrows=1).columns)
    except Exception:
        build(sample=False)
        return
    if REQUIRED_PROGRAM_COLUMNS - columns:
        build(sample=False)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ensure_outputs()
    programs = pd.read_csv(PROGRAMS_PATH)
    metrics = pd.read_csv(METRICS_PATH)
    weekly = pd.read_csv(WEEKLY_PATH)
    missing = REQUIRED_PROGRAM_COLUMNS - set(programs.columns)
    if missing:
        raise ValueError(f"unified_programs.csv 필수 컬럼 누락: {', '.join(sorted(missing))}")
    programs["date_start"] = pd.to_datetime(programs["date_start"], errors="coerce")
    programs["date_end"] = pd.to_datetime(programs["date_end"], errors="coerce")
    programs["fee"] = pd.to_numeric(programs["fee"], errors="coerce").fillna(0).astype(int)
    programs["age_min"] = pd.to_numeric(programs["age_min"], errors="coerce").fillna(0).astype(int)
    programs["age_max"] = pd.to_numeric(programs["age_max"], errors="coerce").fillna(99).astype(int)
    for col in ["available_now", "is_full_or_closed", "reservation_required"]:
        programs[col] = programs[col].fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])
    return programs, metrics, weekly


def get_data_status() -> DataStatus:
    meta = {}
    if META_PATH.exists():
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    mode = meta.get("data_mode", "sample")
    updated_at = meta.get("last_api_call") or _file_timestamp(PROGRAMS_PATH)
    return DataStatus(
        mode=mode,
        updated_at=updated_at,
        public_reservation_count=int(meta.get("public_reservation_count", 0) or 0),
        culture_event_count=int(meta.get("culture_event_count", 0) or 0),
        errors=tuple(meta.get("errors", [])),
        meta=meta,
    )


def plotly_config() -> dict:
    return {"displayModeBar": False, "responsive": True}


def date_label(row: pd.Series) -> str:
    start = row.get("date_start")
    end = row.get("date_end")
    if pd.isna(start):
        return "날짜 확인 필요"
    if pd.notna(end) and start.date() != end.date():
        return f"{start:%m.%d}~{end:%m.%d}"
    return f"{start:%m.%d}"


def fee_label(row: pd.Series) -> str:
    if int(row.get("fee", 0)) == 0 or row.get("fee_type") == "무료":
        return "무료"
    return f"{int(row['fee']):,}원"


def pill_class(row: pd.Series) -> str:
    norm = row.get("reservation_status_norm", "unknown")
    if norm in {"available", "always_available"}:
        return "pill-good"
    if norm in {"closing_soon", "soon_open", "unknown"}:
        return "pill-warn"
    return "pill-bad"


def confidence_badge(row: pd.Series) -> str:
    value = str(row.get("availability_confidence") or row.get("data_confidence") or "공식 링크에서 최종 확인")
    if "샘플" in value:
        return "샘플"
    if "상세" in value:
        return "상세 확인"
    if "API" in value:
        return "공공데이터 확인"
    return "공식 링크에서 최종 확인"


def difficulty_label(row: pd.Series) -> str:
    difficulty = str(row.get("reservation_difficulty", "unknown"))
    friction = str(row.get("reservation_friction", "unknown"))
    if friction == "low" or difficulty == "easy":
        return "신청 부담 낮음"
    if difficulty == "hard":
        return "마감 위험 높음"
    if difficulty == "medium":
        return "확인 필요"
    return "공식 확인 필요"


def safe_source_url(row: pd.Series) -> str:
    url = str(row.get("source_url", "") or row.get("detail_url", "")).strip()
    return url if url else "https://data.seoul.go.kr/"


def program_brief(row: pd.Series) -> str:
    return f"{row.get('district', '확인 필요')} · {row.get('venue', '확인 필요')} · {date_label(row)} {row.get('time_text', '')}"


def recommendation_bullets(row: pd.Series, filters: ParentFilters) -> list[str]:
    bullets: list[str] = []
    schedule_level = row.get("schedule_match_level", "")
    if schedule_level == "exact_date_match":
        bullets.append("선택한 날짜에 운영되는 후보입니다.")
    elif schedule_level == "recurring_day_match":
        bullets.append("선택한 날짜의 요일과 운영 요일이 맞는 후보입니다.")
    elif schedule_level == "same_weekend_match":
        bullets.append("선택한 날짜가 포함된 주말에 확인할 수 있는 후보입니다.")
    if row.get("age_fit", False):
        bullets.append(f"{filters.child_age}세 아이 조건에 맞고, 대상연령 조건을 통과했습니다.")
    if row.get("fee_type") in {"무료", "저비용"}:
        bullets.append("무료/저비용 조건을 만족합니다.")
    if row.get("indoor_outdoor") in {"실내", "혼합"}:
        bullets.append("실내 또는 날씨 영향을 덜 받는 후보입니다.")
    if int(row.get("travel_minutes", 99)) <= 35:
        bullets.append("출발 자치구에서 가까운 편입니다.")
    if row.get("category") in filters.categories:
        bullets.append(f"관심분야 '{row.get('interest_label', row.get('category'))}' 조건과 맞습니다.")
    return bullets[:3] or [str(row.get("recommendation_reason", "현재 조건에서 먼저 확인할 만한 후보입니다."))]


def render_today_recommendation_card(row: pd.Series, filters: ParentFilters) -> None:
    safe_url = safe_source_url(row)
    badge_items = [
        str(row.get("date_match_badge", "공식 확인 필요")),
        "나이 적합",
        "무료/저비용" if row.get("fee_type") in {"무료", "저비용"} else str(row.get("fee_type", "비용 확인")),
        str(row.get("indoor_outdoor", "확인 필요")),
        "공식 링크 확인",
    ]
    badges = "".join(f'<span class="pill pill-good">{badge}</span>' for badge in badge_items if badge)
    reasons = "".join(f"<li>{reason}</li>" for reason in recommendation_bullets(row, filters))
    st.markdown(
        f"""
        <div class="program-card" style="border-width:2px; border-color:#7a9a70; background:#fffef8;">
          <div class="program-title">오늘의 추천 · {row['title']}</div>
          <div class="program-meta">선택한 날짜와 조건을 기준으로 가장 먼저 확인할 만한 곳입니다.</div>
          <div>{badges}</div>
          <div class="program-meta" style="margin-top:.45rem;">
            <strong>장소</strong> · {row.get('district', '확인 필요')} {row.get('venue', '확인 필요')}<br>
            <strong>일시</strong> · {date_label(row)} {row.get('time_text', '')}<br>
            <strong>대상</strong> · {row.get('age_label', '확인 필요')} · <strong>비용</strong> · {fee_label(row)}<br>
            <strong>이동</strong> · {row.get('travel_range', '추정 확인 필요')} · 이동 난이도 {row.get('travel_difficulty', '확인 필요')}<br>
            <strong>관심분야</strong> · {row.get('interest_label', row.get('category', '확인 필요'))}
          </div>
          <div class="reason-box"><strong>추천 이유</strong><ul style="margin:.35rem 0 .1rem 1.1rem; padding:0;">{reasons}</ul></div>
          <div class="caution-box"><strong>주의할 점</strong> · 실제 신청 가능 여부와 잔여석은 공식 링크에서 최종 확인해 주세요. 이동시간은 공공데이터 위치 기준 추정입니다.</div>
          <a class="card-link-button" href="{safe_url}" target="_blank">공식 링크에서 확인</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("이 후보 상세 보기", key=f"today_answer_detail_{row['program_id']}", use_container_width=True):
            st.session_state["selected_program_id"] = row["program_id"]
            st.toast("상세 확인 탭에서 이 후보를 볼 수 있어요.")
    with c2:
        if st.button("대체 후보 보기", key=f"today_answer_backup_{row['program_id']}", use_container_width=True):
            st.session_state["selected_program_id"] = row["program_id"]
            st.session_state["home_view"] = "대체 후보"
            st.toast("대체 후보를 아래에서 확인하세요.")
            st.rerun()
    with c3:
        if st.button("이미 가본 곳으로 표시", key=f"today_answer_visited_{row['program_id']}", use_container_width=True):
            programs_seen = list(st.session_state.get("visited_programs", []))
            if row["title"] not in programs_seen:
                programs_seen.append(row["title"])
            st.session_state["visited_programs"] = programs_seen
            st.session_state["filters_applied"] = True
            st.toast("이미 가본 곳으로 표시했습니다. 추천 결과에 반영됩니다.")
            st.rerun()


def render_program_card(row: pd.Series, rank: int, *, compact: bool = False, key_prefix: str = "card", show_excluded: bool = False) -> None:
    title_prefix = "지금은 추천하지 않음" if show_excluded else "후보"
    safe_url = safe_source_url(row)
    st.markdown(
        f"""
        <div class="program-card">
          <div class="program-title">{title_prefix} {rank}. {row['title']}</div>
          <div class="program-meta">{program_brief(row)}</div>
          <span class="pill {pill_class(row)}">{row['availability_group']}</span>
          <span class="pill pill-blue">{row['date_match_badge']}</span>
          <span class="pill">{confidence_badge(row)}</span>
          <span class="pill">{row.get('interest_label', row['category'])}</span>
          <span class="pill">{row['age_label']}</span>
          <span class="pill">{fee_label(row)}</span>
          <span class="pill">{row['indoor_outdoor']}</span>
          <span class="pill">{row['travel_range']} · 이동 난이도 {row['travel_difficulty']}</span>
          <span class="pill">{difficulty_label(row)}</span>
          <div class="reason-box"><strong>{'지금은 추천하지 않은 이유' if show_excluded else '왜 이곳인가?'}</strong> · {row.get('excluded_reason', row['recommendation_reason'])}</div>
          <div class="caution-box"><strong>주의할 점</strong> · {row['caution_note']}</div>
          <a class="card-link-button" href="{safe_url}" target="_blank">공식 링크에서 확인</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    action_label = "상세 보기" if not show_excluded else "왜 제외됐는지 보기"
    if compact:
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            if st.button(action_label, key=f"{key_prefix}_detail_{row['program_id']}", use_container_width=True):
                st.session_state["selected_program_id"] = row["program_id"]
                st.toast("상세 확인 탭에서 이 후보를 볼 수 있어요.")
        with bc2:
            if st.button("대체 후보", key=f"{key_prefix}_backup_{row['program_id']}", use_container_width=True):
                st.session_state["selected_program_id"] = row["program_id"]
                st.session_state["home_view"] = "막혔을 때 갈 만한 곳"
                st.toast("상세 확인 탭에서 대체 후보를 확인하세요.")
                st.rerun()
        with bc3:
            if st.button("제외하기", key=f"{key_prefix}_visited_{row['program_id']}", use_container_width=True):
                programs_seen = list(st.session_state.get("visited_programs", []))
                if row["title"] not in programs_seen:
                    programs_seen.append(row["title"])
                st.session_state["visited_programs"] = programs_seen
                st.session_state["filters_applied"] = True
                st.toast("이미 가본 곳으로 표시했습니다. 추천 결과에 반영됩니다.")
                st.rerun()
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("이 후보 상세 보기", key=f"{key_prefix}_detail_{row['program_id']}", use_container_width=True):
                st.session_state["selected_program_id"] = row["program_id"]
                st.toast("상세 확인 탭에서 이 후보를 볼 수 있어요.")
        with c2:
            if st.button("대체 후보 보기", key=f"{key_prefix}_planb_{row['program_id']}", use_container_width=True):
                st.session_state["selected_program_id"] = row["program_id"]
                st.session_state["home_view"] = "막혔을 때 갈 만한 곳"
                st.toast("상세 확인 탭에서 대체 후보를 확인하세요.")
                st.rerun()
        with c3:
            if st.button("이미 가본 곳으로 표시", key=f"{key_prefix}_visited_{row['program_id']}", use_container_width=True):
                programs_seen = list(st.session_state.get("visited_programs", []))
                if row["title"] not in programs_seen:
                    programs_seen.append(row["title"])
                st.session_state["visited_programs"] = programs_seen
                st.session_state["filters_applied"] = True
                st.toast("이미 가본 곳으로 표시했습니다. 추천 결과에 반영됩니다.")
                st.rerun()


def save_funnel_png(funnel: pd.DataFrame) -> Path:
    setup_korean_font()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / "06_condition_relaxation_funnel.png"
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.barh(funnel["step"], funnel["candidate_count"], color="#5f8f77")
    for i, row in funnel.iterrows():
        ax.text(row["candidate_count"] + 0.2, i, f"{int(row['candidate_count'])}개", va="center", fontsize=10)
    ax.set_title("조건을 조금 풀면 후보가 얼마나 늘어날까?", fontsize=14, weight="bold")
    ax.set_xlabel("후보 수")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def make_funnel_figure(funnel: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        funnel,
        x="candidate_count",
        y="step",
        orientation="h",
        text="candidate_count",
        color="increase",
        color_continuous_scale="YlGnBu",
        labels={"candidate_count": "후보 수", "step": "조건 완화 단계", "increase": "증가분"},
    )
    fig.update_traces(texttemplate="%{text}개", textposition="outside")
    fig.update_layout(height=340, yaxis={"categoryorder": "array", "categoryarray": list(reversed(funnel["step"].tolist()))}, margin={"l": 8, "r": 24, "t": 12, "b": 20}, paper_bgcolor="#fffdf8", plot_bgcolor="#fffdf8")
    return fig


@st.cache_data
def load_geojson():
    if not SEOUL_GEOJSON.exists():
        return None
    return json.loads(SEOUL_GEOJSON.read_text(encoding="utf-8"))


def render_map(programs_df: pd.DataFrame) -> None:
    map_df = programs_df.dropna(subset=["lat", "lng"]).copy()
    if map_df.empty:
        st.info("지도에 표시할 좌표가 있는 후보가 없습니다.")
        return
    map_df["map_status"] = map_df.apply(
        lambda row: "확장 후보" if row["date_match_level"] in {"near_7_days", "wider_option"} else row["availability_group"],
        axis=1,
    )
    color_map = {
        "지금 신청 가능": "#2f8f4e",
        "신청 부담 낮음": "#2f8f4e",
        "마감 임박": "#d28426",
        "접수 예정": "#d28426",
        "확인 필요": "#8b8b8b",
        "예약 마감": "#c75b4a",
        "접수 종료": "#c75b4a",
        "행사 종료": "#c75b4a",
        "확장 후보": "#7fb7d6",
    }
    fig = px.scatter_map(
        map_df,
        lat="lat",
        lon="lng",
        hover_name="title",
        hover_data={
            "district": True,
            "venue": True,
            "age_label": True,
            "date_match_badge": True,
            "availability_group": True,
            "travel_range": True,
            "recommendation_reason": True,
            "lat": False,
            "lng": False,
        },
        color="map_status",
        color_discrete_map=color_map,
        size=[14] * len(map_df),
        zoom=10,
        height=480,
        map_style="carto-positron",
    )
    fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0}, paper_bgcolor="#fffdf8", legend_title_text="상태")
    st.plotly_chart(fig, width="stretch", config=plotly_config())


def rule_state(text: str) -> str:
    text = str(text)
    if "확인 필요" in text or "공식" in text:
        return "확인 필요"
    if "주의" in text or "제한" in text or "노쇼" in text:
        return "주의"
    if "없음" in text:
        return "해당 없음"
    return "확인됨"


def render_rule_cards(selected: pd.Series) -> None:
    items = [
        ("보호자 동반", selected["family_fit"]),
        ("준비물", selected["preparation_note"]),
        ("취소 규칙", selected["cancel_rule"]),
        ("노쇼 규칙", selected["no_show_rule"]),
        ("최종 확인 필요사항", selected["caution_note"]),
    ]
    cols = st.columns(5)
    for col, (title, body) in zip(cols, items):
        col.markdown(
            f"""
            <div class="rule-card">
              <h4>{title}</h4>
              <div class="rule-state">{rule_state(body)}</div>
              <p class="soft-note">{body}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def data_quality(programs: pd.DataFrame, filtered_count: int, status: DataStatus) -> dict[str, str]:
    total = len(programs)
    if total == 0:
        return {}
    meta = status.meta
    mode_label = {"api": "실제 API 데이터", "sample": "샘플 데이터", "mixed_error": "데이터 모드 오류"}.get(status.mode, status.mode)
    return {
        "데이터 모드": mode_label,
        "마지막 API 호출": str(status.updated_at or "없음"),
        "공공서비스예약 수집": f"{status.public_reservation_count:,}건",
        "문화행사 수집": f"{status.culture_event_count:,}건",
        "전체 레코드": f"{total:,}건",
        "필터 후 후보": f"{filtered_count:,}건",
        "지금 신청 가능 후보": f"{int(programs['available_now'].fillna(False).astype(bool).sum()):,}건",
        "마감/종료 후보": f"{int(programs['is_full_or_closed'].fillna(False).astype(bool).sum()):,}건",
        "연령 파싱 성공률": f"{float(meta.get('age_parse_success_rate', 0)):.1f}%",
        "날짜 파싱 성공률": f"{float(meta.get('date_parse_success_rate', 0)):.1f}%",
        "좌표 보유율": f"{float(meta.get('coordinate_rate', 0)):.1f}%",
        "예약상태 확인율": f"{float(meta.get('status_known_rate', 0)):.1f}%",
        "마감/예약불가 후보": f"{int(meta.get('closed_or_full_count', programs['is_full_or_closed'].sum())):,}건",
        "공식 링크 보유율": f"{float(meta.get('official_link_rate', 0)):.1f}%",
        "상세 파싱 성공률": f"{float(meta.get('detail_parse_success_rate', 0)):.1f}%",
    }


def render_quality_panel(programs: pd.DataFrame, filtered_count: int, status: DataStatus) -> None:
    quality = data_quality(programs, filtered_count, status)
    cols = st.columns(4)
    for idx, (label, value) in enumerate(quality.items()):
        cols[idx % 4].metric(label, value)
    if status.mode == "mixed_error":
        st.error("샘플 데이터와 API 데이터가 섞였습니다. 캐시를 비우고 다시 수집하세요.")
    elif status.mode != "api":
        st.warning("현재는 샘플 데이터 기반입니다. 실제 제출 전 서울시 OpenAPI 키를 연결해야 합니다.")
    if status.errors:
        st.caption("수집/빌드 메모: " + " / ".join(status.errors[:3]))
    st.caption("이동시간 산정 방식: 실제 교통 API가 아니라 자치구 간 상대거리 기반 추정 범위입니다. 실제 이동시간은 지도/교통 서비스에서 확인하세요.")


def policy_summary(metrics: pd.DataFrame, programs: pd.DataFrame, age_group: str) -> list[str]:
    sub = metrics[metrics["age_group"] == age_group].copy()
    low_choice = ", ".join(sub.sort_values("choice_index").head(3)["district"])
    closed = ", ".join(sub.sort_values("closed_count", ascending=False).head(3)["district"]) if "closed_count" in sub.columns else "확인 필요"
    total = len(programs)
    compatible = programs[(programs["age_min"] <= 9) & (programs["age_max"] >= 7)]
    constrained = compatible[(compatible["fee_type"].isin(["무료", "저비용"])) & (compatible["indoor_outdoor"].isin(["실내", "혼합"]))]
    drop = 0 if len(compatible) == 0 else (1 - len(constrained) / len(compatible)) * 100
    return [
        f"선택가능도 하위 자치구: {low_choice}",
        f"마감 또는 확인 필요 후보가 많은 자치구: {closed}",
        f"7~9세 무료·실내 조건을 적용하면 후보가 전체 대비 약 {drop:.1f}% 감소합니다.",
    ]


def make_heatmap(weekly: pd.DataFrame, age_group: str) -> go.Figure:
    subset = weekly[weekly["age_group"] == age_group]
    pivot = subset.pivot(index="district", columns="week", values="choice_index").reindex(SEOUL_DISTRICTS)
    fig = go.Figure(go.Heatmap(z=pivot.values, x=list(pivot.columns), y=list(pivot.index), zmin=0, zmax=100, colorscale="YlGnBu", colorbar={"title": "선택가능도"}))
    fig.update_layout(height=500, margin={"l": 20, "r": 8, "t": 24, "b": 20}, paper_bgcolor="#fffdf8", plot_bgcolor="#fffdf8")
    return fig


def make_age_blindspot(metrics: pd.DataFrame) -> go.Figure:
    pivot = metrics.pivot(index="district", columns="age_group", values="choice_index").reindex(SEOUL_DISTRICTS)
    pivot = pivot[[age for age in AGE_GROUPS if age in pivot.columns]]
    fig = go.Figure(go.Heatmap(z=pivot.values, x=list(pivot.columns), y=list(pivot.index), zmin=0, zmax=100, colorscale="PuBuGn", text=[[f"{v:.0f}" for v in row] for row in pivot.values], texttemplate="%{text}", colorbar={"title": "선택가능도"}))
    fig.update_layout(height=560, margin={"l": 8, "r": 8, "t": 24, "b": 20}, paper_bgcolor="#fffdf8", plot_bgcolor="#fffdf8")
    return fig


def make_policy_matrix(metrics: pd.DataFrame, age_group: str) -> go.Figure:
    subset = metrics[metrics["age_group"] == age_group].copy()
    fig = px.scatter(subset, x="choice_index", y="planb_index", text="district", color="district_type", hover_data={"program_count": True, "available_count": True, "closed_count": True}, labels={"choice_index": "선택가능도", "planb_index": "대체 후보 충분도", "district_type": "유형"})
    fig.add_vline(x=subset["choice_index"].median(), line_dash="dash", line_color="#626b62")
    fig.add_hline(y=subset["planb_index"].median(), line_dash="dash", line_color="#626b62")
    fig.update_traces(textposition="top center", marker={"size": 12, "opacity": 0.82})
    fig.update_layout(height=500, margin={"l": 8, "r": 8, "t": 24, "b": 20}, paper_bgcolor="#fffdf8", plot_bgcolor="#fffdf8")
    return fig


def make_barrier(metrics: pd.DataFrame, age_group: str) -> go.Figure:
    subset = metrics[metrics["age_group"] == age_group].sort_values("barrier_index", ascending=False).head(10)
    fig = go.Figure()
    for column, label, color in [
        ("paid_share", "비용", "#6f5d48"),
        ("reservation_dependency", "예약 의존", "#3f7c75"),
        ("age_restriction_intensity", "연령 제한", "#a55755"),
        ("rule_complexity", "규칙 명확성", "#6d7f3f"),
    ]:
        fig.add_bar(x=subset["district"], y=subset[column] * 100, name=label, marker_color=color)
    fig.update_layout(barmode="stack", height=430, margin={"l": 8, "r": 8, "t": 24, "b": 20}, paper_bgcolor="#fffdf8", plot_bgcolor="#fffdf8")
    return fig


def policy_action_kind(row: pd.Series, choice_cut: float, planb_cut: float, barrier_cut: float) -> str:
    if row["choice_index"] < choice_cut and row["planb_index"] < planb_cut:
        return "종합 보완 필요형"
    if row["barrier_index"] >= barrier_cut:
        return "이용장벽 완화형"
    if row["planb_index"] < planb_cut:
        return "대체 후보 확충형"
    if row["choice_index"] < choice_cut:
        return "선택지 확충형"
    return "유지·확산형"


def policy_action_plan(kind: str) -> dict[str, str]:
    plans = {
        "종합 보완 필요형": {
            "signal": "선택가능도와 대체 후보가 동시에 낮습니다.",
            "now": "이번 달 공개 프로그램·행사 링크를 우선 정비하고 마감 후보의 대체안을 함께 노출합니다.",
            "mid": "인접구 연계형 주말 패키지와 저비용 실내 프로그램을 보강합니다.",
            "dept": "자치구 문화·교육 부서, 서울시 공공서비스예약 운영",
            "accent": "#5f4035",
        },
        "이용장벽 완화형": {
            "signal": "비용·예약 의존·규칙 불명확성이 후보를 줄입니다.",
            "now": "무료/저비용 필터에서 남는 후보를 점검하고 준비물·취소 규칙 문구를 표준화합니다.",
            "mid": "노쇼·취소 규정은 유지하되 보호자가 이해하기 쉬운 한 줄 요약을 API에 포함합니다.",
            "dept": "시설 운영기관, 예약 플랫폼 운영",
            "accent": "#7a5532",
        },
        "대체 후보 확충형": {
            "signal": "첫 후보가 막히면 같은 조건의 대체안이 부족합니다.",
            "now": "같은 날짜 또는 ±7일 안의 인접구 후보를 함께 묶어 보여줍니다.",
            "mid": "구 경계 인근 시설을 공동 홍보하고 실내 대체 프로그램을 확충합니다.",
            "dept": "인접 자치구 협력, 문화시설 네트워크",
            "accent": "#2f5f62",
        },
        "선택지 확충형": {
            "signal": "후보 총량 자체가 낮아 부모의 첫 선택지가 적습니다.",
            "now": "연령·날짜·링크 누락 데이터를 보완해 숨은 후보를 먼저 복구합니다.",
            "mid": "수요가 큰 연령대의 주말형 프로그램 편성을 늘립니다.",
            "dept": "자치구 교육·문화 기획, 공공시설 운영",
            "accent": "#4f6336",
        },
        "유지·확산형": {
            "signal": "현재 기준으로 선택지와 대체안이 비교적 안정적입니다.",
            "now": "좋은 공지·예약 문구를 표준 사례로 정리합니다.",
            "mid": "인접 취약구와 공동 프로그램을 기획해 효과를 확산합니다.",
            "dept": "우수 운영기관, 서울시 확산 지원",
            "accent": "#465c77",
        },
    }
    return plans[kind]


def policy_action_frame(metrics: pd.DataFrame, age_group: str) -> pd.DataFrame:
    subset = metrics[metrics["age_group"] == age_group].copy()
    if subset.empty:
        return subset
    choice_cut = subset["choice_index"].median()
    planb_cut = subset["planb_index"].median()
    barrier_cut = subset["barrier_index"].quantile(0.70)
    subset["policy_type"] = subset.apply(lambda row: policy_action_kind(row, choice_cut, planb_cut, barrier_cut), axis=1)
    subset["priority_score"] = (
        (100 - subset["choice_index"]) * 0.45
        + (100 - subset["planb_index"]) * 0.35
        + subset["barrier_index"] * 0.20
    )
    return subset.sort_values("priority_score", ascending=False)


def render_policy_action_cards(metrics: pd.DataFrame, age_group: str) -> None:
    frame = policy_action_frame(metrics, age_group)
    if frame.empty:
        st.info("정책 실행 브리프를 계산할 데이터가 없습니다.")
        return
    ordered_types = ["종합 보완 필요형", "대체 후보 확충형", "선택지 확충형", "이용장벽 완화형"]
    cols = st.columns(4)
    for idx, kind in enumerate(ordered_types):
        plan = policy_action_plan(kind)
        areas = frame[frame["policy_type"].eq(kind)].head(3)["district"].tolist()
        area_text = ", ".join(areas) if areas else "해당 상위 지역 없음"
        with cols[idx]:
            st.markdown(
                f'<div class="policy-brief-card" style="border-top: 4px solid {plan["accent"]};">'
                f'<h4>{kind}</h4>'
                f'<p><strong>우선 점검:</strong> {area_text}</p>'
                f'<p>{plan["signal"]}</p>'
                f'<p><strong>즉시:</strong> {plan["now"]}</p>'
                f'<p><strong>협업:</strong> {plan["dept"]}</p>'
                '</div>',
                unsafe_allow_html=True,
            )


def make_condition_loss_figure(programs: pd.DataFrame, filters: ParentFilters) -> go.Figure:
    pool = add_recommendation_features(programs, filters)
    stages = [
        ("전체 후보", len(pool)),
        ("연령 맞음", int(pool["age_fit"].sum())),
        ("선택 날짜/같은 주말", int(pool["date_match_level"].isin(["exact_date", "same_weekend"]).sum())),
        ("지금 신청 가능", int(pool["available_now"].sum())),
        ("무료/저비용", int(pool["fee_type"].isin(["무료", "저비용"]).sum())),
        ("실내/혼합", int(pool["indoor_outdoor"].isin(["실내", "혼합"]).sum())),
        ("공식 링크 보유", int(pool["source_url"].fillna("").astype(str).str.len().gt(0).sum())),
    ]
    total = max(stages[0][1], 1)
    frame = pd.DataFrame(stages, columns=["condition", "count"])
    frame["share"] = frame["count"] / total * 100
    fig = px.bar(
        frame,
        x="share",
        y="condition",
        text=frame.apply(lambda row: f"{int(row['count'])}개 · {row['share']:.0f}%", axis=1),
        orientation="h",
        labels={"share": "전체 대비 비율", "condition": "조건"},
        color="share",
        color_continuous_scale=["#b96a58", "#f2c879", "#5b8c72"],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=360, margin={"l": 8, "r": 32, "t": 24, "b": 20}, paper_bgcolor="#fffdf8", plot_bgcolor="#fffdf8", coloraxis_showscale=False, xaxis_range=[0, 112])
    return fig


def make_priority_matrix_current(metrics: pd.DataFrame, age_group: str) -> go.Figure:
    frame = policy_action_frame(metrics, age_group)
    if frame.empty:
        return go.Figure()
    frame["choice_gap"] = 100 - frame["choice_index"]
    frame["planb_gap"] = 100 - frame["planb_index"]
    fig = px.scatter(
        frame,
        x="choice_gap",
        y="planb_gap",
        text="district",
        size="barrier_index",
        color="policy_type",
        hover_data={"choice_index": ":.1f", "planb_index": ":.1f", "barrier_index": ":.1f", "program_count": True},
        labels={"choice_gap": "첫 선택 어려움", "planb_gap": "대체 후보 부족", "policy_type": "점검 유형"},
    )
    fig.add_vline(x=frame["choice_gap"].median(), line_dash="dash", line_color="#626b62")
    fig.add_hline(y=frame["planb_gap"].median(), line_dash="dash", line_color="#626b62")
    fig.update_traces(textposition="top center", marker={"opacity": 0.82})
    fig.update_layout(height=500, margin={"l": 8, "r": 8, "t": 24, "b": 20}, paper_bgcolor="#fffdf8", plot_bgcolor="#fffdf8")
    return fig


try:
    programs, metrics, weekly = load_data()
except Exception as exc:
    st.error("처리된 데이터가 새 스키마와 맞지 않습니다.")
    st.caption(str(exc))
    if st.button("데이터 다시 빌드", type="primary"):
        build(sample=False)
        load_data.clear()
        st.rerun()
    st.stop()

status = get_data_status()
all_categories = sorted(programs["category"].dropna().astype(str).unique().tolist())
programs["interest_label"] = programs["category"].apply(display_for_raw_category)
interest_options = available_interest_options(all_categories)
all_fee_types = ["무료", "저비용", "유료"]
all_indoor_types = ["실내", "실외", "혼합", "확인 필요"]
default_categories = [interest for interest in PARENT_DEFAULT_INTERESTS if interest in interest_options] or interest_options
default_indoor_types = [value for value in ["실내", "실외", "혼합", "확인 필요"] if value in all_indoor_types]
if "categories_filter" in st.session_state:
    st.session_state["categories_filter"] = normalize_selected_interests(st.session_state["categories_filter"], interest_options)
for key, default in {
    "child_age_filter": 7,
    "grade_filter": "초2",
    "origin_filter": "마포구" if "마포구" in SEOUL_DISTRICTS else SEOUL_DISTRICTS[0],
    "selected_day_filter": next_saturday(),
    "max_travel_filter": 45,
    "fee_types_filter": ["무료", "저비용"],
    "indoor_types_filter": default_indoor_types,
    "categories_filter": default_categories,
    "visited_places": [],
    "visited_programs": [],
    "visited_text": "",
    "exclude_same_place": True,
    "exclude_same_program": True,
    "exclude_same_link": True,
    "show_visited_section": False,
    "home_view": "오늘의 추천",
    "filters_applied": False,
    "result_notice": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.get("reset_filters_requested"):
    st.session_state["child_age_filter"] = 7
    st.session_state["grade_filter"] = "초2"
    st.session_state["origin_filter"] = "마포구" if "마포구" in SEOUL_DISTRICTS else SEOUL_DISTRICTS[0]
    st.session_state["selected_day_filter"] = next_saturday()
    st.session_state["max_travel_filter"] = 45
    st.session_state["fee_types_filter"] = ["무료", "저비용"]
    st.session_state["indoor_types_filter"] = default_indoor_types
    st.session_state["categories_filter"] = default_categories
    st.session_state["visited_places"] = []
    st.session_state["visited_programs"] = []
    st.session_state["visited_text"] = ""
    st.session_state["show_visited_section"] = False
    st.session_state["home_view"] = "오늘의 추천"
    st.session_state["filters_applied"] = False
    st.session_state["result_notice"] = ""
    st.session_state["reset_filters_requested"] = False

mode_title = {"api": "실제 API 데이터", "sample": "샘플 데이터", "mixed_error": "데이터 모드 오류"}.get(status.mode, status.mode)
mode_note = {
    "api": "서울시 OpenAPI 수집 결과를 기반으로 합니다.",
    "sample": "현재는 샘플 데이터입니다. 실제 제출 전 SEOUL_OPENAPI_KEY 연결과 API 수집 검증이 필요합니다.",
    "mixed_error": "샘플 데이터와 API 데이터가 섞였습니다. 캐시를 비우고 다시 수집하세요.",
}.get(status.mode, "데이터 모드를 확인하세요.")
st.markdown(f'<div class="data-badge">{mode_title} · 업데이트 {status.updated_at}</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">이번 주말, 우리 아이 어디 갈까?</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">서울 공공데이터로 날짜·나이·지역·비용 조건에 맞는 아이체험을 먼저 추려봅니다. '
    '최종 신청 가능 여부는 공식 예약/출처 링크에서 확인하세요.</div>',
    unsafe_allow_html=True,
)
if status.mode == "mixed_error":
    st.error("데이터 모드 오류입니다. 추천 계산을 중단합니다. 데이터 확인에서 API/원천 데이터를 다시 수집하세요.")
    st.stop()
elif status.mode != "api":
    st.warning("현재는 샘플 데이터 기반입니다. 실제 제출 전 서울시 OpenAPI 키를 연결해야 합니다. 샘플과 실제 데이터는 섞지 않습니다.")

with st.expander("데이터 확인", expanded=False):
    st.caption(f"{mode_title} · 업데이트 {status.updated_at} · {mode_note} 실제 회차별 잔여석과 신청 가능 여부는 공식 예약/출처 페이지에서 최종 확인해야 합니다.")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("API/원천 데이터 다시 수집", type="primary"):
            with st.spinner("서울시 공개 API 또는 fallback 데이터를 다시 빌드하는 중입니다..."):
                build(sample=False, force_refresh=True)
            load_data.clear()
            st.rerun()
    with c2:
        if st.button("샘플 데이터로 재생성"):
            build(sample=True)
            load_data.clear()
            st.rerun()
    with c3:
        st.caption("비공개 API, 로그인 후 데이터, 자동예약, 결제, 알림, DB 저장은 구현하지 않습니다.")
    render_quality_panel(programs, len(programs), status)

st.markdown('<div class="parent-panel">', unsafe_allow_html=True)
st.subheader("핵심 필터")
f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
with f1:
    child_age = st.selectbox("아이 나이", list(range(4, 13)), format_func=lambda x: f"{x}세", key="child_age_filter")
with f2:
    grade = st.selectbox("학년/단계", ["미취학", "초1", "초2", "초3", "초4", "초5", "초6"], key="grade_filter")
with f3:
    origin = st.selectbox("출발 자치구", SEOUL_DISTRICTS, key="origin_filter")
with f4:
    selected_day = st.date_input("날짜", min_value=date(2026, 1, 1), max_value=date(2026, 12, 31), key="selected_day_filter")

f5, f6, f7 = st.columns([1, 1, 1])
with f5:
    max_travel = st.slider("이동시간", 15, 75, step=5, format="%d분 이내", key="max_travel_filter")
with f6:
    fee_types = st.multiselect("비용", all_fee_types, key="fee_types_filter")
with f7:
    indoor_types = st.multiselect("실내/실외", all_indoor_types, key="indoor_types_filter")
st.markdown("#### 관심분야")
selected_interests = st.multiselect("관심분야를 고르면 추천 후보가 더 좁혀집니다", interest_options, key="categories_filter")

cta1, cta2, cta3 = st.columns([1.2, 1, 1.2])
with cta1:
    if st.button("추천 결과 보기", type="primary", use_container_width=True):
        st.session_state["filters_applied"] = True
        st.session_state["home_view"] = "전체 보기"
        st.session_state["result_notice"] = "추천 결과를 다시 계산했습니다. 오늘의 추천, 추천 후보 5곳, 대체 후보를 한 번에 펼쳐 보여드립니다."
with cta2:
    if st.button("조건 초기화", use_container_width=True):
        st.session_state["reset_filters_requested"] = True
        st.rerun()
with cta3:
    if st.button("이미 가본 곳 제외 설정", use_container_width=True):
        st.session_state["show_visited_section"] = True
        st.info("페이지 맨 아래에 '이미 가본 곳 제외 설정' 영역을 열었습니다. 설정 후 다시 추천 버튼을 눌러주세요.")
if st.session_state.get("visited_recalc_message"):
    st.success(st.session_state.pop("visited_recalc_message"))
st.markdown("</div>", unsafe_allow_html=True)

fee_types = tuple(fee_types or all_fee_types)
indoor_types = tuple(indoor_types or all_indoor_types)
categories = raw_categories_for_interests(selected_interests or interest_options, all_categories)
filters = ParentFilters(child_age, origin, selected_day, max_travel, fee_types, indoor_types, categories, grade)
enriched = add_recommendation_features(programs, filters)
visited_places = st.session_state.get("visited_places", [])
visited_programs = st.session_state.get("visited_programs", [])
visited_text = st.session_state.get("visited_text", "")
exclude_same_place = bool(st.session_state.get("exclude_same_place", True))
exclude_same_program = bool(st.session_state.get("exclude_same_program", True))
exclude_same_link = bool(st.session_state.get("exclude_same_link", True))
visited_mask = pd.Series(False, index=enriched.index)
if exclude_same_place and visited_places:
    visited_mask |= enriched["venue"].astype(str).isin(visited_places)
if exclude_same_program and visited_programs:
    visited_mask |= enriched["title"].astype(str).isin(visited_programs)
if visited_text.strip():
    pattern = visited_text.strip()
    visited_mask |= enriched["venue"].astype(str).str.contains(pattern, case=False, regex=False, na=False)
    visited_mask |= enriched["title"].astype(str).str.contains(pattern, case=False, regex=False, na=False)
if exclude_same_link and visited_programs:
    visited_links = set(enriched[enriched["title"].astype(str).isin(visited_programs)]["source_url"].astype(str))
    visited_mask |= enriched["source_url"].astype(str).isin(visited_links)
enriched["visited_excluded"] = visited_mask
if visited_mask.any():
    enriched.loc[visited_mask, "is_actionable"] = False
    enriched.loc[visited_mask, "hard_filter_reason"] = "이미 가본 곳"
    enriched.loc[visited_mask, "recommendation_reason"] = "이미 가본 곳으로 표시해 추천에서 제외했습니다."
available = available_now_candidates(enriched, filters)
closed = closed_or_uncertain_candidates(enriched, filters)
recommended = filter_recommendations(enriched, filters, include_extension=False)
extension = filter_recommendations(enriched, filters, include_extension=True)
extension = extension[~extension["program_id"].isin(recommended["program_id"]) & extension["date_match_level"].isin(["near_7_days", "wider_option"])]
funnel = condition_relaxation_counts(programs, filters)
funnel_png_path = FIGURES_DIR / "06_condition_relaxation_funnel.png"
if not funnel_png_path.exists():
    save_funnel_png(funnel)

today_pick = recommended.head(1)
seed = today_pick.iloc[0] if not today_pick.empty else None
if seed is not None:
    top_candidates = recommended[~recommended["program_id"].eq(seed["program_id"])].head(5)
else:
    top_candidates = recommended.head(5)
exact_available = recommended[recommended["date_match_level"].eq("exact_date")]
closed_now = closed[closed["date_match_level"].isin(["exact_date", "same_weekend"])]
backup = plan_b_candidates(enriched, seed, filters, limit=3) if seed is not None else recommended.iloc[1:4].copy()
low_friction = recommended[recommended["reservation_friction"].isin(["low", "medium"])]
excluded_total = int((~enriched.get("is_actionable", pd.Series(False, index=enriched.index))).sum())

if st.session_state.get("result_notice"):
    st.success(st.session_state.pop("result_notice"))

if seed is not None:
    st.markdown(
        f"""
        <div class="result-preview" id="recommendation-results">
          <div class="result-preview-title">현재 조건의 오늘의 추천은 ‘{seed['title']}’입니다.</div>
          <div class="result-preview-meta">
            {origin}에서 출발하는 {child_age}세 아이 기준, {selected_day:%m월 %d일} 조건으로 가장 먼저 확인할 후보입니다.<br>
            바로 아래 <strong>부모용 홈</strong>에서 공식 링크, 상세 확인, 대체 후보, 이미 가본 곳 제외를 이어서 선택할 수 있습니다.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pv1, pv2, pv3, pv4 = st.columns(4)
    with pv1:
        if st.button("오늘의 추천 보기", key="preview_today", use_container_width=True):
            st.session_state["home_view"] = "오늘의 추천"
            st.rerun()
    with pv2:
        if st.button("추천 후보 5곳 보기", key="preview_top5", use_container_width=True):
            st.session_state["home_view"] = "추천 후보 5곳"
            st.rerun()
    with pv3:
        if st.button("대체 후보 보기", key="preview_backup", use_container_width=True):
            st.session_state["home_view"] = "막혔을 때 갈 만한 곳"
            st.rerun()
    with pv4:
        if st.button("전체 지도 보기", key="preview_map", use_container_width=True):
            st.session_state["home_view"] = "전체 지도"
            st.rerun()
else:
    max_relaxed = int(funnel["candidate_count"].max()) if not funnel.empty else 0
    st.markdown(
        f"""
        <div class="result-preview" id="recommendation-results">
          <div class="result-preview-title">조건 그대로는 추천할 만한 곳이 없습니다.</div>
          <div class="result-preview-meta">
            날짜를 ±7일로 넓히거나 인접 자치구까지 보면 최대 {max_relaxed}개 후보를 다시 확인할 수 있습니다.
            아래 버튼으로 조건 확장 결과나 전체 지도를 먼저 볼 수 있습니다.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    ev1, ev2 = st.columns(2)
    with ev1:
        if st.button("조건을 넓히면 늘어나는 후보 보기", key="preview_relax", use_container_width=True):
            st.session_state["home_view"] = "조건 넓히기"
            st.rerun()
    with ev2:
        if st.button("전체 지도에서 보기", key="preview_empty_map", use_container_width=True):
            st.session_state["home_view"] = "전체 지도"
            st.rerun()

tab_home, tab_explore, tab_compare, tab_detail, tab_policy = st.tabs(["부모용 홈", "추천 탐색", "후보 비교", "상세 확인", "서울시 관점"])

with tab_home:
    if seed is not None:
        st.info(f"{origin}에서 출발하는 {child_age}세 아이 기준, {selected_day:%m월 %d일}에 가장 추천하는 곳은 '{seed['title']}'입니다.")
    else:
        max_relaxed = int(funnel["candidate_count"].max()) if not funnel.empty else 0
        st.warning(f"선택한 날짜와 조건 그대로는 추천할 만한 곳이 없습니다. 날짜를 ±7일로 넓히거나 인접 자치구까지 보면 {max_relaxed}개 후보가 생깁니다.")

    st.markdown("### 다음에 무엇을 볼까요?")
    quick_options = ["오늘의 추천", "추천 후보 5곳", "막혔을 때 갈 만한 곳", "추천하지 않은 이유", "조건 넓히기", "전체 지도", "이미 가본 곳 제외", "전체 보기"]
    quick_cols = st.columns(3)
    for idx, label in enumerate(quick_options):
        with quick_cols[idx % 3]:
            if st.button(label, key=f"quick_view_{idx}", use_container_width=True):
                st.session_state["home_view"] = label
                if label == "이미 가본 곳 제외":
                    st.session_state["show_visited_section"] = True
    home_view = st.session_state.get("home_view", "오늘의 추천")

    st.markdown("### 오늘의 결론")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="summary-card"><div class="summary-label">오늘의 추천</div><div class="summary-value">{"1곳" if seed is not None else "없음"}</div><span class="soft-note">가장 먼저 볼 곳</span></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="summary-card"><div class="summary-label">바로 확인할 수 있는 곳</div><div class="summary-value">{min(len(recommended), 99)}개</div><span class="soft-note">조건에 맞는 후보</span></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="summary-card"><div class="summary-label">신청 부담 낮은 대체 후보</div><div class="summary-value">{min(len(low_friction), 99)}개</div><span class="soft-note">공식 확인 후 판단하기 쉬운 후보</span></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="summary-card"><div class="summary-label">제외된 부적합 후보</div><div class="summary-value">{min(excluded_total, 999)}개</div><span class="soft-note">대상·요일·마감 등</span></div>', unsafe_allow_html=True)

    if home_view in {"오늘의 추천", "전체 보기"}:
        st.markdown("### 오늘의 추천 1곳")
        if seed is None:
            st.warning("조건 그대로는 추천할 만한 곳이 없습니다.")
            st.caption("날짜를 조금 넓히거나 인접 자치구까지 보면 후보가 생길 수 있습니다.")
            empty_c1, empty_c2, empty_c3, empty_c4 = st.columns(4)
            with empty_c1:
                if st.button("날짜 ±7일로 보기", use_container_width=True):
                    st.session_state["home_view"] = "조건 넓히기"
            with empty_c2:
                if st.button("인접 자치구 포함하기", use_container_width=True):
                    st.session_state["home_view"] = "조건 넓히기"
            with empty_c3:
                if st.button("조건 넓히기 보기", use_container_width=True):
                    st.session_state["home_view"] = "조건 넓히기"
            with empty_c4:
                if st.button("전체 지도 보기", use_container_width=True):
                    st.session_state["home_view"] = "전체 지도"
        else:
            render_today_recommendation_card(seed, filters)

    if home_view in {"추천 후보 5곳", "전체 보기"}:
        st.markdown("### 추천 후보 5곳")
        if top_candidates.empty:
            st.info("추천 후보 5곳으로 보여줄 후보가 없습니다.")
        else:
            cols = st.columns(2)
            for idx, (_, row) in enumerate(top_candidates.iterrows(), start=1):
                with cols[(idx - 1) % 2]:
                    render_program_card(row, idx, compact=(idx != 1), key_prefix="home_top5")
            remaining = max(0, len(recommended) - 1 - 5)
            if remaining:
                with st.expander(f"조건에 맞는 나머지 {remaining}개 더보기"):
                    more = recommended[~recommended["program_id"].isin(top_candidates["program_id"].tolist() + ([seed["program_id"]] if seed is not None else []))].head(20)
                    for idx, (_, row) in enumerate(more.iterrows(), start=6):
                        render_program_card(row, idx, compact=True, key_prefix="home_more")

    if home_view in {"막혔을 때 갈 만한 곳", "대체 후보", "전체 보기"}:
        st.markdown("### 첫 후보가 어려울 때 볼 곳")
        if backup.empty:
            st.info("현재 조건에서는 신청 부담이 낮은 대체 후보가 없습니다.")
        else:
            for idx, (_, row) in enumerate(backup.head(3).iterrows(), start=1):
                st.caption(row.get("planb_reason", row.get("backup_reason", "막혔을 때 갈 만한 대체 후보입니다.")))
                render_program_card(row, idx, compact=True, key_prefix="home_backup")

    if home_view in {"조건 넓히기", "전체 보기"}:
        st.markdown("### 조건을 넓히면 늘어나는 후보")
        st.info(best_relaxation_comment(funnel))
        st.plotly_chart(make_funnel_figure(funnel), width="stretch", config=plotly_config(), key="home_funnel")

    if home_view == "전체 지도":
        st.markdown("### 전체 지도")
        render_map(recommended.head(20))

    if home_view == "이미 가본 곳 제외":
        st.info("페이지 맨 아래의 '이미 가본 곳 제외 설정' 영역을 열었습니다. 설정 후 '이 설정으로 다시 추천 보기'를 눌러주세요.")

    if home_view in {"추천하지 않은 이유", "전체 보기"}:
        st.markdown("### 지금은 추천하지 않은 이유")
        if closed_now.empty and not visited_mask.any():
            st.success("현재 조건에서 별도로 설명할 제외 후보가 많지 않습니다.")
        else:
            excluded_view = pd.concat([closed_now.head(15), enriched[enriched["visited_excluded"]].head(10)], ignore_index=True).drop_duplicates("program_id")
            for bucket, part in excluded_view.groupby(excluded_view.apply(lambda row: row.get("hard_filter_reason") or row.get("schedule_filter_reason") or row.get("date_filter_reason") or row.get("availability_group"), axis=1)):
                with st.expander(str(bucket)[:40] or "확인 필요"):
                    for idx, (_, row) in enumerate(part.head(3).iterrows(), start=1):
                        render_program_card(row, idx, compact=True, key_prefix="home_excluded", show_excluded=True)
                    remaining_excluded = max(0, len(part) - 3)
                    if remaining_excluded:
                        st.caption(f"같은 이유로 제외된 후보 {remaining_excluded}개는 기본 화면에서 접어두었습니다.")

with tab_explore:
    st.subheader("추천 탐색")
    sort_option = st.radio("정렬", ["오늘의 추천 순", "가까운 순", "신청 부담 낮은 순", "무료/저비용 우선", "실내 우선"], horizontal=True)
    explore = recommended.head(20).copy()
    if sort_option == "가까운 순":
        explore = explore.sort_values(["travel_minutes", "status_priority", "recommend_score"], ascending=[True, True, False])
    elif sort_option == "신청 부담 낮은 순":
        explore = explore.sort_values(["reservation_friction", "date_rank", "travel_minutes"], ascending=[True, True, True])
    elif sort_option == "무료/저비용 우선":
        explore = explore.sort_values(["is_free_or_low", "fee", "status_priority"], ascending=[False, True, True])
    elif sort_option == "실내 우선":
        explore = explore.sort_values(["is_indoor", "status_priority", "travel_minutes"], ascending=[False, True, True])
    map_col, list_col = st.columns([1.2, 1])
    with map_col:
        render_map(explore.head(80))
    with list_col:
        if explore.empty:
            st.info("현재 조건에 맞는 지도/리스트 후보가 없습니다.")
        for rank, (_, row) in enumerate(explore.head(20).iterrows(), start=1):
            render_program_card(row, rank, compact=True, key_prefix="explore")

with tab_compare:
    st.subheader("후보 비교")
    compare_options = pd.concat([today_pick, backup.head(2), recommended.head(8)], ignore_index=True).drop_duplicates("program_id")
    if compare_options.empty:
        st.info("비교할 즉시 신청 가능 후보가 없습니다.")
    else:
        default_ids = compare_options["program_id"].head(3).tolist()
        chosen_ids = st.multiselect(
            "최대 3개 후보를 골라 비교하세요",
            compare_options["program_id"].tolist(),
            default=default_ids,
            max_selections=3,
            format_func=lambda pid: compare_options.loc[compare_options["program_id"].eq(pid), "title"].iloc[0],
        )
        compare_df = compare_options[compare_options["program_id"].isin(chosen_ids)].copy()
        if compare_df.empty:
            st.info("비교 후보를 선택하세요.")
        else:
            best = sort_recommendations(compare_df).iloc[0]
            st.success(f"가장 먼저 볼 후보는 {best['title']}입니다. 날짜·나이·비용 조건을 가장 잘 만족합니다.")
            table = pd.DataFrame({
                "구분": ["오늘의 추천" if idx == 0 else f"대체 후보 {idx}" for idx in range(len(compare_df))],
                "프로그램명": compare_df["title"],
                "날짜 일치": compare_df["date_match_badge"],
                "나이 적합": compare_df["age_fit"].map({True: "적합", False: "확인 필요"}),
                "신청 상태": compare_df["availability_group"],
                "신청 부담": compare_df.apply(difficulty_label, axis=1),
                "이동 난이도": compare_df["travel_difficulty"],
                "비용": compare_df.apply(fee_label, axis=1),
                "실내/실외": compare_df["indoor_outdoor"],
                "추천/대체 이유": compare_df["recommendation_reason"],
                "주의할 점": compare_df["caution_note"],
                "공식 링크": compare_df["source_url"].fillna("").replace("", "공식 확인 필요"),
            })
            st.caption("모바일에서는 표를 좌우로 밀어 비교할 수 있습니다.")
            st.dataframe(table, width="stretch", hide_index=True)
    st.markdown("### 조건을 넓히면 늘어나는 후보")
    st.plotly_chart(make_funnel_figure(funnel), width="stretch", config=plotly_config(), key="compare_funnel")

with tab_detail:
    st.subheader("상세 확인")
    st.caption("추천 이유와 주의할 점을 확인한 뒤 공식 링크로 이동하세요.")
    detail_pool = pd.concat([available, closed.head(6)], ignore_index=True).drop_duplicates("program_id")
    if detail_pool.empty:
        st.info("상세로 볼 후보가 없습니다.")
    else:
        selected_program_id = st.session_state.get("selected_program_id", detail_pool["program_id"].iloc[0])
        ids = detail_pool["program_id"].tolist()
        selected_program_id = st.selectbox(
            "상세로 볼 프로그램",
            ids,
            index=ids.index(selected_program_id) if selected_program_id in ids else 0,
            format_func=lambda pid: detail_pool.loc[detail_pool["program_id"].eq(pid), "title"].iloc[0],
        )
        selected = detail_pool[detail_pool["program_id"].eq(selected_program_id)].iloc[0]
        render_program_card(selected, 1, compact=True, key_prefix="detail")
        st.markdown("### 이용규칙 카드")
        render_rule_cards(selected)
        st.markdown("### 추천 이유와 주의할 점")
        cc1, cc2 = st.columns(2)
        cc1.success(selected["recommendation_reason"])
        cc2.warning(selected["caution_note"])
        st.caption("잔여석 관련 문구가 공개 상세 페이지에서 보이더라도 참고 정보로만 사용합니다.")
        st.markdown("### 주변/유사 대체안")
        alts = plan_b_candidates(enriched, selected, filters)
        if alts.empty:
            st.info("현재 조건에서는 바로 제안할 대체 후보가 없습니다.")
        else:
            for rank, (_, row) in enumerate(alts.iterrows(), start=1):
                st.caption(row["planb_reason"])
                render_program_card(row, rank, compact=True, key_prefix="detail_planb")

with tab_policy:
    st.subheader("서울시 관점 / 지역별 기회 보기")
    if status.mode != "api":
        st.warning("현재 서울시 관점 화면은 샘플 데이터 기반입니다. API 키 연결 후 실제 수집 결과로 재계산됩니다.")
    policy_age = st.radio("정책 지표 연령대", list(AGE_GROUPS.keys()), horizontal=True, index=1)
    insight_prefix = "API 수집 기준" if status.mode == "api" else "샘플 데이터 기준"
    for item in policy_summary(metrics, programs, policy_age):
        st.info(f"{insight_prefix}, {item}")

    st.markdown("### 정책 실행 브리프")
    st.caption("자치구 낙인이 아니라 우선 점검과 데이터 보완 방향을 제안합니다.")
    render_policy_action_cards(metrics, policy_age)

    st.markdown("### 무엇이 후보를 줄이는가")
    st.caption("부모 조건을 한 단계씩 적용할 때 후보 풀이 얼마나 줄어드는지 보여주는 제출용 병목 진단입니다.")
    st.plotly_chart(make_condition_loss_figure(programs, filters), width="stretch", config=plotly_config(), key="policy_condition_loss")

    st.markdown("### 우선 점검 매트릭스")
    st.caption("첫 선택 어려움과 대체 후보 부족을 함께 놓고, 이용장벽이 큰 지역을 크게 표시합니다.")
    st.plotly_chart(make_priority_matrix_current(metrics, policy_age), width="stretch", config=plotly_config(), key="policy_priority_current")

    st.markdown("### 빈 주말 캘린더")
    st.caption("선택가능도가 낮은 주말이 반복되는 자치구를 확인합니다.")
    st.plotly_chart(make_heatmap(weekly, policy_age), width="stretch", config=plotly_config())

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 연령별 블라인드 스팟")
        st.caption("연령대별로 공공체험 접근성이 다르게 나타나는 지역을 확인합니다.")
        st.plotly_chart(make_age_blindspot(metrics), width="stretch", config=plotly_config())
    with c2:
        st.markdown("### 자치구 유형화")
        st.caption("선택가능도와 대체 후보 충분도를 함께 보면 정책 우선순위 유형을 나눌 수 있습니다.")
        st.plotly_chart(make_policy_matrix(metrics, policy_age), width="stretch", config=plotly_config())

    st.markdown("### 대체 후보 충분도와 이용장벽")
    st.caption("첫 선택이 막혔을 때 인접구까지 확장해도 대체안이 부족한 지역과 비용·예약·연령·규칙 장벽을 비교합니다.")
    st.plotly_chart(make_barrier(metrics, policy_age), width="stretch", config=plotly_config())

    st.markdown("### 데이터 확인")
    render_quality_panel(programs, len(recommended), status)

st.markdown('<div class="parent-panel">', unsafe_allow_html=True)
st.markdown("### 이미 가본 곳 제외 설정")
st.caption("가본 장소나 프로그램을 선택하면 현재 추천 결과에서만 제외합니다. 저장하지 않고, 새로고침하면 초기화됩니다.")
if not st.session_state.get("show_visited_section", False):
    st.info("상단 필터의 '이미 가본 곳 제외 설정' 버튼을 누르면 이 영역을 열어 설정할 수 있습니다.")
with st.expander("가본 곳 선택하기", expanded=bool(st.session_state.get("show_visited_section", False))):
    st.multiselect("가본 장소명", sorted(programs["venue"].dropna().astype(str).unique().tolist())[:500], key="visited_places")
    st.multiselect("가본 프로그램명", sorted(programs["title"].dropna().astype(str).unique().tolist())[:500], key="visited_programs")
    st.text_input("장소나 프로그램 이름 직접 입력", placeholder="장소명 또는 프로그램명 일부를 입력", key="visited_text")
    visited_col1, visited_col2, visited_col3 = st.columns(3)
    with visited_col1:
        st.checkbox("같은 장소 제외", key="exclude_same_place")
    with visited_col2:
        st.checkbox("같은 프로그램 제외", key="exclude_same_program")
    with visited_col3:
        st.checkbox("같은 공식 링크 제외", key="exclude_same_link")
    if visited_mask.any():
        st.caption(f"현재 세션에서 이미 가본 곳 {int(visited_mask.sum())}개를 추천에서 제외했습니다.")
    visit_apply_col, visit_reset_col = st.columns([1.2, 1])
    with visit_apply_col:
        if st.button("이 설정으로 다시 추천 보기", type="primary", use_container_width=True):
            st.session_state["filters_applied"] = True
            st.session_state["show_visited_section"] = True
            st.session_state["home_view"] = "오늘의 추천"
            st.session_state["visited_recalc_message"] = f"이미 가본 곳 {int(visited_mask.sum())}개를 제외하고 추천을 다시 계산했습니다."
            st.rerun()
    with visit_reset_col:
        if st.button("선택 초기화", use_container_width=True):
            st.session_state["visited_places"] = []
            st.session_state["visited_programs"] = []
            st.session_state["visited_text"] = ""
            st.session_state["visited_recalc_message"] = "이미 가본 곳 제외 선택을 초기화했습니다."
            st.rerun()
    if visited_mask.any():
        with st.expander("제외된 후보 보기"):
            excluded_seen = enriched[enriched["visited_excluded"]].drop_duplicates("program_id").head(12)
            for idx, (_, row) in enumerate(excluded_seen.iterrows(), start=1):
                st.markdown(f"**{idx}. {row['title']}**  \n{row.get('venue', '장소 확인 필요')} · 이미 가본 곳으로 제외")
                if st.button("다시 포함", key=f"restore_seen_{row['program_id']}", use_container_width=True):
                    programs_seen = [value for value in st.session_state.get("visited_programs", []) if value != row["title"]]
                    places_seen = [value for value in st.session_state.get("visited_places", []) if value != row.get("venue")]
                    st.session_state["visited_programs"] = programs_seen
                    st.session_state["visited_places"] = places_seen
                    if row["title"] in st.session_state.get("visited_text", ""):
                        st.session_state["visited_text"] = ""
                    st.session_state["visited_recalc_message"] = "선택한 후보를 다시 포함했습니다."
                    st.rerun()
st.markdown("</div>", unsafe_allow_html=True)
