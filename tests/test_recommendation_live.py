from datetime import date

import pandas as pd

from src.recommend import ParentFilters, add_recommendation_features, filter_recommendations, plan_b_candidates


def _filters() -> ParentFilters:
    return ParentFilters(
        child_age=7,
        origin="마포구",
        selected_day=date(2026, 5, 16),
        max_travel=60,
        fee_types=("무료", "저비용"),
        indoor_types=("실내", "혼합"),
        categories=("교육", "공연"),
    )


def test_not_for_selected_date_is_not_in_default_recommendations():
    programs = pd.DataFrame([
        {
            "program_id": "near",
            "title": "어린이 과학 실험실",
            "category": "교육",
            "district": "마포구",
            "venue": "마포청소년센터",
            "age_min": 7,
            "age_max": 9,
            "age_label": "7~9세",
            "date_start": "2026-05-16",
            "date_end": "2026-05-16",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/near",
        },
        {
            "program_id": "future",
            "title": "가을 박물관 탐험",
            "category": "교육",
            "district": "마포구",
            "venue": "박물관",
            "age_min": 7,
            "age_max": 9,
            "age_label": "7~9세",
            "date_start": "2026-09-16",
            "date_end": "2026-09-16",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/future",
        },
    ])
    enriched = add_recommendation_features(programs, _filters())
    recommended = filter_recommendations(enriched, _filters())

    assert "near" in set(recommended["program_id"])
    assert "future" not in set(recommended["program_id"])
    assert set(recommended["date_match_level"]).issubset({"exact_date", "same_weekend"})


def test_exact_date_outranks_same_weekend_for_today_pick():
    programs = pd.DataFrame([
        {
            "program_id": "same_weekend",
            "title": "가족 미술 워크숍",
            "category": "교육",
            "district": "마포구",
            "venue": "센터",
            "age_min": 7,
            "age_max": 9,
            "age_label": "7~9세",
            "date_start": "2026-05-17",
            "date_end": "2026-05-17",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/weekend",
        },
        {
            "program_id": "exact",
            "title": "어린이 과학 실험실",
            "category": "교육",
            "district": "마포구",
            "venue": "센터",
            "age_min": 7,
            "age_max": 9,
            "age_label": "7~9세",
            "date_start": "2026-05-16",
            "date_end": "2026-05-16",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/exact",
        },
    ])
    recommended = filter_recommendations(add_recommendation_features(programs, _filters()), _filters())

    assert recommended.iloc[0]["program_id"] == "exact"
    assert recommended.iloc[0]["date_match_level"] == "exact_date"


def test_plan_b_excludes_selected_program():
    programs = pd.DataFrame([
        {
            "program_id": "a",
            "title": "가족 미술 워크숍",
            "category": "교육",
            "district": "마포구",
            "venue": "센터",
            "age_min": 7,
            "age_max": 9,
            "age_label": "7~9세",
            "date_start": "2026-05-16",
            "date_end": "2026-05-16",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/a",
        },
        {
            "program_id": "b",
            "title": "도서관 창의 독서교실",
            "category": "교육",
            "district": "서대문구",
            "venue": "도서관",
            "age_min": 7,
            "age_max": 9,
            "age_label": "7~9세",
            "date_start": "2026-05-17",
            "date_end": "2026-05-17",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/b",
        },
    ])
    enriched = add_recommendation_features(programs, _filters())
    selected = enriched[enriched["program_id"].eq("a")].iloc[0]
    plan_b = plan_b_candidates(enriched, selected, _filters())

    assert "a" not in set(plan_b["program_id"])
    assert "b" in set(plan_b["program_id"])


def test_heavy_general_public_topic_is_excluded_for_lower_elementary_child():
    programs = pd.DataFrame([
        {
            "program_id": "heavy",
            "title": "문예북송 No.61 - 『5.18 푸른 눈의 증인』 폴 코트라이트가 증언하고 우리가 기억해야 할 오월의 광주",
            "category": "교육/체험",
            "district": "은평구",
            "venue": "이호철북콘서트홀",
            "age_min": 0,
            "age_max": 99,
            "age_label": "누구나",
            "target_text": "누구나",
            "date_start": "2026-05-16",
            "date_end": "2026-05-16",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "always_available",
            "availability_group": "신청 부담 낮음",
            "source_url": "https://example.com/heavy",
        },
        {
            "program_id": "child",
            "title": "어린이 과학 실험실",
            "category": "교육/체험",
            "district": "마포구",
            "venue": "어린이센터",
            "age_min": 7,
            "age_max": 9,
            "age_label": "7~9세",
            "target_text": "초등학생",
            "date_start": "2026-05-16",
            "date_end": "2026-05-16",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/child",
        },
    ])
    filters = ParentFilters(7, "마포구", date(2026, 5, 16), 60, ("무료",), ("실내",), ("교육/체험",))
    enriched = add_recommendation_features(programs, filters)
    recommended = filter_recommendations(enriched, filters)

    assert "heavy" not in set(recommended["program_id"])
    heavy = enriched[enriched["program_id"].eq("heavy")].iloc[0]
    assert bool(heavy["child_content_fit"]) is False
    assert heavy["content_difficulty"] == "hard"


def test_recommendations_are_deduplicated_by_program_series():
    programs = pd.DataFrame([
        {
            "program_id": "may",
            "title": "(토,일) 5월 불암산나비정원 곤충아카데미-장수풍뎅이 표본교실-",
            "category": "자연/과학",
            "district": "노원구",
            "venue": "불암산 나비정원",
            "age_min": 7,
            "age_max": 12,
            "age_label": "초등학생",
            "target_text": "초등학생",
            "date_start": "2026-05-01",
            "date_end": "2026-05-31",
            "time_text": "토,일 11:00",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/may",
        },
        {
            "program_id": "june",
            "title": "(토,일) 6월 불암산나비정원 곤충아카데미-장수풍뎅이 표본교실-",
            "category": "자연/과학",
            "district": "노원구",
            "venue": "불암산 나비정원",
            "age_min": 7,
            "age_max": 12,
            "age_label": "초등학생",
            "target_text": "초등학생",
            "date_start": "2026-05-01",
            "date_end": "2026-06-30",
            "time_text": "토,일 11:00",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/june",
        },
    ])
    filters = ParentFilters(7, "노원구", date(2026, 5, 16), 60, ("무료",), ("실내",), ("자연/과학",))
    recommended = filter_recommendations(add_recommendation_features(programs, filters), filters)

    assert len(recommended) == 1


def test_grade_specific_program_is_excluded_when_grade_is_too_low():
    programs = pd.DataFrame([
        {
            "program_id": "grade_3_6",
            "title": "(3~6학년) Guro 월드컵 : 우리들만의 국가대표",
            "category": "교육체험",
            "district": "구로구",
            "venue": "구로센터",
            "age_min": 7,
            "age_max": 12,
            "age_label": "초등학생",
            "target_text": "초등 3~6학년",
            "date_start": "2026-05-16",
            "date_end": "2026-05-16",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/grade",
        },
        {
            "program_id": "grade_2",
            "title": "초등 저학년 어린이 과학 실험실",
            "category": "교육체험",
            "district": "구로구",
            "venue": "구로센터",
            "age_min": 7,
            "age_max": 9,
            "age_label": "초등학생",
            "target_text": "초등 1~3학년",
            "date_start": "2026-05-16",
            "date_end": "2026-05-16",
            "fee": 0,
            "fee_type": "무료",
            "indoor_outdoor": "실내",
            "reservation_status_norm": "available",
            "availability_group": "지금 신청 가능",
            "source_url": "https://example.com/grade2",
        },
    ])
    filters = ParentFilters(
        7,
        "마포구",
        date(2026, 5, 16),
        60,
        ("무료",),
        ("실내",),
        ("교육체험",),
        grade="초2",
    )
    enriched = add_recommendation_features(programs, filters)
    recommended = filter_recommendations(enriched, filters)

    assert "grade_3_6" not in set(recommended["program_id"])
    assert "grade_2" in set(recommended["program_id"])
    excluded = enriched[enriched["program_id"].eq("grade_3_6")].iloc[0]
    assert bool(excluded["grade_fit"]) is False
