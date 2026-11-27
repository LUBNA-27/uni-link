"""Timetable-frequency predictor (rule-based heuristic, NOT a trained model). Suggests tomorrow's first
class from the cached confirmed timetable; it never books automatically."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any, Optional

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def suggest_tomorrow(timetable: Optional[list[dict[str, Any]]], today: date) -> Optional[dict[str, str | bool]]:
    if not timetable:
        return None
    tomorrow = today + timedelta(days=1)
    day = DAY_NAMES[tomorrow.weekday()]
    starts = sorted(c["start"] for c in timetable if c.get("day") == day and c.get("start"))
    if not starts:
        return {"day": day, "suggest_booking": False, "reason": "no class in cached timetable",
                "method": "timetable_frequency_rule", "auto_booking": False}
    weekly = Counter(c["start"] for c in timetable if c.get("start"))
    first = starts[0]
    return {"day": day, "service_date": tomorrow.isoformat(), "first_class": first, "suggest_booking": True,
            "weekly_occurrences": str(weekly[first]), "method": "timetable_frequency_rule", "auto_booking": False}
