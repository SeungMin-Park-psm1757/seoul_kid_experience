import pandas as pd

from src.normalize import load_and_normalize_raw, read_csv_with_fallback


def test_read_csv_with_fallback_handles_cp949(tmp_path):
    path = tmp_path / "public_service.csv"
    pd.DataFrame([{"서비스명": "어린이 과학 체험", "자치구": "종로구"}]).to_csv(path, index=False, encoding="cp949")

    df = read_csv_with_fallback(path)

    assert df.loc[0, "서비스명"] == "어린이 과학 체험"


def test_load_and_normalize_raw_keeps_unified_schema(tmp_path):
    path = tmp_path / "공공서비스예약.csv"
    pd.DataFrame([
        {
            "서비스명": "토요 미술 교실",
            "자치구": "마포구",
            "장소": "마포구립미술관",
            "이용대상": "7~9세",
            "이용요금": "무료",
            "시작일": "2026-03-07",
            "서비스상태": "예약 가능",
        }
    ]).to_csv(path, index=False, encoding="utf-8-sig")

    out = load_and_normalize_raw(tmp_path)

    assert out.loc[0, "district"] == "마포구"
    assert out.loc[0, "week"] == 10
    assert {"title", "district", "age_min", "age_max", "fee_type"}.issubset(out.columns)
