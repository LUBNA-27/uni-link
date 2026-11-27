"""Offline proof that the live-Gemini checker is not vacuous: it is fed hand-crafted model outputs
(through the real /api/timetable/parse pipeline with a FAKE client) and must PASS a faithful extraction and
FAIL invented classes, wrong times, silent guesses for unreadable fields, missing telemetry and key leaks.
No API call is made here; these are NOT inference results."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main, vision
from backend.eval.evaluate import evaluate

EVAL = Path(__file__).resolve().parents[1] / "eval"
SECRET = "AIza-TEST-SECRET-123"


class _Usage:
    prompt_token_count, candidates_token_count, total_token_count = 1290, 140, 1430


class _Resp:
    def __init__(self, payload, usage=True):
        self.parsed, self.text = None, json.dumps(payload)
        self.usage_metadata = _Usage() if usage else None


class _Client:
    def __init__(self, payload, usage=True):
        self.models, self.payload, self.usage = self, payload, usage

    def generate_content(self, **_):
        return _Resp(self.payload, self.usage)


def run(monkeypatch, image: str, payload: dict, usage: bool = True):
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    monkeypatch.setattr(vision, "client_factory", lambda: _Client(payload, usage))
    data = (EVAL / f"{image}.png").read_bytes()
    with TestClient(main.app) as c:
        r = c.post("/api/timetable/parse", data={"session_id": "eval-logic"}, files={"image": ("t.png", data, "image/png")})
    truth = json.loads((EVAL / f"{image}.truth.json").read_text())
    return evaluate(image, r.json(), r.text, truth, SECRET)


def gem(rows):
    return {"classes": [dict(zip(("day", "course", "start", "end", "building"), r)) for r in rows], "uncertain_fields": []}


FAITHFUL_A = [("Sunday", "CS 201 Data Structures", "08:30", "09:30", "Eng 102"),
              ("Sunday", "AI 305 Machine Learning", "11:30", "12:30", "IT 214"),
              ("Tuesday", "CS 250 Databases", "10:00", "11:00", "Eng 110")]


def test_faithful_extraction_passes(monkeypatch):
    rep = run(monkeypatch, "demo_A", gem(FAITHFUL_A))
    assert rep.passed, rep.problems
    assert rep.fields_correct == rep.fields_total == 9 and rep.usage["total_token_count"] == 1430


def test_invented_class_fails(monkeypatch):
    rep = run(monkeypatch, "demo_A", gem(FAITHFUL_A + [("Thursday", "AI 999 Ghost", "13:00", None, None)]))
    assert not rep.checks["no_invented"]


def test_wrong_start_time_fails(monkeypatch):
    rows = [FAITHFUL_A[0], ("Sunday", "AI 305 Machine Learning", "11:00", "12:30", "IT 214"), FAITHFUL_A[2]]
    rep = run(monkeypatch, "demo_A", gem(rows))
    assert not rep.checks["weekday_course_start"]


def test_wrong_weekday_fails(monkeypatch):
    rows = [FAITHFUL_A[0], FAITHFUL_A[1], ("Wednesday", "CS 250 Databases", "10:00", "11:00", "Eng 110")]
    assert not run(monkeypatch, "demo_A", gem(rows)).checks["weekday_course_start"]


def test_empty_extraction_fails(monkeypatch):
    rep = run(monkeypatch, "demo_A", {"classes": [], "uncertain_fields": []})
    assert not rep.checks["extracted_any"] and not rep.passed


def test_guessing_an_unreadable_time_fails(monkeypatch):
    rows = [("Monday", "MATH 241 Linear Algebra", "09:00", "10:00", None),
            ("Wednesday", "PHYS 102 General Physics", "12:00", "13:00", "Sci 12")]   # 12:00 is under the blot
    rep = run(monkeypatch, "demo_C", gem(rows))
    assert not rep.checks["unreadable_flagged"]


def test_flagging_the_unreadable_time_passes(monkeypatch):
    payload = gem([("Monday", "MATH 241 Linear Algebra", "09:00", "10:00", None),
                   ("Wednesday", "PHYS 102 General Physics", None, "13:00", "Sci 12")])
    payload["uncertain_fields"] = ["classes[1].start", "classes[0].building"]
    rep = run(monkeypatch, "demo_C", payload)
    assert rep.passed, rep.problems


def test_missing_telemetry_fails(monkeypatch):
    assert not run(monkeypatch, "demo_A", gem(FAITHFUL_A), usage=False).checks["telemetry"]


def test_secret_leak_is_detected():
    rep = evaluate("x", {"classes": [], "inference_source": "gemini_vision", "source": "inference"},
                   f'{{"oops":"{SECRET}"}}', [], SECRET)
    assert not rep.checks["no_secret"]


@pytest.mark.parametrize("name", ["demo_A", "demo_B", "demo_C"])
def test_eval_images_have_independent_truth(name):
    truth = json.loads((EVAL / f"{name}.truth.json").read_text())
    assert truth and all({"weekday", "course", "start"} <= set(t) for t in truth)
