"""REAL Gemini inference verification. Separate from the mocked vision tests; makes billed API calls.

Skipped unless GEMINI_API_KEY is set. Images: every *.png / *.jpg in UNILINK_TIMETABLE_DIR (default:
backend/eval) that has a sibling <name>.truth.json written by a person who looked at the image
(never generated from model output). At least two DISTINCT images are required.

    GEMINI_API_KEY=... [GEMINI_MODEL=gemini-3.8-flash] python -m pytest backend/tests/test_gemini_live.py -q -s
    GEMINI_API_KEY=... UNILINK_TIMETABLE_DIR=/path/to/redacted_real_timetables python -m pytest backend/tests/test_gemini_live.py -q -s

Per image (see backend/eval/evaluate.py): ≥1 class extracted · weekday/course/start match the truth ·
no invented classes · unreadable fields left empty or flagged · inference_ms + token usage reported ·
API key never in the response. Printed results are the evidence; copy them verbatim into the log.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main, vision
from backend.eval.evaluate import evaluate, render

KEY = os.environ.get("GEMINI_API_KEY")
DIR = Path(os.environ.get("UNILINK_TIMETABLE_DIR") or Path(__file__).resolve().parents[1] / "eval")
IMAGES = sorted(p for p in DIR.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")
                and p.with_name(p.stem + ".truth.json").is_file())
pytestmark = pytest.mark.skipif(not KEY, reason="live Gemini test needs GEMINI_API_KEY (Replit Secret)")
RESULTS: dict[str, dict] = {}


def _mime(data: bytes) -> str:
    return "image/png" if data.startswith(b"\x89PNG") else "image/jpeg"


def test_at_least_two_distinct_images():
    digests = {hashlib.sha256(p.read_bytes()).hexdigest() for p in IMAGES}
    assert len(digests) >= 2, f"need ≥2 distinct images with truth files in {DIR}, found {len(digests)}"


@pytest.mark.parametrize("img", IMAGES, ids=[p.name for p in IMAGES])
def test_live_extraction_against_ground_truth(img: Path):
    data = img.read_bytes()
    truth = json.loads(img.with_name(img.stem + ".truth.json").read_text())
    assert truth and all(t.get("weekday") and t.get("course") for t in truth), "truth file must list real classes"
    model = vision.configured_model()
    with TestClient(main.app) as c:
        r = c.post("/api/timetable/parse", data={"session_id": f"live-{img.stem}"},
                   files={"image": (img.name, data, _mime(data))})
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:300]}"
    body = r.json()
    print(f"\n{img.name}: configured {model} (fallback {vision.fallback_model()}), API reported {body.get('model')}")
    assert body["classes"], "model returned no classes: an empty extraction never passes"
    assert body["inference_source"] == "gemini_vision" and body["source"] == "inference"
    allowed = [m for m in (model, vision.fallback_model()) if m]      # the fallback may answer on a 503/504/timeout
    assert any(str(body.get("model", "")).startswith(m) for m in allowed), \
        f"served model {body.get('model')!r} not in configured {allowed!r}"
    assert KEY not in r.text
    rep = evaluate(img.name, body, r.text, truth, KEY)
    RESULTS[img.stem] = r.json()
    print(render(rep))
    print("    extracted:", json.dumps(r.json()["classes"], ensure_ascii=False))
    print("    uncertain:", json.dumps(r.json()["uncertain_fields"], ensure_ascii=False))
    assert rep.passed, "\n".join(rep.problems)


def test_distinct_images_give_distinct_schedules():
    if len(RESULTS) < 2:
        pytest.skip("needs the per-image tests to have run")
    sigs = {k: tuple(sorted((c["weekday"], c["start"]) for c in v["classes"])) for k, v in RESULTS.items()}
    assert len(set(sigs.values())) == len(sigs), f"different images produced identical schedules: {sigs}"
