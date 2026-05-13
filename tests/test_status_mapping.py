from src.normalize_status import normalize_reservation_status


def test_live_status_mapping_available_and_closed():
    assert normalize_reservation_status("접수중").norm == "available"
    assert normalize_reservation_status("예약가능").group == "지금 신청 가능"
    assert normalize_reservation_status("상시 자유이용").norm == "always_available"
    assert normalize_reservation_status("접수마감").norm == "full"
    assert normalize_reservation_status("행사종료").group == "행사 종료"
    assert normalize_reservation_status("").norm == "unknown"

