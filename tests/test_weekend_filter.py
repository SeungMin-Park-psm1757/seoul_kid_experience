from datetime import date

import pandas as pd

from src.recommend import ParentFilters, add_recommendation_features, filter_recommendations


def test_weekend_top_candidates_do_not_include_known_weekday_patterns():
    programs = pd.DataFrame(
        [
            {
                "program_id": "good_weekend",
                "title": "주말 가족 숲 체험",
                "category": "교육체험",
                "district": "노원구",
                "venue": "숲체험장",
                "age_min": 6,
                "age_max": 9,
                "age_label": "6~9세",
                "target_text": "초등학생, 가족",
                "date_start": "2026-04-01",
                "date_end": "2026-11-30",
                "time_text": "",
                "fee": 0,
                "fee_type": "무료",
                "indoor_outdoor": "실외",
                "reservation_status_norm": "available",
                "availability_group": "지금 신청 가능",
                "source_url": "https://example.com/weekend",
                "rule_summary": "",
                "source": "공공서비스예약",
            },
            {
                "program_id": "suryaksan",
                "title": "[노원구 수락산 유아숲체험원] 체험프로그램(수, 목 오후 13:00~15:00)",
                "category": "교육체험",
                "district": "노원구",
                "venue": "수락산 유아숲체험원",
                "age_min": 4,
                "age_max": 12,
                "age_label": "4~12세",
                "target_text": "가족, 어린이, 유아, 초등학생",
                "date_start": "2026-04-22",
                "date_end": "2026-11-26",
                "time_text": "13:00",
                "fee": 0,
                "fee_type": "무료",
                "indoor_outdoor": "실외",
                "reservation_status_norm": "available",
                "availability_group": "지금 신청 가능",
                "source_url": "https://example.com/suryaksan",
                "rule_summary": "",
                "source": "공공서비스예약",
            },
            {
                "program_id": "taereung",
                "title": "[노원구 태릉 유아숲체험원] 시설체험(금 오후 13:00~14:30)",
                "category": "교육체험",
                "district": "노원구",
                "venue": "태릉 유아숲체험원",
                "age_min": 4,
                "age_max": 12,
                "age_label": "4~12세",
                "target_text": "가족, 어린이, 유아, 초등학생",
                "date_start": "2026-04-24",
                "date_end": "2026-11-27",
                "time_text": "13:00",
                "fee": 0,
                "fee_type": "무료",
                "indoor_outdoor": "실외",
                "reservation_status_norm": "available",
                "availability_group": "지금 신청 가능",
                "source_url": "https://example.com/taereung",
                "rule_summary": "",
                "source": "공공서비스예약",
            },
        ]
    )
    filters = ParentFilters(
        child_age=7,
        origin="노원구",
        selected_day=date(2026, 5, 16),
        max_travel=45,
        fee_types=("무료",),
        indoor_types=("실외",),
        categories=("교육체험",),
    )

    recommended = filter_recommendations(add_recommendation_features(programs, filters), filters)

    assert list(recommended["program_id"]) == ["good_weekend"]
