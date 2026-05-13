from __future__ import annotations

import re
import time
from html import unescape
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

DETAIL_URL_TEMPLATE = "https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id={svcid}"
_LAST_REQUEST_TS = 0.0


def reservation_detail_url(svcid: str) -> str:
    return DETAIL_URL_TEMPLATE.format(svcid=svcid)


def _strip_html(text: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _find_sentence(text: str, keywords: list[str], default: str = "공개 상세 페이지에서 확인 필요") -> str:
    for keyword in keywords:
        idx = text.find(keyword)
        if idx >= 0:
            start = max(0, idx - 40)
            end = min(len(text), idx + 130)
            return text[start:end].strip()
    return default


def parse_public_detail_page(url: str, *, timeout: int = 10) -> dict[str, Any]:
    global _LAST_REQUEST_TS
    elapsed = time.time() - _LAST_REQUEST_TS
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _LAST_REQUEST_TS = time.time()

    result = {
        "family_fit": "공개 상세 페이지에서 확인 필요",
        "preparation_note": "공개 상세 페이지에서 확인 필요",
        "cancel_rule": "공개 상세 페이지에서 확인 필요",
        "no_show_rule": "공개 상세 페이지에서 확인 필요",
        "capacity_text": "공개 상세 페이지 참고 정보 없음",
        "phone": "",
        "address": "",
        "detail_parse_status": "failed",
        "availability_confidence": "링크 확인 필요",
    }
    if not url:
        return result

    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 public-data-visualization/1.0"})
        with urlopen(req, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except URLError:
        return result
    except Exception:
        return result

    text = _strip_html(html)
    result.update({
        "family_fit": _find_sentence(text, ["보호자", "동반", "가족"], "보호자 동반 여부 확인 필요"),
        "preparation_note": _find_sentence(text, ["준비물", "지참", "복장"], "준비물 확인 필요"),
        "cancel_rule": _find_sentence(text, ["취소", "환불"], "취소 규칙 확인 필요"),
        "no_show_rule": _find_sentence(text, ["노쇼", "미참여", "불참"], "노쇼/미참여 규칙 확인 필요"),
        "capacity_text": _find_sentence(text, ["잔여", "정원", "모집인원"], "공개 상세 페이지 참고 정보 없음"),
        "detail_parse_status": "ok",
        "availability_confidence": "상세 확인",
    })
    phone = re.search(r"(0\d{1,2}-\d{3,4}-\d{4})", text)
    if phone:
        result["phone"] = phone.group(1)
    return result
