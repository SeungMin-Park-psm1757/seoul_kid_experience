from __future__ import annotations

import re
from typing import Any


def district_from_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        match = re.search(r"([가-힣]+구)", text)
        if match:
            return match.group(1)
    return "확인 필요"


__all__ = ["district_from_text"]

