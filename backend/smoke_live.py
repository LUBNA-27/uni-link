"""Live end-to-end API smoke test over real HTTP (run against local uvicorn or the Replit URL).

    python -m backend.smoke_live                       # http://localhost:8000
    python -m backend.smoke_live https://<your-app>.replit.app

Journey: timetable confirm → Best Deal → booking → co-rider cancel → requester consent → peer consent
(Smart Rescue commit) → Class Shift → wallet reconciliation; then Zaid in a separate session:
WAV plan → WAV-01 unavailable → honest no_accessible_route. Prints measured timings; exits non-zero on failure.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
TIMINGS: list[tuple[str, float]] = []


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"FAIL {method} {path}: HTTP {e.code} {e.read()[:300]!r}") from None
    TIMINGS.append((f"{method} {path.split('?')[0]}", (time.perf_counter() - t0) * 1000))
    return out


def check(cond: bool, label: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        raise SystemExit(1)


def plan_req(s, **o):
    b = {"session_id": s, "rider_token": "R-7K2", "campus_id": "JUST", "zone_id": "irbid_east", "service_date": "2026-11-29",
         "class_start": "08:30", "arrival_buffer_min": 10, "pickup_mode": "door_to_door", "gender_pool": "female_only",
         "desired_companions": 3, "booking": "day_ahead", "preferred_pickup": "07:44", "fare_cap_fils": 2000,
         "accessibility": {"wheelchair": False, "big_car": False}, "sharing_opt_in": True}
    b.update(o)
    return b


def main() -> None:
    S = "smoke-" + uuid.uuid4().hex[:8]
    print(f"UniLink live smoke against {BASE}  (session {S})")
    h = call("GET", "/api/health")
    check(h["status"] == "ok" and h["source"] == "simulation", f"health ok, gemini_ready={h['gemini_ready']}")
    tt = [{"id": "c1", "course": "CS 201", "weekday": "Sun", "start": "08:30"},
          {"id": "c2", "course": "AI 305", "weekday": "Sun", "start": "11:30"}]
    check(call("POST", "/api/timetable/confirm", {"session_id": S, "classes": tt})["class_count"] == 2, "timetable confirmed")
    p = call("POST", "/api/plan", plan_req(S))
    bd1, bd2 = p["options"]
    check(p["status"] == "best_deal_proposed", "strict request → best_deal_proposed")
    check((bd1["fare"]["your_share_fils"], bd1["arrival"], bd1["utility"]) == (1860, "08:17", 85.25), "BD1 1860 / 08:17 / 85.25")
    check([x["share_fils"] for x in bd1["fare"]["shares"]] == [1860, 1380, 1260], "BD1 shares 1860+1380+1260 = 4500")
    check((bd2["fare"]["your_share_fils"], bd2["arrival"], bd2["utility"]) == (1565, "08:08", 80.0), "BD2 1565 / 08:08 / 80.00")
    r = call("POST", "/api/trips/confirm", {"session_id": S, "rider_token": "R-7K2", "plan_id": "BD1",
                                            "plan_revision": p["plan_revision"], "accepted_fare_fils": 1860,
                                            "idempotency_key": str(uuid.uuid4())})
    trip = r["trip_id"]
    check(r["status"] == "confirmed" and r["wallet"]["balance_fils"] == 10140, "booked BD1, wallet 12000 → 10140")
    st = call("POST", "/api/simulation/event", {"session_id": S, "event": "cancel", "target": "R-9TD", "sim_time": "06:55"})
    (pr,) = st["pending_proposals"]
    check(pr["proposal_id"] == "R2" and pr["plan"]["fare"]["your_share_fils"] == 1900 and pr["delta_fils"] == 40,
          "co-rider cancel 06:55 → Smart Rescue R2 1900 (+40)")
    a = call("POST", "/api/trips/confirm", {"session_id": S, "rider_token": "R-7K2", "plan_id": "R2",
                                            "plan_revision": pr["plan_revision"], "accepted_fare_fils": 1900,
                                            "idempotency_key": str(uuid.uuid4()), "decision": "accept"})
    check(a["status"] == "awaiting_consent" and a["wallet"]["balance_fils"] == 10140, "requester approved; nothing charged yet")
    st = call("POST", "/api/simulation/event", {"session_id": S, "event": "peer_consent"})
    check(st["pending_proposals"] == [] and st["wallet"]["balance_fils"] == 10100, "peers consented → committed, wallet 10100")
    sh = call("POST", "/api/trips/shift-class", {"session_id": S, "trip_id": trip, "rider_token": "R-7K2", "request_time": "07:05"})
    sp = sh["proposal"]
    check(sh["status"] == "shift_proposed" and sp["refund_fils"] == 1900 and sp["new_charge_fils"] == 1860,
          "class shift 07:05 → refund 1900 / new 1860")
    check([x["time"] for x in sp["plan"]["pickups"]] == ["10:47", "10:53", "10:58"] and sp["plan"]["arrival"] == "11:15",
          "11:30 class: pickups 10:47/10:53/10:58 → 11:15")
    d = call("POST", "/api/trips/confirm", {"session_id": S, "rider_token": "R-7K2", "plan_id": sp["plan"]["plan_id"],
                                            "plan_revision": sp["plan_revision"], "accepted_fare_fils": 1860,
                                            "idempotency_key": str(uuid.uuid4()), "decision": "accept",
                                            "replaces_trip_id": trip})
    check(d["status"] == "confirmed", "class shift committed atomically")
    st = call("GET", f"/api/simulation/state?session_id={S}")
    led = [(e["kind"], e["amount_fils"]) for e in st["wallet"]["ledger"]]
    check(st["wallet"]["balance_fils"] == 10140 and led == [("debit", 1860), ("debit", 40), ("refund", 1900), ("debit", 1860)],
          f"wallet reconciled 12000→10140→10100→10140, ledger {led}")

    Z = "smoke-z-" + uuid.uuid4().hex[:6]
    zreq = plan_req(Z, rider_token="R-W01", campus_id="AAU", zone_id="sweileh", class_start="09:00",
                    gender_pool="male_only", desired_companions=0, preferred_pickup="08:25", fare_cap_fils=3000,
                    accessibility={"wheelchair": True, "big_car": False})
    z = call("POST", "/api/plan", zreq)
    o = z["options"][0]
    check(o["vehicle"]["kind"] == "wav" and o["fare"]["your_share_fils"] == 2700 and o["arrival"] == "08:45",
          "Zaid (separate session) → WAV-01 2700, arrive 08:45")
    check(o["accessible_dropoff"]["verified"] is False, "accessible drop-off labeled synthetic / not verified")
    call("POST", "/api/simulation/event", {"session_id": Z, "event": "vehicle_unavailable", "target": "WAV-01"})
    z2 = call("POST", "/api/plan", zreq)
    check(z2["status"] == "no_accessible_route" and z2["options"] == [], "WAV-01 out → no_accessible_route, never a sedan")
    check(call("GET", f"/api/simulation/state?session_id={S}")["wallet"]["balance_fils"] == 10140, "Sara's session untouched by Zaid's")

    print("\nmeasured HTTP round-trips (ms):")
    for name, ms in TIMINGS:
        print(f"  {ms:7.1f}  {name}")
    print("SMOKE PASSED")


if __name__ == "__main__":
    main()
