from datetime import date

from src.schedule_parser import classify_schedule_for_selected_date


def _row(title: str, start: str = "2026-04-01", end: str = "2026-11-30", **extra):
    return {
        "title": title,
        "date_start": start,
        "date_end": end,
        "time_text": extra.pop("time_text", ""),
        "target_text": extra.pop("target_text", "초등학생, 가족"),
        **extra,
    }


def test_wednesday_thursday_program_is_excluded_on_saturday():
    result = classify_schedule_for_selected_date(
        _row("[노원구 수락산 유아숲체험원] 체험프로그램(수, 목 오후 13:00~15:00)"),
        date(2026, 5, 16),
    )

    assert result["schedule_days_norm"] == ["wed", "thu"]
    assert result["schedule_match_level"] == "weekday_only_excluded"
    assert result["is_selected_date_eligible"] is False
    assert "수·목 운영" in result["schedule_filter_reason"]


def test_friday_program_is_excluded_on_saturday():
    result = classify_schedule_for_selected_date(
        _row("[노원구 태릉 유아숲체험원] 시설체험(금 오후 13:00~14:30)"),
        date(2026, 5, 16),
    )

    assert result["schedule_days_norm"] == ["fri"]
    assert result["schedule_match_level"] == "weekday_only_excluded"
    assert result["is_selected_date_eligible"] is False


def test_weekday_only_facility_is_excluded_on_saturday():
    result = classify_schedule_for_selected_date(
        _row("월드컵 보조경기장 평일주간"),
        date(2026, 5, 16),
    )

    assert result["schedule_days_norm"] == ["mon", "tue", "wed", "thu", "fri"]
    assert result["schedule_match_level"] == "weekday_only_excluded"
    assert result["is_selected_date_eligible"] is False


def test_weekend_and_daily_candidates_can_match_weekend_date():
    saturday = date(2026, 5, 16)

    saturday_program = classify_schedule_for_selected_date(_row("토요일 어린이 과학 체험"), saturday)
    weekend_program = classify_schedule_for_selected_date(_row("주말 가족 숲 체험"), date(2026, 5, 17))
    always_open = classify_schedule_for_selected_date(_row("상설 어린이 전시"), saturday)
    tue_to_sun = classify_schedule_for_selected_date(_row("화~일 운영 어린이 박물관"), saturday)

    assert saturday_program["is_selected_date_eligible"] is True
    assert weekend_program["is_selected_date_eligible"] is True
    assert always_open["is_selected_date_eligible"] is True
    assert tue_to_sun["is_selected_date_eligible"] is True


def test_monday_to_friday_range_is_excluded_on_saturday():
    result = classify_schedule_for_selected_date(
        _row("월~금 운영 창의교실"),
        date(2026, 5, 16),
    )

    assert result["schedule_match_level"] == "weekday_only_excluded"
    assert result["is_selected_date_eligible"] is False
