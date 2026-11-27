"""Integration-contract tests: the EXACT request payloads the frontend builds (frontend/src/screens/*.tsx,
components/ConfirmSheet.tsx, components/DevDrawer.tsx), checked against the required keys of
frontend/src/types.ts. JSON.stringify drops `undefined`, so optional fields are simply omitted here too."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend import main

# required (non-optional) keys per interface in frontend/src/types.ts
REQUIRED = {
    "PlanResponse": {"session_id", "plan_revision", "status", "exact_match_found", "options", "requires_approval", "source"},
    "PlanOption": {"plan_id", "relaxed", "leave_home", "arrival", "pickup_order", "fare"},
    "Fare": {"your_share_fils", "vehicle_total_fils"},
    "Pickup": {"rider_token", "landmark", "time", "is_you"},
    "ConfirmResponse": {"session_id", "revision", "status", "source"},
    "Proposal": {"proposal_id", "kind", "message", "plan_revision", "plan", "delta_fils", "requires_approval", "consents"},
    "ConsentEntry": {"rider_token", "label", "state"},
    "SimState": {"session_id", "revision", "sim_time", "service_date", "trips", "pending_proposals", "wallet", "source"},
    "TripView": {"trip_id", "status", "class_start", "plan", "amount_paid_fils", "has_next_class"},
    "LedgerEntry": {"at", "kind", "amount_fils", "note"},
    "ShiftResponse": {"session_id", "revision", "status", "trip_id", "message", "source"},
    "EmergencyResponse": {"session_id", "revision", "status", "message", "source"},
    "TimetableResponse": {"session_id", "classes", "uncertain_fields", "inference_source", "source"},
    "TimetableConfirmResponse": {"session_id", "confirmed", "class_count", "invalidated_plans"},
    "ClassItem": {"id", "course", "weekday", "start"},
}
OPTIONAL_NUMERIC = ("utility", "hypothetical_reference_fils", "delta_vs_reference_fils", "previous_your_share_fils",
                    "refund_fils", "new_charge_fils", "amount_paid_fils")


def has(obj: dict, iface: str) -> dict:
    missing = REQUIRED[iface] - set(obj)
    assert not missing, f"{iface} missing {missing}"
    for k in OPTIONAL_NUMERIC:                           # `?:` fields must be absent, never null (UI checks !== undefined)
        assert obj.get(k, 0) is not None, f"{iface}.{k} is null"
    return obj


def check_option(o: dict) -> dict:
    has(o, "PlanOption")
    has(o["fare"], "Fare")
    for p in o.get("pickups", []):
        has(p, "Pickup")
    assert o["relaxed"] is None or isinstance(o["relaxed"], str)
    return o


def check_proposal(p: dict) -> dict:
    has(p, "Proposal")
    check_option(p["plan"])
    assert p["plan"]["plan_id"] == p["proposal_id"]       # Booked.tsx confirms with p.plan.plan_id
    for c in p["consents"]:
        has(c, "ConsentEntry")
    for a in p.get("alternatives", []):
        assert a["selectable"] is False
    return p


def check_state(st: dict) -> dict:
    has(st, "SimState")
    for t in st["trips"]:
        has(t, "TripView")
        check_option(t["plan"])
    for p in st["pending_proposals"]:
        check_proposal(p)
    for e in st["wallet"]["ledger"]:
        has(e, "LedgerEntry")
        assert e["kind"] in ("debit", "refund") and e["amount_fils"] > 0
    return st


@pytest.fixture()
def c(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    main.STORE.clear()
    with TestClient(main.app) as client:
        yield client


def new_key() -> str:            # format.ts newKey() → crypto.randomUUID()
    return str(uuid.uuid4())


# ---- payload builders copied from the frontend source ------------------------------------------------
def trip_tsx_plan(session_id, rider="R-7K2", zone="irbid_east", campus="JUST", date="2026-11-29", class_start="08:30",
                  buffer=10, pool="female_only", companions=3, pickup="07:44", cap=2000, wheelchair=False,
                  big_car=False, opt_in=True):
    return {"session_id": session_id, "rider_token": rider, "campus_id": campus, "zone_id": zone, "service_date": date,
            "class_start": class_start, "arrival_buffer_min": buffer, "pickup_mode": "door_to_door",
            "gender_pool": pool, "desired_companions": companions, "booking": "day_ahead", "preferred_pickup": pickup,
            "fare_cap_fils": cap, "accessibility": {"wheelchair": wheelchair, "big_car": big_car},
            "sharing_opt_in": opt_in}


def confirm_sheet(session_id, rider, option, plan_revision):
    return {"session_id": session_id, "rider_token": rider, "plan_id": option["plan_id"], "plan_revision": plan_revision,
            "accepted_fare_fils": option["fare"]["your_share_fils"], "idempotency_key": new_key()}


def booked_respond(session_id, rider, p, decision, trip_id=None):
    body = {"session_id": session_id, "rider_token": rider, "plan_id": p["plan"]["plan_id"],
            "plan_revision": p["plan_revision"], "accepted_fare_fils": p["plan"]["fare"]["your_share_fils"],
            "idempotency_key": new_key(), "decision": decision}
    if p["kind"] == "class_shift" and trip_id:
        body["replaces_trip_id"] = trip_id
    return body


SCHEDULE_ROWS = [  # Schedule.tsx manual rows (ids from blank(): `new-${Date.now()}-${seq}`)
    {"id": "new-1764250000000-0", "course": "CS 201 · Data Structures", "weekday": "Sun", "start": "08:30", "room": "Eng. 102"},
    {"id": "new-1764250000000-1", "course": "AI 305 · Machine Learning", "weekday": "Sun", "start": "11:30", "end": ""},
    {"id": "new-1764250000000-2", "course": "CS 250 · Databases", "weekday": "Tue", "start": "10:00"},
]


# ---- the P0 student journey ------------------------------------------------------------------------
def test_full_student_journey_wire_contract(c):
    S, ME = "s-ab12cd34", "R-7K2"                        # store.tsx auto session id format
    tt = c.post("/api/timetable/manual", json={"session_id": S, "classes": SCHEDULE_ROWS}).json()
    has(tt, "TimetableResponse")
    assert tt["inference_source"] == "manual" and [has(x, "ClassItem")["id"] for x in tt["classes"]] == [r["id"] for r in SCHEDULE_ROWS]
    ok = c.post("/api/timetable/confirm", json={"session_id": S, "classes": tt["classes"]}).json()
    assert has(ok, "TimetableConfirmResponse") == {"session_id": S, "confirmed": True, "class_count": 3, "invalidated_plans": False}

    check_state(c.get(f"/api/simulation/state?session_id={S}").json())            # Trip.tsx refreshSim() first
    plan = has(c.post("/api/plan", json=trip_tsx_plan(S)).json(), "PlanResponse")
    assert plan["status"] == "best_deal_proposed"
    bd1, bd2 = (check_option(o) for o in plan["options"])
    assert (bd1["fare"]["your_share_fils"], bd1["arrival"], bd1["utility"]) == (1860, "08:17", 85.25)
    assert [x["share_fils"] for x in bd1["fare"]["shares"]] == [1860, 1380, 1260]
    assert (bd2["fare"]["your_share_fils"], bd2["arrival"], bd2["utility"]) == (1565, "08:08", 80.0)

    r = has(c.post("/api/trips/confirm", json=confirm_sheet(S, ME, bd1, plan["plan_revision"])).json(), "ConfirmResponse")
    assert r["status"] == "confirmed" and r["amount_paid_fils"] == 1860 and r["wallet"]["balance_fils"] == 10140
    check_option(r["plan"])
    trip_id = r["trip_id"]

    # DevDrawer: "Companion C cancels @ 06:55"
    st = check_state(c.post("/api/simulation/event", json={"session_id": S, "event": "cancel", "target": "R-9TD",
                                                          "sim_time": "06:55"}).json())
    (p,) = st["pending_proposals"]
    assert p["kind"] == "smart_rescue" and p["plan"]["fare"]["your_share_fils"] == 1900 and p["delta_fils"] == 40
    assert {a["your_share_fils"] for a in p["alternatives"]} == {2490, 4260}

    # Booked.tsx Approve → awaiting the simulated co-riders
    a = has(c.post("/api/trips/confirm", json=booked_respond(S, ME, p, "accept")).json(), "ConfirmResponse")
    assert a["status"] == "awaiting_consent" and a["wallet"]["balance_fils"] == 10140
    assert [x["state"] for x in a["pending_consents"]] == ["accepted", "pending", "pending"]
    st = check_state(c.get(f"/api/simulation/state?session_id={S}").json())
    assert st["trips"][0]["status"] == "awaiting_consent"

    # DevDrawer: "Other riders consent (simulated)"
    st = check_state(c.post("/api/simulation/event", json={"session_id": S, "event": "peer_consent"}).json())
    assert st["pending_proposals"] == [] and st["wallet"]["balance_fils"] == 10100
    assert st["trips"][0]["amount_paid_fils"] == 1900 and st["trips"][0]["has_next_class"] is True

    # Booked.tsx "My first class was canceled" (request_time from the sim clock, edited to 07:05)
    sh = has(c.post("/api/trips/shift-class", json={"session_id": S, "trip_id": trip_id, "rider_token": ME,
                                                    "request_time": "07:05"}).json(), "ShiftResponse")
    assert sh["status"] == "shift_proposed"
    sp = check_proposal(sh["proposal"])
    assert sp["refund_fils"] == 1900 and sp["new_charge_fils"] == 1860 and sp["next_class"]["start"] == "11:30"
    assert [x["time"] for x in sp["plan"]["pickups"]] == ["10:47", "10:53", "10:58"] and sp["plan"]["arrival"] == "11:15"
    st = check_state(c.get(f"/api/simulation/state?session_id={S}").json())
    assert any(x["proposal_id"] == sp["proposal_id"] for x in st["pending_proposals"])

    done = has(c.post("/api/trips/confirm", json=booked_respond(S, ME, sp, "accept", trip_id)).json(), "ConfirmResponse")
    assert done["status"] == "confirmed" and done["wallet"]["balance_fils"] == 10140
    st = check_state(c.get(f"/api/simulation/state?session_id={S}").json())
    assert st["wallet"]["balance_fils"] == 10140 and st["pending_proposals"] == []
    assert [(e["kind"], e["amount_fils"]) for e in st["wallet"]["ledger"]] == [
        ("debit", 1860), ("debit", 40), ("refund", 1900), ("debit", 1860)]
    live = [t for t in st["trips"] if t["status"] != "canceled"]
    assert len(live) == 1 and live[0]["class_start"] == "11:30" and live[0]["amount_paid_fils"] == 1860

    # DevDrawer: Reset
    st = check_state(c.post("/api/simulation/event", json={"session_id": S, "event": "reset"}).json())
    assert st["revision"] == 1 and st["wallet"]["balance_fils"] == 12000


def test_zaid_separate_session_wav_then_no_option(c):
    S = "s-zaid0001"
    req = trip_tsx_plan(S, rider="R-W01", zone="sweileh", campus="AAU", class_start="09:00", pool="male_only",
                        companions=0, pickup="08:25", cap=3000, wheelchair=True)   # DevDrawer.loadZaid()
    plan = has(c.post("/api/plan", json=req).json(), "PlanResponse")
    o = check_option(plan["options"][0])
    assert plan["status"] == "exact_match" and o["vehicle"]["kind"] == "wav" and o["vehicle"]["wheelchair_accessible"]
    assert o["fare"]["your_share_fils"] == 2700 and o["arrival"] == "08:45"
    assert o["accessible_dropoff"]["verified"] is False
    # DevDrawer: "WAV-01 unavailable" sends no sim_time
    check_state(c.post("/api/simulation/event", json={"session_id": S, "event": "vehicle_unavailable",
                                                      "target": "WAV-01"}).json())
    p2 = has(c.post("/api/plan", json=req).json(), "PlanResponse")
    assert p2["status"] == "no_accessible_route" and p2["options"] == [] and p2["reason"] and p2["assistance"]


def test_sara_session_unaffected_by_zaid_session(c):
    c.post("/api/plan", json=trip_tsx_plan("s-zaid0002", rider="R-W01", zone="sweileh", campus="AAU",
                                           class_start="09:00", pool="male_only", companions=0, pickup="08:25",
                                           cap=3000, wheelchair=True))
    st = check_state(c.get("/api/simulation/state?session_id=s-sara0002").json())
    assert st["revision"] == 1 and st["wallet"]["balance_fils"] == 12000


def test_emergency_payload_from_trip_tsx(c):
    S = "s-emg00001"
    c.post("/api/timetable/confirm", json={"session_id": S, "classes": [
        {"id": "m1", "course": "Monday class", "weekday": "Mon", "start": "08:30"}]})
    body = {"session_id": S, "rider_token": "R-7K2", "campus_id": "JUST", "zone_id": "irbid_east",
            "service_date": "2026-11-30", "class_start": "08:30", "arrival_buffer_min": 10, "request_time": "07:58",
            "gender_pool": "female_only", "fare_cap_fils": 2000, "accessibility": {"wheelchair": False, "big_car": False},
            "sharing_opt_in": True}
    r = has(c.post("/api/trips/emergency", json=body).json(), "EmergencyResponse")
    assert r["status"] == "emergency_proposed" and r["newcomer_fare_fils"] == 1575
    p = check_proposal(r["proposal"])
    ok = c.post("/api/trips/confirm", json={"session_id": S, "rider_token": "R-7K2", "plan_id": p["plan"]["plan_id"],
                                             "plan_revision": p["plan_revision"],
                                             "accepted_fare_fils": p["plan"]["fare"]["your_share_fils"],
                                             "idempotency_key": new_key()}).json()
    assert ok["status"] == "confirmed" and ok["wallet"]["balance_fils"] == 12000 - 1575
    st = check_state(c.get(f"/api/simulation/state?session_id={S}").json())
    assert st["trips"][0]["plan"]["fare"]["your_share_fils"] == 1575


def test_stale_409_matches_api_ts_parser(c):
    S = "s-stale001"
    plan = c.post("/api/plan", json=trip_tsx_plan(S)).json()
    c.post("/api/simulation/event", json={"session_id": S, "event": "traffic", "target": "all"})
    r = c.post("/api/trips/confirm", json=confirm_sheet(S, "R-7K2", plan["options"][0], plan["plan_revision"]))
    body = r.json()
    d = body.get("detail", body)                          # api.ts: (data.detail ?? data)
    assert r.status_code == 409 and d["code"] == "STALE_REVISION" and d["current_revision"] == 2
    assert isinstance(d["message"], str)


def test_cancel_only_payload_from_booked_tsx(c):
    S = "s-cancel01"
    c.post("/api/timetable/confirm", json={"session_id": S, "classes": SCHEDULE_ROWS[:1]})
    plan = c.post("/api/plan", json=trip_tsx_plan(S)).json()
    r = c.post("/api/trips/confirm", json=confirm_sheet(S, "R-7K2", plan["options"][0], plan["plan_revision"])).json()
    st = c.get(f"/api/simulation/state?session_id={S}").json()
    sh = c.post("/api/trips/shift-class", json={"session_id": S, "trip_id": r["trip_id"], "rider_token": "R-7K2",
                                                 "request_time": "07:05"}).json()
    assert sh["status"] == "no_next_class" and sh["cancel_only"]["refund_fils"] == 1860
    st = c.get(f"/api/simulation/state?session_id={S}").json()
    trip = next(t for t in st["trips"] if t["status"] != "canceled")
    cx = c.post("/api/trips/confirm", json={"session_id": S, "rider_token": "R-7K2", "plan_id": trip["plan"]["plan_id"],
                                             "plan_revision": st["revision"], "accepted_fare_fils": 0,
                                             "idempotency_key": new_key(), "decision": "cancel_trip"}).json()
    assert has(cx, "ConfirmResponse")["status"] == "canceled" and cx["wallet"]["balance_fils"] == 12000


def test_parse_accepts_frontend_field_name_image(c):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    r = c.post("/api/timetable/parse", data={"session_id": "s-parse001"}, files={"image": ("tt.png", png, "image/png")})
    assert r.status_code == 503 and r.json()["code"] == "VISION_UNAVAILABLE"   # honest: no key → no fake inference
