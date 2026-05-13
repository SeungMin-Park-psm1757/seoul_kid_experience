from src.category_groups import (
    available_interest_options,
    display_for_raw_category,
    normalize_selected_interests,
    raw_categories_for_interests,
)


def test_duplicate_source_categories_share_one_interest_label():
    assert display_for_raw_category("교육/체험") == "교육/체험"
    assert display_for_raw_category("교육체험") == "교육/체험"
    assert display_for_raw_category("전시/미술") == "전시/관람"
    assert display_for_raw_category("전시/관람") == "전시/관람"


def test_available_interest_options_do_not_show_duplicate_education_labels():
    options = available_interest_options(["교육/체험", "교육체험", "전시/미술", "전시/관람", "문화행사"])

    assert options.count("교육/체험") == 1
    assert "교육체험" not in options
    assert options.count("전시/관람") == 1
    assert "전시/미술" not in options


def test_selected_interest_expands_to_raw_source_categories():
    raw = raw_categories_for_interests(["교육/체험", "전시/관람"], ["교육/체험", "교육체험", "전시/미술", "전시/관람"])

    assert raw == ("교육/체험", "교육체험", "전시/미술", "전시/관람")


def test_existing_session_raw_values_are_migrated_to_display_labels():
    migrated = normalize_selected_interests(["교육/체험", "교육체험", "전시/미술"], ["교육/체험", "전시/관람"])

    assert migrated == ["교육/체험", "전시/관람"]
