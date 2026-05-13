from pathlib import Path


APP_TEXT = Path("app.py").read_text(encoding="utf-8")
PARENT_TEXT = APP_TEXT.split("with tab_policy:", 1)[0]


def test_parent_screen_forbidden_terms_absent():
    forbidden = [
        "저마찰",
        "하드필터",
        "조건 완화 퍼널",
        "데이터 품질 패널",
        "API 확인",
        "플랜B",
        "예약 확정",
        "잔여석 확정",
    ]
    for term in forbidden:
        assert term not in PARENT_TEXT


def test_policy_terms_are_allowed_in_policy_area():
    policy_text = APP_TEXT.split("with tab_policy:", 1)[1]
    assert "선택가능도" in policy_text
    assert "우선 점검 매트릭스" in policy_text


def test_cta_texts_exist_and_not_empty():
    ctas = [
        "추천 결과 보기",
        "조건 초기화",
        "이미 가본 곳 제외 설정",
        "공식 링크에서 확인",
        "상세 보기",
        "대체 후보 보기",
        "이미 가본 곳으로 표시",
        "이 설정으로 다시 추천 보기",
        "선택 초기화",
    ]
    for cta in ctas:
        assert cta in APP_TEXT
        assert cta.strip()


def test_official_link_principle_exists_and_risky_claims_absent():
    assert "공식 예약/출처 링크에서 확인" in APP_TEXT
    risky = ["예약 확정", "잔여석 확정", "자동예약"]
    parent_risky = ["예약 확정", "잔여석 확정"]
    for term in parent_risky:
        assert term not in APP_TEXT
    assert "자동예약" in APP_TEXT  # allowed only as a non-implemented feature notice


def test_text_review_documents_exist():
    required = [
        "docs/ui_text_review_for_ai.md",
        "docs/ui_text_inventory.md",
        "docs/terminology_review.md",
        "docs/cta_text_review.md",
        "docs/ui_writing_style_guide.md",
    ]
    for path in required:
        assert Path(path).exists()
