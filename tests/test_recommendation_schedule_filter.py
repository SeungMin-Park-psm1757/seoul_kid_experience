from datetime import date

import pandas as pd

from src.recommend import ParentFilters, add_recommendation_features, filter_recommendations, plan_b_candidates


def _filters() -> ParentFilters:
    return ParentFilters(
        child_age=7,
        origin="노원구",
        selected_day=date(2026, 5, 16),
        max_travel=60,
        fee_types=("무료",),
        indoor_types=("실내", "실외"),
        categories=("교육체험",),
    )


def _program(pid: str, title: str, *, day_text: str = "", status: str = "available") -> dict:
    return {
        "program_id": pid,
        "title": title,
        "category": "교육체험",
        "district": "노원구",
        "venue": "노원 체험공간",
        "age_min": 6,
        "age_max": 9,
        "age_label": "6~9세",
        "target_text": "초등학생, 가족",
        "date_start": "2026-04-01",
        "date_end": "2026-11-30",
        "time_text": day_text,
        "fee": 0,
        "fee_type": "무료",
        "indoor_outdoor": "실내",
        "reservation_status_norm": status,
        "availability_group": "지금 신청 가능",
        "source_url": f"https://example.com/{pid}",
        "rule_summary": "",
        "source": "공공서비스예약",
    }


def test_default_recommendations_exclude_weekday_only_schedule_on_weekend():
    programs = pd.DataFrame(
        [
            _program("sat", "토요일 어린이 과학 체험"),
            _program("wed_thu", "[노원구 수락산 유아숲체험원] 체험프로그램(수, 목 오후 13:00~15:00)"),
            _program("fri", "[노원구 태릉 유아숲체험원] 시설체험(금 오후 13:00~14:30)"),
            _program("weekday", "월드컵 보조경기장 평일주간"),
        ]
    )

    enriched = add_recommendation_features(programs, _filters())
    recommended = filter_recommendations(enriched, _filters())

    assert set(recommended["program_id"]) == {"sat"}
    excluded = enriched.set_index("program_id")
    assert excluded.loc["wed_thu", "schedule_match_level"] == "weekday_only_excluded"
    assert excluded.loc["fri", "schedule_match_level"] == "weekday_only_excluded"
    assert excluded.loc["weekday", "schedule_match_level"] == "weekday_only_excluded"


def test_backup_candidates_use_same_schedule_hard_filter():
    programs = pd.DataFrame(
        [
            _program("seed", "토요일 어린이 과학 체험"),
            _program("backup", "상설 어린이 전시"),
            _program("weekday_backup", "월~금 운영 창의교실"),
        ]
    )

    enriched = add_recommendation_features(programs, _filters())
    selected = enriched[enriched["program_id"].eq("seed")].iloc[0]
    backup = plan_b_candidates(enriched, selected, _filters())

    assert "backup" in set(backup["program_id"])
    assert "weekday_backup" not in set(backup["program_id"])


def test_map_default_pool_can_use_recommended_without_weekday_items():
    programs = pd.DataFrame(
        [
            _program("sat", "토요일 어린이 과학 체험"),
            _program("weekday", "월~금 운영 창의교실"),
        ]
    )

    recommended = filter_recommendations(add_recommendation_features(programs, _filters()), _filters())
    map_default = recommended.head(20)

    assert set(map_default["program_id"]) == {"sat"}
    assert map_default["is_selected_date_eligible"].all()
