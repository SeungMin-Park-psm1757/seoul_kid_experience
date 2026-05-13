from datetime import date

import pandas as pd

from src.curation_rules import classify_reservation_friction, classify_weekday, normalize_target_audience
from src.recommend import ParentFilters, add_recommendation_features, filter_recommendations, plan_b_candidates


def test_target_filter_excludes_youth_adult_pet_but_keeps_child_animal_education():
    assert normalize_target_audience("청년정책 네트워크", "청년", "기타").suitability == "excluded"
    assert normalize_target_audience("성인 목공 교실", "성인", "공예").suitability == "excluded"
    assert normalize_target_audience("반려견 산책교실", "반려견", "공원").suitability == "excluded"
    assert normalize_target_audience("어린이 동물보호교육", "초등학생", "교육체험").suitability == "eligible"


def test_general_public_without_child_context_is_review_needed():
    result = normalize_target_audience("구민 강의실 대관", "제한없음", "강의실", age_min=0, age_max=99)
    assert result.suitability in {"review_needed", "excluded"}


def test_weekend_filter_excludes_weekday_and_keeps_weekend_or_always():
    selected = date(2026, 5, 16)
    assert classify_weekday("평일 유아 단체 프로그램", selected_day=selected)["date_weekday_match"] is False
    assert classify_weekday("토,일 가족 체험", selected_day=selected)["date_weekday_match"] is True
    assert classify_weekday("상시 전시 관람", selected_day=selected)["date_weekday_match"] is True


def _program(pid, title, target, status="available", weekday_word="토요일", category="교육체험"):
    return {
        "program_id": pid,
        "title": title,
        "category": category,
        "district": "마포구",
        "venue": "마포센터",
        "age_min": 0,
        "age_max": 99,
        "age_label": target,
        "target_text": target,
        "date_start": "2026-05-16",
        "date_end": "2026-05-16",
        "time_text": weekday_word,
        "fee": 0,
        "fee_type": "무료",
        "indoor_outdoor": "실내",
        "reservation_status_norm": status,
        "availability_group": "지금 신청 가능",
        "source_url": f"https://example.com/{pid}",
        "rule_summary": "",
        "source": "공공서비스예약",
    }


def test_curation_top_recommendations_exclude_bad_targets_and_weekdays():
    programs = pd.DataFrame([
        _program("good", "어린이 과학 실험실", "초등학생", weekday_word="토요일"),
        _program("youth", "청년정책 네트워크", "청년", weekday_word="토요일"),
        _program("pet", "반려견 산책교실", "반려견", weekday_word="토요일"),
        _program("weekday", "평일 유아 체험", "유아", weekday_word="평일"),
    ])
    filters = ParentFilters(7, "마포구", date(2026, 5, 16), 45, ("무료",), ("실내",), ("교육체험",))
    enriched = add_recommendation_features(programs, filters)
    recommended = filter_recommendations(enriched, filters)

    assert list(recommended["program_id"]) == ["good"]


def test_child_specific_candidate_outranks_broad_general_public():
    programs = pd.DataFrame([
        _program("general", "전시해설 예약", "제한없음", weekday_word="토요일", category="전시/관람"),
        _program("child", "어린이 과학 실험실", "초등학생", weekday_word="토요일", category="교육체험"),
    ])
    filters = ParentFilters(
        7,
        "마포구",
        date(2026, 5, 16),
        45,
        ("무료",),
        ("실내",),
        ("전시/관람", "교육체험"),
    )
    recommended = filter_recommendations(add_recommendation_features(programs, filters), filters)

    assert recommended["program_id"].iloc[0] == "child"


def test_elementary_filter_excludes_infant_group_only_programs():
    programs = pd.DataFrame([
        _program("good", "어린이 과학 실험실", "초등학생", weekday_word="토요일"),
        _program("infant_group", "유아 단체 숲체험", "유아 단체", weekday_word="토요일", category="산림여가"),
        _program("kindergarten", "정원탐험 유아 단체", "유치원 또는 어린이집 기관", weekday_word="토요일", category="산림여가"),
    ])
    filters = ParentFilters(
        7,
        "마포구",
        date(2026, 5, 16),
        45,
        ("무료",),
        ("실내", "실외"),
        ("교육체험", "산림여가"),
    )
    recommended = filter_recommendations(add_recommendation_features(programs, filters), filters)

    assert set(recommended["program_id"]) == {"good"}


def test_backup_candidates_exclude_selected_and_prefer_low_friction():
    programs = pd.DataFrame([
        _program("seed", "어린이 박물관 탐험", "초등학생", status="available"),
        _program("alt", "상시 가족 전시 관람", "가족", status="always_available", weekday_word="상시"),
        _program("closed", "정원마감 체험", "초등학생", status="full"),
    ])
    filters = ParentFilters(7, "마포구", date(2026, 5, 16), 45, ("무료",), ("실내",), ("교육체험",))
    enriched = add_recommendation_features(programs, filters)
    selected = enriched[enriched["program_id"].eq("seed")].iloc[0]
    backup = plan_b_candidates(enriched, selected, filters)

    assert "seed" not in set(backup["program_id"])
    assert "alt" in set(backup["program_id"])
    assert "closed" not in set(backup["program_id"])


def test_reservation_difficulty_signal():
    assert classify_reservation_friction(pd.Series({"reservation_status_norm": "always_available", "title": "상시 전시"}))["reservation_difficulty"] == "easy"
    assert classify_reservation_friction(pd.Series({"reservation_status_norm": "closing_soon", "title": "마감임박"}))["reservation_difficulty"] == "hard"
    assert classify_reservation_friction(pd.Series({"reservation_status_norm": "unknown", "title": "확인 필요"}))["reservation_difficulty"] == "unknown"


def test_no_confirmed_capacity_wording_in_app():
    text = open("app.py", encoding="utf-8").read()
    assert ("확정 " + "잔여석") not in text
    assert "오늘의 추천" in text
    assert "대체 후보" in text
    assert "조건을 넓히면 늘어나는 후보" in text


def test_mobile_interaction_ctas_exist():
    text = open("app.py", encoding="utf-8").read()
    assert text.count("이번 주말, 우리 아이 어디 갈까?") == 1
    assert "SEOUL KID EXPERIENCE CURATOR" not in text
    assert "추천 결과 보기" in text
    assert "조건 초기화" in text
    assert "이미 가본 곳 제외 설정" in text
    assert "이 설정으로 다시 추천 보기" in text
    assert "공식 링크에서 확인" in text
    assert "대체 후보 보기" in text
    assert "이미 가본 곳으로 표시" in text
    assert "flex-wrap: wrap" in text
    assert "@media (max-width: 760px)" in text
