"""Thin compatibility layer: frontend contract (contract.py) ⇄ engine (replanner/state/schemas).

No matching, routing or pricing happens here; every number comes from the engine. This module only
(1) converts request shapes, (2) renders engine results as the frontend's types, and (3) implements
the contract-level decisions (decline / cancel_trip / proposal-scoped peer consent) on top of the
engine's existing commit functions.
"""
from __future__ import annotations

import time
from datetime import date
from typing import Any, Optional

from . import contract as C
from . import replanner, schemas, vision
from .errors import ApiError
from .replanner import DAY_NAMES, Engine
from .state import PendingPlan, Session, Trip
from .timeutil import to_hhmm, to_min

ZONE_LABEL = {"irbid_east": "Irbid East", "irbid_nuzha": "Irbid Nuzha", "sweileh": "Sweileh"}
ABBR = {"Sunday": "Sun", "Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu"}
FULL = {v: k for k, v in ABBR.items()}
ACCESS_SOURCE = "Simulation fixture (synthetic) — not a verified real-world campus fact"
FIELD_MAP = {"day": "weekday", "building": "room", "course": "course", "start": "start", "end": "end"}
ALT_LABEL = {"R1": "Continue with remaining riders", "R2": "Re-match replacement riders", "R3": "Re-timed departure",
             "SOLO": "Ride alone"}
DEFAULT_DATE = "2026-11-29"


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 3)


# ============================================================================ timetable
def class_out(c: dict[str, Any]) -> C.ClassItemOut:
    return C.ClassItemOut(id=c["id"], course=c.get("course") or "", weekday=ABBR[c["day"]], start=c.get("start") or "",
                          end=c.get("end") or None, room=c.get("building") or None)


def classes_from_request(items: list[C.ClassItem], require_start: bool) -> list[dict[str, Any]]:
    out = []
    for c in items:
        if require_start and not c.start:
            raise ApiError(422, "VALIDATION_ERROR", f"class {c.id} needs a start time")
        out.append({"id": c.id, "day": FULL[c.weekday], "course": c.course or None, "start": c.start or None,
                    "end": c.end or None, "building": c.room or None})
    return out


def parse_response(s: Session, classes: list[schemas.TimetableClass], uncertain: list[str],
                   usage: Optional[dict[str, int]] = None, inference_ms: Optional[float] = None,
                   model: Optional[str] = None) -> C.TimetableResponse:
    kept, id_of = [], {}
    for i, c in enumerate(classes):
        if c.day not in ABBR:                       # Fri/Sat are not in the Sun–Thu contract
            continue
        cid = f"c{len(kept) + 1}"
        id_of[i] = cid
        kept.append({"id": cid, "day": c.day, "course": c.course, "start": c.start, "end": c.end, "building": c.building})
    unc = []
    for path in uncertain:
        idx, field = path.split("[", 1)[1].split("].")
        if int(idx) in id_of and field in FIELD_MAP:
            unc.append(C.UncertainField(class_id=id_of[int(idx)], field=FIELD_MAP[field],
                                        reason="The model was not sure about this field. Please check it."))
    s.timetable_draft = kept
    return C.TimetableResponse(session_id=s.session_id, classes=[class_out(c) for c in kept], uncertain_fields=unc,
                               inference_source="gemini_vision", model=model or vision.configured_model(), source="inference",
                               inference_ms=inference_ms, usage=usage or None)


def manual(s: Session, req: C.TimetableRequest) -> C.TimetableResponse:
    rows = classes_from_request(list(req.classes), require_start=False)
    s.timetable_draft = rows
    unc = [C.UncertainField(class_id=r["id"], field="start", reason="Start time is required.")
           for r in rows if not r["start"]]
    return C.TimetableResponse(session_id=s.session_id, classes=[class_out(r) for r in rows], uncertain_fields=unc,
                               inference_source="manual", source="simulation")


def confirm_timetable(s: Session, req: C.TimetableRequest) -> C.TimetableConfirmResponse:
    rows = classes_from_request(list(req.classes), require_start=True)
    changed = s.timetable != rows
    invalidated = False
    if changed:
        stale = [k for k, p in s.pending.items() if p.kind in ("quote", "class_shift") and p.status == "pending"]
        for k in stale:
            del s.pending[k]
        if stale:
            s.bump()                                 # older plan_revision values now return 409
            invalidated = True
        s.timetable = rows
    s.timetable_draft = None
    return C.TimetableConfirmResponse(session_id=s.session_id, confirmed=True, class_count=len(rows),
                                      invalidated_plans=invalidated)


# ============================================================================ plan option rendering
def _letters(n: int) -> str:
    return "BCDEFG"[n] if n < 6 else str(n)


def option_out(s: Session, opt: schemas.PlanOption, viewer: str, *, best_deal: bool = False,
               plan_id: Optional[str] = None, new_tokens: frozenset[str] = frozenset(),
               extra_flags: tuple[str, ...] = ()) -> C.PlanOption:
    fx = s.fx
    vr = fx.riders.get(viewer) or fx.riders[opt.pickup_order[0]]
    zone = ZONE_LABEL.get(vr["zone_id"], vr["zone_id"])
    members = [fx.riders[t] for t in opt.pickup_order if t in fx.riders]
    chair = any(m.get("wheelchair") for m in members) or opt.vehicle_class == "wav"
    pickups = []
    for i, p in enumerate(opt.pickups):
        if opt.mode == "main_road_shuttle":
            lm = f"Meet point · {zone} (synthetic)" if p.token == viewer else f"Meet point · rider {i + 1} (synthetic)"
        elif p.token == viewer:
            lm = f"Ramp-accessible pickup · {zone} (synthetic)" if chair else f"Your door · {zone} (synthetic)"
        elif p.token in new_tokens:
            lm = f"Replacement rider {_letters(i - 1)} · {zone} (synthetic)"
        else:
            lm = f"Companion {_letters(i - 1)} · {zone} (synthetic)"
        pickups.append(C.Pickup(rider_token=p.token, landmark=lm, time=p.pickup_time, is_you=p.token == viewer))
    f = opt.fare
    kind = opt.vehicle_class if opt.vehicle_class in ("sedan", "big_car", "wav") else "sedan"
    label = {"sedan": "Standard car · 4 seats", "big_car": "Big Car · 6 seats",
             "wav": f"{opt.vehicle_id or 'WAV'} · ramp vehicle (2 seats + 1 wheelchair)"}[kind]
    if opt.mode == "main_road_shuttle" and opt.shuttle:
        label = f"Feeder car + shuttle {opt.shuttle.shuttle_id}"
    pool = "Female-only pool" if vr["gender_pool"] == "female_only" else "Male-only pool"
    hard = [pool]
    if kind == "wav":
        hard += ["Ramp vehicle (simulated fixture)", "WAV capacity 2 + 1 wheelchair"]
    elif kind == "big_car":
        hard.append("Big Car capacity ≤ 6")
    else:
        hard.append("Capacity ≤ 4")
    if opt.deadline:
        hard.append(f"Meets class deadline {opt.deadline}")
    if opt.bookable:
        hard.append("Within your fare cap")
    if opt.shuttle:
        hard.append(f"Transfer buffer ≥ {opt.shuttle.transfer_buffer_min} min")
    flags = [opt.cap_status] if opt.cap_status != "within_cap" else []
    flags += list(extra_flags)
    return C.PlanOption(
        plan_id=plan_id or opt.plan_id, relaxed=opt.relaxed if best_deal else None,
        utility=opt.utility if best_deal else None, leave_home=opt.leave_home, arrival=opt.arrival,
        deadline=opt.deadline, pickup_order=list(opt.pickup_order), pickups=pickups,
        fare=C.Fare(your_share_fils=f.your_share_fils,
                    shares=[C.FareShare(rider_token=x.token, share_fils=x.share_fils) for x in f.shares],
                    vehicle_total_fils=f.vehicle_total_fils, hypothetical_reference_fils=f.hypothetical_reference_fils,
                    delta_vs_reference_fils=f.delta_vs_reference_fils),
        vehicle=C.Vehicle(kind=kind, label=label, wheelchair_accessible=kind == "wav"),
        accessible_dropoff=C.AccessibleDropoff(label=f"Step-free drop-off at the {_campus(opt, members)} gate",
                                               source=ACCESS_SOURCE, verified=False) if chair else None,
        hard_filters_passed=hard, flags=flags or None)


def _campus(opt: schemas.PlanOption, members: list[dict[str, Any]]) -> str:
    return members[0]["campus_id"] if members else "campus"


# ============================================================================ plan
def plan(s: Session, req: C.PlanRequest) -> C.PlanResponse:
    if req.booking == "on_demand":
        raise ApiError(422, "USE_EMERGENCY_ENDPOINT", "on-demand rides use /api/trips/emergency")
    if not req.sharing_opt_in and req.desired_companions > 0:
        raise ApiError(422, "SHARING_NOT_OPTED_IN", "turn on ride sharing to look for companions")
    internal = schemas.PlanRequest(**req.model_dump(exclude={"booking"}), booking="day_ahead")
    r = replanner.plan(s, internal)
    best = r.status == "best_deal_proposed"
    opts = [option_out(s, o, req.rider_token, best_deal=best) for o in r.options]
    comps = [option_out(s, o, req.rider_token, best_deal=True) for o in r.unbookable_comparisons]
    reason = assistance = None
    if r.status == "no_accessible_route":
        reason = C.Reason(code="NO_ACCESSIBLE_VEHICLE",
                          message="No wheelchair-accessible vehicle meets your class deadline right now.")
        assistance = C.Assistance(message="We never offer a car without a ramp. A UniLink operator can arrange "
                                          "assistance. This is a simulated hand-off; nothing is dispatched.")
    elif r.status == "no_feasible_route":
        codes = ", ".join(sorted(r.audit.rejections_by_code)) or "none"
        reason = C.Reason(code="NO_FEASIBLE_ROUTE",
                          message=f"No route meets every rule you set. Engine rejection codes: {codes}.")
        assistance = C.Assistance(message="Try another class time or fare cap. An operator can help; "
                                          "nothing is booked automatically.")
    return C.PlanResponse(session_id=r.session_id, plan_revision=r.plan_revision, status=r.status,
                          exact_match_found=r.exact_match_found, options=opts, reason=reason, assistance=assistance,
                          requires_approval=r.requires_approval, unbookable_comparisons=comps,
                          rejected=[C.RejectionOut(**x.model_dump()) for x in r.rejected], compute_ms=r.compute_ms,
                          audit=r.audit)


# ============================================================================ proposals
def _consents(s: Session, p: PendingPlan, viewer: str) -> list[C.ConsentEntry]:
    declined = p.extra.get("declined", set())
    trip = s.trips.get(p.trip_id) if p.trip_id else None
    old_members = set(trip.members) if trip else set()
    out = []
    for t in p.affected:
        if t == viewer:
            label = "You"
        elif t not in old_members:
            label = "Replacement rider (simulated)"
        else:
            label = f"Co-rider {t} (simulated)"
        state = "declined" if t in declined else "accepted" if t in p.consents else "pending"
        out.append(C.ConsentEntry(rider_token=t, label=label, state=state))
    return out


def _message(s: Session, p: PendingPlan) -> str:
    at = to_hhmm(p.extra.get("at", s.sim_min))
    if p.kind == "class_shift":
        return (f"Your {p.extra.get('old_class', '')} class is canceled. Your next class is "
                f"{p.request.get('class_start', '')}. Here is a new group for it.")
    if p.kind == "emergency":
        return "A same-pool trip already on the road can pick you up on its way."
    return {"rider_cancel": f"A companion canceled at {at}. Here is the best plan that still meets every rule.",
            "traffic": f"Traffic changed at {at}. Your pickup times need to move to keep your deadline.",
            "shuttle_full": f"Your shuttle became full at {at}. Your feeder car can continue to campus.",
            "vehicle_unavailable": f"Your vehicle became unavailable at {at}.",
            "co_rider_class_shift": "A co-rider moved to another class. Here is a revised plan for this trip.",
            "co_rider_canceled_trip": "A co-rider canceled this trip. Here is a revised plan."}.get(
        p.trigger, f"Your plan changed at {at}.")


def proposal_out(s: Session, p: PendingPlan, viewer: str) -> Optional[C.Proposal]:
    if p.option is None:
        return None
    old = p.old_fares.get(viewer)
    new = p.new_fares.get(viewer, p.option.fare.your_share_fils)
    new_tokens = frozenset(t for t in p.option.pickup_order if p.trip_id in s.trips
                           and t not in s.trips[p.trip_id].members) if p.kind == "smart_rescue" else frozenset()
    plan_view = option_out(s, p.option, viewer, plan_id=p.plan_id, new_tokens=new_tokens)
    alts = []
    for a in p.alternatives:
        alts.append(C.ProposalAlternative(label=ALT_LABEL.get(a.plan_id, a.relaxed or a.plan_id),
                                          your_share_fils=a.fare.your_share_fils,
                                          delta_fils=a.fare.your_share_fils - (old or 0),
                                          flags=[a.cap_status] if a.cap_status != "within_cap" else None,
                                          selectable=False))
    nxt = None
    if p.kind == "class_shift" and s.timetable:
        nxt = next((class_out(c) for c in s.timetable if c.get("start") == p.request.get("class_start")
                    and c["day"] == p.extra.get("day")), None)
    delta = new - (old or 0)
    return C.Proposal(proposal_id=p.plan_id, kind=p.kind, message=_message(s, p), plan_revision=p.revision,
                      plan=plan_view, previous_your_share_fils=old if p.kind != "emergency" else None,
                      delta_fils=delta if p.kind != "emergency" else 0,
                      refund_fils=p.extra.get("refund_fils") if p.kind == "class_shift" else None,
                      new_charge_fils=new if p.kind == "class_shift" else None, next_class=nxt,
                      requires_approval=p.status == "pending" and bool(p.affected),
                      consents=_consents(s, p, viewer), alternatives=alts or None)


def _visible(s: Session, p: PendingPlan, viewer: str) -> bool:
    return (p.kind != "quote" and p.revision == s.revision and p.status == "pending" and p.option is not None
            and (viewer in p.affected or viewer == p.requester))


# ============================================================================ state
def _has_next_class(s: Session, t: Trip) -> bool:
    if not s.timetable or not t.service_date:
        return False
    day = DAY_NAMES[date.fromisoformat(t.service_date).weekday()]
    return any(c["day"] == day and c.get("start") and to_min(c["start"]) > t.class_start for c in s.timetable)


def trip_out(s: Session, t: Trip, viewer: str) -> Optional[C.TripView]:
    if t.option is None:
        return None
    waiting = any(p.trip_id == t.trip_id and _visible(s, p, viewer) and viewer in p.consents for p in s.pending.values())
    status = "canceled" if t.status in ("released", "cancelled") else "awaiting_consent" if waiting else "confirmed"
    return C.TripView(trip_id=t.trip_id, status=status, class_start=to_hhmm(t.class_start),
                      plan=option_out(s, t.option, viewer, extra_flags=tuple(t.flags)),
                      amount_paid_fils=t.paid.get(viewer, 0), has_next_class=_has_next_class(s, t))


def state(s: Session) -> C.SimState:
    me = s.primary
    trips = [v for t in s.trips.values() if me in t.members and (v := trip_out(s, t, me)) is not None]
    trips.sort(key=lambda v: v.status == "canceled")
    props = [x for p in s.pending.values() if _visible(s, p, me) and (x := proposal_out(s, p, me)) is not None]
    ledger = [C.LedgerEntry(at=e["at"], kind=e["kind"], amount_fils=e["amount_fils"], note=e["note"] or e["kind"])
              for e in s.ledger if e["token"] == me]
    svc = next((t.service_date for t in s.trips.values() if me in t.members and t.service_date), DEFAULT_DATE)
    return C.SimState(session_id=s.session_id, revision=s.revision, sim_time=to_hhmm(s.sim_min), service_date=svc,
                      trips=trips, pending_proposals=props,
                      wallet=C.WalletState(balance_fils=s.wallets[me], ledger=ledger))


# ============================================================================ confirm / decline / cancel
def _fp(req: C.ConfirmRequest) -> str:
    return f"{req.rider_token}|{req.plan_id}|{req.plan_revision}|{req.accepted_fare_fils}|{req.decision}|{req.replaces_trip_id}"


def confirm(s: Session, req: C.ConfirmRequest) -> C.ConfirmResponse:
    prior = s.wire_idem.get(req.idempotency_key)
    if prior is not None:
        if prior[0] != _fp(req):
            raise ApiError(409, "IDEMPOTENCY_KEY_REUSED", "idempotency key already used for a different request")
        return prior[1].model_copy(update={"idempotent_replay": True})
    if req.decision == "cancel_trip":
        resp = _cancel_trip(s, req)
    elif req.decision == "decline":
        resp = _decline(s, req)
    else:
        resp = _accept(s, req)
    s.wire_idem[req.idempotency_key] = (_fp(req), resp)
    return resp


def _stale(s: Session, rev: int) -> None:
    if rev != s.revision:
        raise ApiError(409, "STALE_REVISION", "the plan changed while you were deciding", s.revision)


def _accept(s: Session, req: C.ConfirmRequest) -> C.ConfirmResponse:
    p = s.pending.get(req.plan_id)
    if p is None:
        raise ApiError(404, "PLAN_NOT_FOUND", "unknown or expired plan")
    if p.kind == "class_shift" and req.replaces_trip_id and req.replaces_trip_id != p.trip_id:
        raise ApiError(409, "TRIP_MISMATCH", "this class-shift proposal replaces a different trip")
    internal = schemas.ConfirmRequest(session_id=req.session_id, rider_token=req.rider_token, plan_id=req.plan_id,
                                      plan_revision=max(req.plan_revision, 1),
                                      accepted_fare_fils=req.accepted_fare_fils,
                                      idempotency_key=req.idempotency_key)
    if req.plan_revision != s.revision:
        _stale(s, req.plan_revision)
    r = replanner.confirm(s, internal)
    if r.status == "consent_recorded":
        return C.ConfirmResponse(session_id=s.session_id, revision=s.revision, status="awaiting_consent",
                                 trip_id=p.trip_id, plan=option_out(s, p.option, req.rider_token, plan_id=p.plan_id),
                                 wallet=C.Wallet(balance_fils=s.wallets[req.rider_token]),
                                 pending_consents=_consents(s, p, req.rider_token))
    trip = s.trips[r.trip_id]
    return C.ConfirmResponse(session_id=s.session_id, revision=s.revision, status="confirmed", trip_id=trip.trip_id,
                             plan=option_out(s, trip.option, req.rider_token),
                             amount_paid_fils=trip.paid.get(req.rider_token, 0),
                             wallet=C.Wallet(balance_fils=s.wallets[req.rider_token]))


def _decline(s: Session, req: C.ConfirmRequest) -> C.ConfirmResponse:
    p = s.pending.get(req.plan_id)
    if p is None:
        raise ApiError(404, "PLAN_NOT_FOUND", "unknown or expired plan")
    _stale(s, req.plan_revision)
    if p.kind == "quote":
        if req.rider_token != p.requester:
            raise ApiError(403, "NOT_PLAN_OWNER", "only the requesting rider can decline this quote")
        del s.pending[req.plan_id]
    else:
        if req.rider_token not in p.affected and req.rider_token != p.requester:
            raise ApiError(403, "NOT_AFFECTED_RIDER", "rider is not part of this proposal")
        if p.status != "pending":
            raise ApiError(409, "PLAN_NOT_PENDING", "proposal is no longer pending")
        p.extra.setdefault("declined", set()).add(req.rider_token)
        p.status = "declined"                       # nothing charged; class shift keeps the old booking
        if p.kind == "smart_rescue" and p.trip_id in s.trips:
            s.trips[p.trip_id].flags = ["RESCUE_DECLINED", "OPERATOR_ASSISTANCE_AVAILABLE"]
    s.bump()
    return C.ConfirmResponse(session_id=s.session_id, revision=s.revision, status="declined",
                             trip_id=p.trip_id, wallet=C.Wallet(balance_fils=s.wallets[req.rider_token]))


def _cancel_trip(s: Session, req: C.ConfirmRequest) -> C.ConfirmResponse:
    _stale(s, req.plan_revision)
    trip = next((t for t in s.trips.values() if t.status == "booked" and req.rider_token in t.members
                 and (not req.plan_id or (t.option is not None and t.option.plan_id == req.plan_id)
                      or req.plan_id == t.trip_id)), None)
    if trip is None:
        raise ApiError(404, "TRIP_NOT_FOUND", "no booked trip to cancel")
    dispatch = min(trip.pickups.values())
    if dispatch - s.sim_min <= int(s.fx.tariffs["FREE_RELEASE_MIN"]):
        raise ApiError(409, "RELEASE_REQUIRES_OPERATOR_POLICY",
                       "less than 30 minutes before pickup; cancellation terms are set by Jeeny (not simulated)")
    refund = trip.paid.pop(req.rider_token, 0)
    if refund:
        s.post(req.rider_token, trip.trip_id, "refund", refund, "Trip canceled — refund")
    trip.members = [t for t in trip.members if t != req.rider_token]
    trip.fares.pop(req.rider_token, None)
    trip.pickups.pop(req.rider_token, None)
    for k, p in list(s.pending.items()):
        if p.trip_id == trip.trip_id and p.status == "pending":
            p.status = "declined"
    s.bump()
    remaining = [t for t in trip.members if t not in s.cancelled]
    if remaining:
        trip.requester = remaining[0]
        replanner.rescue_trip(s, Engine(s), trip, "co_rider_canceled_trip")
    else:
        trip.status = "cancelled"
    return C.ConfirmResponse(session_id=s.session_id, revision=s.revision, status="canceled", trip_id=trip.trip_id,
                             amount_paid_fils=0, wallet=C.Wallet(balance_fils=s.wallets[req.rider_token]))


# ============================================================================ class shift
def shift(s: Session, req: C.ShiftRequest) -> C.ShiftResponse:
    r = replanner.class_shift(s, schemas.ShiftClassRequest(**req.model_dump()))
    base = dict(session_id=s.session_id, revision=s.revision, trip_id=req.trip_id)
    if r.status == "proposed":
        p = s.pending[r.proposal.proposal_id]
        trip = s.trips[req.trip_id]
        p.extra["old_class"] = to_hhmm(trip.class_start)
        p.extra["day"] = DAY_NAMES[date.fromisoformat(trip.service_date).weekday()]
        return C.ShiftResponse(**base, status="shift_proposed", proposal=proposal_out(s, p, req.rider_token),
                               message="Next class found in your saved timetable (no new scan). "
                                       "Nothing changes until you approve.")
    if r.status == "no_next_class":
        co = r.cancel_only_option or {}
        return C.ShiftResponse(**base, status="no_next_class",
                               cancel_only=C.CancelOnly(refund_fils=int(co.get("refund_fils", 0)),
                                                        terms="Free release more than 30 minutes before pickup "
                                                              "(simulation policy). Real terms are set by Jeeny."),
                               message="There is no later class today in your saved timetable.")
    if r.status == "release_requires_operator_policy":
        raise ApiError(409, "RELEASE_REQUIRES_OPERATOR_POLICY",
                       "less than 30 minutes before pickup; Jeeny's cancellation policy applies (not simulated)")
    raise ApiError(409, "NO_FEASIBLE_ROUTE", f"no feasible group for your {r.next_class} class; your booking is unchanged")


# ============================================================================ emergency
def emergency(s: Session, req: C.EmergencyRequest) -> C.EmergencyResponse:
    eng = Engine(s)
    rq = eng.requester(req.rider_token, req.zone_id, req.campus_id, req.gender_pool, req.service_date.isoformat(),
                       to_min(req.class_start), req.arrival_buffer_min, req.accessibility.wheelchair,
                       req.accessibility.big_car, req.fare_cap_fils)
    base = dict(session_id=s.session_id)
    if rq.wheelchair:
        s.advance_clock(req.request_time)
        return C.EmergencyResponse(**base, revision=s.revision, status="no_option",
                                   reason=C.Reason(code="NO_ACCESSIBLE_VEHICLE",
                                                   message="No verified ramp vehicle is on the road near you."),
                                   message="We never offer a car without a ramp. An operator can arrange assistance; "
                                           "nothing is dispatched.")
    pre: list[schemas.Rejection] = []
    allow = True
    if not req.sharing_opt_in:
        allow = False
        pre.append(schemas.Rejection(subject="emergency_pool", code="SOFT_PREFERENCE",
                                     detail="sharing not opted in: no shared insertion"))
    if rq.big_car:
        allow = False
        pre.append(schemas.Rejection(subject="emergency_pool", code="INSUFFICIENT_SEATS",
                                     detail="big car required; en-route trips are standard cars"))
    internal = schemas.EmergencyRequest(session_id=req.session_id, rider_token=req.rider_token,
                                        class_start=req.class_start, request_time=req.request_time,
                                        service_date=req.service_date, arrival_buffer_min=req.arrival_buffer_min,
                                        fare_cap_fils=req.fare_cap_fils)
    r = replanner.emergency(s, internal, allow_insertion=allow, pre_rejected=pre)
    base["revision"] = s.revision
    if r.status == "insertion_proposed":
        p = s.pending[r.proposal_id]
        prop = proposal_out(s, p, req.rider_token)
        prop.plan.vehicle = C.Vehicle(kind="sedan", label=f"En-route trip {r.insertion.trip_id}", wheelchair_accessible=False)
        prop.plan.hard_filters_passed = [
            "Female-only trip" if req.gender_pool == "female_only" else "Male-only trip", "Free seat available",
            "Pickup within 10 min of request", "Everyone still meets their deadline", "Existing riders' fares unchanged",
            "Within your fare cap"]
        return C.EmergencyResponse(**base, status="emergency_proposed", proposal=prop,
                                   newcomer_fare_fils=r.insertion.fare_fils,
                                   existing_riders_fares_unchanged=all(x.delta_fils == 0 for x in r.insertion.existing_riders),
                                   message="Emergency price applies to you only. Riders already on the trip pay the same.")
    fb = r.fallback or {}
    codes = ", ".join(sorted({x.code for x in r.rejected})) or "none"
    if fb.get("handoff_eligible") and not rq.big_car:
        return C.EmergencyResponse(**base, status="solo_handoff_eligible",
                                   reason=C.Reason(code="NO_SHARED_INSERTION", message=f"No shared seat fits ({codes})."),
                                   message=f"A standard solo Jeeny ride (simulated quote {fb.get('simulated_quote_fils')} fils) "
                                           "is within your cap. Hand-off only; nothing is dispatched.")
    quote = fb.get("simulated_quote_fils")
    over = quote is not None and not fb.get("within_fare_cap")
    return C.EmergencyResponse(**base, status="no_option",
                               reason=C.Reason(code="FARE_CAP" if over else "NO_FEASIBLE_ROUTE",
                                               message=(f"No shared seat fits ({codes}). A solo ride would be about "
                                                        f"{quote} fils, above your fare cap." if over else
                                                        f"No shared seat fits ({codes}).")),
                               message="Nothing was booked. You can raise your fare cap yourself or ask an operator.")


# ============================================================================ events (incl. peer consent)
def event(s: Session, req: C.SimEventRequest) -> C.SimState:
    if req.event == "peer_consent":
        _peer_consent(s, req.target)
        return state(s)
    name = "rider_cancel" if req.event in ("cancel", "rider_cancel") else req.event
    if name in ("rider_cancel", "shuttle_full", "vehicle_unavailable") and not req.target:
        raise ApiError(422, "TARGET_REQUIRED", f"{req.event} needs a target")
    sim_time = req.sim_time
    if sim_time is None and name != "reset":
        key = {"rider_cancel": "cancel", "traffic": "traffic", "shuttle_full": "full",
               "vehicle_unavailable": "wav_out"}[name]
        default = s.fx.scenarios.get(key, {}).get("sim_time", to_hhmm(s.sim_min))
        sim_time = to_hhmm(max(to_min(default), s.sim_min))
    internal = schemas.SimulationEventRequest(session_id=req.session_id, event=name, target=req.target or "all",
                                              sim_time=sim_time, multiplier=req.multiplier)
    replanner.apply_event(s, internal)
    if name == "vehicle_unavailable":
        for t in s.trips.values():
            if t.vehicle_id == req.target and t.status == "booked":
                if any(p.trip_id == t.trip_id and p.option is None and p.revision == s.revision for p in s.pending.values()):
                    t.flags = ["VEHICLE_UNAVAILABLE", "OPERATOR_ASSISTANCE_REQUIRED"]
    return state(s)


def _peer_consent(s: Session, target: Optional[str]) -> None:
    """Simulated explicit consent of SYNTHETIC co-riders only. Never consents for the proposal's requester
    or the session's own rider: their decision always comes from /api/trips/confirm."""
    for p in list(s.pending.values()):
        if p.kind == "quote" or p.status != "pending" or p.revision != s.revision or p.option is None:
            continue
        if target and target != "all" and target != p.plan_id:
            continue
        peers = [t for t in p.affected if t not in (p.requester, s.primary)]
        if not peers:
            continue
        p.consents.update(peers)
        if all(t in p.consents for t in p.affected):
            replanner._commit_proposal(s, p)
