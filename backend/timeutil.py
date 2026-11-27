"""HH:MM <-> minutes-since-midnight helpers (local Amman service-date time)."""
from __future__ import annotations

import re

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def is_hhmm(value: str) -> bool:
    return bool(_HHMM.match(value))


def to_min(value: str) -> int:
    m = _HHMM.match(value)
    if not m:
        raise ValueError(f"invalid HH:MM time: {value!r}")
    return int(m.group(1)) * 60 + int(m.group(2))


def to_hhmm(minutes: int) -> str:
    if not 0 <= minutes < 24 * 60:
        raise ValueError("time outside service day")
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
