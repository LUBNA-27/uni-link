"""LIVE Gemini timetable check (makes real, billed API calls; nothing is mocked).

    # server running with GEMINI_API_KEY in Replit Secrets:
    python -m backend.eval.gemini_eval https://<your-app>.replit.app      (or http://localhost:8000)

Uploads each backend/eval/*.png to /api/timetable/parse exactly as the frontend does (multipart field
"image"), then compares against the hand-written *.truth.json. Prints field-level accuracy, latency and
whether demo_A and demo_B give different first classes (Rev. E §19). Report the printed numbers as-is.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def upload(path: Path) -> tuple[int, dict, float]:
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"session_id\"\r\n\r\neval-{path.stem}\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/timetable/parse", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read()), (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), (time.perf_counter() - t0) * 1000


def main() -> None:
    """Remote version of backend/tests/test_gemini_live.py (same checker), for the deployed Replit URL."""
    import os
    from backend.eval.evaluate import evaluate, render
    reports = []
    for img in sorted(p for p in HERE.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")):
        tf = img.with_name(img.stem + ".truth.json")
        status, out, ms = upload(img)
        print(f"\n{img.name}: HTTP {status}, round trip {ms:.0f} ms")
        if status != 200:
            print("  ", out)
            continue
        if not tf.is_file():
            print("   (no truth file; not scored)")
            continue
        rep = evaluate(img.name, out, json.dumps(out), json.loads(tf.read_text()), os.environ.get("GEMINI_API_KEY"))
        reports.append(rep)
        print(render(rep))
    if reports:
        tot = sum(r.fields_total for r in reports)
        ok = sum(r.fields_correct for r in reports)
        print(f"\nSUMMARY: {sum(r.passed for r in reports)}/{len(reports)} images passed all checks; "
              f"weekday/course/start fields {ok}/{tot}")


if __name__ == "__main__":
    main()
