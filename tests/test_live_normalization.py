from src.build_all import normalize_culture_event_records, normalize_public_reservation_records


def test_public_reservation_live_normalization_schema():
    df = normalize_public_reservation_records([
        {
            "SVCID": "S123",
            "SVCNM": "어린이 과학 실험실",
            "MINCLASSNM": "교육",
            "GUNAME": "마포구",
            "PLACENM": "마포청소년센터",
            "USETGTINFO": "7~9세",
            "PAYATNM": "무료",
            "SVCSTATNM": "접수중",
            "SVCOPNBGNDT": "2026-05-16",
            "SVCOPNENDDT": "2026-05-16",
            "X": "126.9",
            "Y": "37.5",
        }
    ])

    row = df.iloc[0]
    assert row["program_id"] == "S123"
    assert row["source"] == "공공서비스예약"
    assert row["reservation_status_norm"] == "available"
    assert "yeyak.seoul.go.kr" in row["detail_url"]


def test_culture_event_live_normalization_uncertain_status():
    df = normalize_culture_event_records([
        {
            "TITLE": "가족 공연 체험",
            "CODENAME": "공연",
            "GUNAME": "종로구",
            "PLACE": "세종문화회관",
            "USE_TRGT": "어린이",
            "USE_FEE": "무료",
            "STRTDATE": "2026-05-16",
            "END_DATE": "2026-05-17",
            "ORG_LINK": "https://example.com/event",
        }
    ])

    row = df.iloc[0]
    assert row["source"] == "서울문화행사"
    assert row["reservation_status_norm"] in {"always_available", "unknown", "ended"}
    assert row["source_url"] == "https://example.com/event"

