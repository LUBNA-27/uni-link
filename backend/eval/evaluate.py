"""Scores one /api/timetable/parse response against an independently written ground truth.

Ground truth (`<image>.truth.json`): list of {weekday, course, start, end?, room?}. A field that is
missing or unreadable IN THE IMAGE is written as null; for those the model must either leave the field
empty or flag it in uncertain_fields, never invent a value.

Checks (each is a hard pass/fail):
  extracted_any      ≥ 1 class was extracted
  weekday/course/start  every truth class is matched with the correct weekday, course and start
  no_invented        every extracted class corresponds to a truth class
  unreadable_flagged every null truth field is empty or flagged, and every empty extracted field is flagged
  telemetry          inference_ms > 0 and usage.total_token_count > 0 were reported
  no_secret          the response text does not contain the API key
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


def norm(v: Any) -> str:
    return " ".join(re.sub(r"[^0-9a-z؀-ۿ]+", " ", str(v or "").lower()).split())


def course_match(truth: str, got: str) -> bool:
    t, g = norm(truth), norm(got)
    return bool(t) and bool(g) and (t == g or t in g or g in t)


@dataclass
class Report:
    image: str
    checks: dict[str, bool] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    fields_total: int = 0
    fields_correct: int = 0
    inference_ms: Optional[float] = None
    usage: Optional[dict[str, int]] = None

    @property
    def passed(self) -> bool:
        return all(self.checks.values())

    def fail(self, check: str, msg: str) -> None:
        self.checks[check] = False
        self.problems.append(f"{check}: {msg}")


def evaluate(image: str, resp: dict[str, Any], raw_text: str, truth: list[dict[str, Any]],
             secret: Optional[str]) -> Report:
    r = Report(image, {k: True for k in ("extracted_any", "weekday_course_start", "no_invented",
                                         "unreadable_flagged", "telemetry", "no_secret", "source_honest")})
    got: list[dict[str, Any]] = resp.get("classes", [])
    flagged = {(u["class_id"], u["field"]) for u in resp.get("uncertain_fields", [])}
    r.inference_ms, r.usage = resp.get("inference_ms"), resp.get("usage")

    if resp.get("inference_source") != "gemini_vision" or resp.get("source") != "inference":
        r.fail("source_honest", f"inference_source={resp.get('inference_source')} source={resp.get('source')}")
    if not got:
        r.fail("extracted_any", "no classes extracted")
    if secret and secret in raw_text:
        r.fail("no_secret", "API key appears in the response")
    if not (isinstance(r.inference_ms, (int, float)) and r.inference_ms > 0):
        r.fail("telemetry", "inference_ms missing")
    if not (r.usage and r.usage.get("total_token_count", 0) > 0):
        r.fail("telemetry", "usage.total_token_count missing")

    used: set[int] = set()
    for ti, t in enumerate(truth):
        cand = [i for i, g in enumerate(got) if i not in used and g.get("weekday") == t["weekday"]
                and ((t.get("start") and g.get("start") == t["start"])
                     or (not t.get("start") and course_match(t["course"], g.get("course", ""))))]
        if not cand:
            cand = [i for i, g in enumerate(got) if i not in used and course_match(t["course"] or "", g.get("course", ""))]
        if not cand:
            r.fail("weekday_course_start", f"truth class {ti + 1} ({t['weekday']} {t.get('start')} {t['course']}) not found")
            r.fields_total += 3
            continue
        gi = cand[0]
        used.add(gi)
        g = got[gi]
        for f in ("weekday", "course", "start"):
            tv = t.get(f)
            if tv is None:
                continue
            r.fields_total += 1
            ok = course_match(tv, g.get(f, "")) if f == "course" else g.get(f) == tv
            r.fields_correct += ok
            if not ok:
                r.fail("weekday_course_start", f"class {ti + 1}.{f}: expected {tv!r}, got {g.get(f)!r}")
        for f in ("course", "start", "end", "room"):
            if f in t and t[f] is None and g.get(f) and (g["id"], f) not in flagged:
                r.fail("unreadable_flagged", f"class {ti + 1}.{f} is unreadable in the image but the model returned "
                                             f"{g.get(f)!r} without flagging it")
    for i, g in enumerate(got):
        if i not in used:
            r.fail("no_invented", f"extracted class not in the image: {g.get('weekday')} {g.get('start')} {g.get('course')!r}")
        for f in ("course", "start"):
            if not g.get(f) and (g["id"], f) not in flagged:
                r.fail("unreadable_flagged", f"{g['id']}.{f} is empty but not flagged for review")
    return r


def render(r: Report) -> str:
    lines = [f"[{'PASS' if r.passed else 'FAIL'}] {r.image}: fields {r.fields_correct}/{r.fields_total}, "
             f"inference {r.inference_ms} ms, usage {r.usage}"]
    lines += [f"    {k}: {'ok' if v else 'FAIL'}" for k, v in r.checks.items()]
    lines += [f"    - {p}" for p in r.problems]
    return "\n".join(lines)
