"""ONE replanning engine, four triggers (Rev. E §11.4): best_deal · emergency · class_shift · smart_rescue.

All four share the same Engine, the same hard filters (gender pool, accessibility, capacity,
deadline, required Big Car) and the same approval rule. Hard filters are evaluated BEFORE any
ranking; relaxation only ever touches the soft preferences companions / departure / pickup_mode.
A higher fare cap is never "relaxed": above-cap routes are returned as unbookable comparisons.
Quotes and proposals have no financial side effects; money moves only in commit_* functions.
"""
from __future__ import annotations

import math
import time
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations
from typing import Any, Optional

from . import pricing
from .errors import ApiError
from .matching import (Requester, VehicleChoice, adjacent, candidate_pool, home_cell, point_cell,
                       rider_deadline, soft_arrival_ok, vehicle_for_group)
from .routing import (RouteError, ShuttlePlan, build_door_route, corridor_order, leg, plan_main_road_shuttle,
                      replay, schedule_backward)
from .schemas import (Audit as AuditModel, ConfirmRequest, ConfirmResponse, EmergencyInsertion, EmergencyRequest,
                      EmergencyResponse, EventResponse, FareComponent, FareInfo, FareShare, PickupStop, PlanOption,
                      PlanRequest, PlanResponse, Proposal, Rejection, RiderDelta, ShiftClassRequest,
                      ShiftClassResponse, ShuttleLeg, SimulationEventRequest)
from .state import PendingPlan, Session, Trip
from .timeutil import to_hhmm, to_min
from .traffic_adapter import TrafficOverride

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 3)


# ============================================================================ audit & candidates
@dataclass
class Audit:
    candidates: int = 0
    groups: int = 0
    routes: int = 0
    rej: Counter = field(default_factory=Counter)

    def model(self) -> AuditModel:
        return AuditModel(candidate_riders_considered=self.candidates, groups_evaluated=self.groups,
                          routes_evaluated=self.routes, rejections_by_code=dict(sorted(self.rej.items())))


@dataclass
class Candidate:
    mode: str
    members: list[dict[str, Any]]          # private rider records, pickup order
    pickups: list[int]
    arrival: int
    leave_home: dict[str, int]
    leg_km: list[Fraction]
    shares: dict[str, int]                 # agreed fare per rider (shuttle: incl. ticket at boarding)
    pay_now: dict[str, int]                # debited on confirmation (shuttle ticket excluded)
    vehicle_total: int
    vehicle: VehicleChoice
    fixed_each: dict[str, int]
    deadlines: dict[str, int]
    soft_ok: bool
    cap_violations: list[str]
    shuttle: Optional[ShuttlePlan] = None
    ticket: int = 0
    wait_min: int = 0
    transfers: int = 0

    @property
    def tokens(self) -> list[str]:
        return [m["token"] for m in self.members]


class Engine:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.fx = session.fx
        self.traffic = session.traffic
        self.audit = Audit()
        self.reasons: dict[str, tuple[str, str]] = {}
        t = self.fx.tariffs
        self.BASE, self.FEE = int(t["BASE"]), int(t["FEE"])

    # ------------------------------------------------------------------ requester
    def requester(self, token: str, zone_id: str, campus_id: str, gender_pool: str, service_date: str,
                  class_start: int, buffer_min: int, wheelchair: bool, big_car: bool, fare_cap: int) -> Requester:
        rider = self.fx.rider(token)
        if rider is None:
            raise ApiError(404, "RIDER_NOT_FOUND", "unknown rider token")
        if token in self.s.cancelled:
            raise ApiError(409, "RIDER_CANCELLED", "rider has cancelled in this simulation")
        if rider["zone_id"] != zone_id or rider["campus_id"] != campus_id:
            raise ApiError(422, "ZONE_MISMATCH", "zone/campus do not match the rider's registered commute")
        if rider["gender_pool"] != gender_pool:
            raise ApiError(422, "GENDER_POOL_NOT_ELIGIBLE", "rider is not eligible for the requested pool")
        if campus_id not in self.fx.campuses:
            raise ApiError(422, "UNKNOWN_CAMPUS", "unknown campus")
        # accessibility needs can be added by the request but never removed below the profile
        priv = dict(rider, wheelchair=bool(rider.get("wheelchair")) or wheelchair,
                    big_car=bool(rider.get("big_car")) or big_car)
        return Requester(token, priv, zone_id, campus_id, gender_pool, service_date, class_start,
                         class_start - buffer_min, priv["wheelchair"], priv["big_car"], fare_cap)

    def campus_point(self, rq: Requester) -> str:
        return self.fx.campuses[rq.campus_id]["gate_point"]

    def _reason(self, subject: str, code: str, detail: str) -> None:
        self.reasons.setdefault(subject, (code, detail))

    # ------------------------------------------------------------------ builders (hard filters inside)
    def door_candidate(self, rq: Requester, companions: list[dict[str, Any]], start: Optional[int],
                       target: Optional[int], fixed_prefix: tuple[dict[str, Any], ...] = (),
                       fixed_pickups: Optional[tuple[int, ...]] = None, cap_of: Optional[dict[str, int]] = None
                       ) -> tuple[Optional[Candidate], str]:
        campus = self.campus_point(rq)
        self.audit.routes += 1
        try:
            ordered = corridor_order(self.fx, campus, rq.rider, companions, fixed_prefix)
            route = build_door_route(self.fx, campus, ordered)
            if start is not None:
                route = replay(self.fx, self.traffic, route, campus, start, fixed_pickups)
            else:
                found = schedule_backward(self.fx, self.traffic, route, campus, target, self.s.sim_min)
                if found is None:
                    return None, "LATE_ARRIVAL"
                route = found
        except RouteError as e:
            return None, e.code
        n_fixed = len(fixed_pickups or ())
        if any(p < self.s.sim_min for p in route.pickups[n_fixed:]):
            return None, "PAST_PICKUP"
        deadlines = {}
        for r in ordered:
            dl = rq.deadline if r["token"] == rq.token else rider_deadline(r, rq.service_date)
            deadlines[r["token"]] = dl if dl is not None else rq.deadline
        if any(route.arrival > d for d in deadlines.values()):
            return None, "LATE_ARRIVAL"
        vehicle, vrej = vehicle_for_group(self.fx, ordered, rq.zone_id, rq.campus_id, rq.big_car, self.s.vehicles_out)
        for subj, code, detail in vrej:
            self._reason(subj, code, detail)
        if vehicle is None:
            return None, (vrej[0][1] if vrej else "VEHICLE_UNAVAILABLE")
        split = pricing.leg_weighted_split(list(route.leg_km), vehicle.rate, self.BASE, self.FEE)
        shares = dict(zip(route.order, split.shares))
        caps = cap_of or {}
        cap_viol = [t for t in route.order
                    if shares[t] > (rq.fare_cap if t == rq.token else caps.get(t, int(self.fx.riders[t]["fare_cap_fils"])))]
        soft = all(soft_arrival_ok(r, route.arrival, self.s.sim_min) for r in ordered if r["token"] != rq.token)
        return Candidate("door_to_door", ordered, list(route.pickups), route.arrival,
                         dict(zip(route.order, route.pickups)), list(route.leg_km), shares, dict(shares),
                         split.vehicle_total, vehicle, dict(zip(route.order, split.fixed_each)), deadlines, soft,
                         cap_viol), ""

    def shuttle_candidate(self, rq: Requester, companions: list[dict[str, Any]]) -> tuple[Optional[Candidate], str]:
        members = [rq.rider] + sorted(companions, key=lambda r: r["token"])
        self.audit.routes += 1
        deadlines = {m["token"]: (rq.deadline if m["token"] == rq.token else rider_deadline(m, rq.service_date) or rq.deadline)
                     for m in members}
        chair = any(m.get("wheelchair") for m in members)
        sp, srej = plan_main_road_shuttle(self.fx, self.traffic, rq.zone_id, rq.campus_id, len(members), chair,
                                          min(deadlines.values()), self.s.sim_min, self.s.shuttle_seats)
        for subj, code, detail in srej:
            self._reason(subj, code, detail)
        if sp is None:
            return None, (srej[0][1] if srej else "LATE_ARRIVAL")
        vehicle, vrej = vehicle_for_group(self.fx, members, rq.zone_id, rq.campus_id, rq.big_car, self.s.vehicles_out)
        if vehicle is None:
            for subj, code, detail in vrej:
                self._reason(subj, code, detail)
            return None, (vrej[0][1] if vrej else "VEHICLE_UNAVAILABLE")
        split = pricing.shared_segment_split(sp.feeder_km, vehicle.rate, len(members), True, self.BASE, self.FEE)
        ticket = int(self.fx.tariffs["SHUTTLE"])
        feeder = dict(zip([m["token"] for m in members], split.shares))
        shares = {t: v + ticket for t, v in feeder.items()}
        cap_viol = [t for t in shares if shares[t] > (rq.fare_cap if t == rq.token else int(self.fx.riders[t]["fare_cap_fils"]))]
        soft = all(soft_arrival_ok(m, sp.arrival, self.s.sim_min) for m in members if m["token"] != rq.token)
        return Candidate("main_road_shuttle", members, [sp.feeder_depart] * len(members), sp.arrival,
                         {m["token"]: sp.leave_home for m in members}, [sp.feeder_km], shares, feeder, split.vehicle_total,
                         vehicle, dict(zip(feeder, split.fixed_each)), deadlines, soft, cap_viol, sp, ticket,
                         sp.buffer_min, 1), ""

    def best_group(self, rq: Requester, pool: list[dict[str, Any]], size: int, mode: str, start: Optional[int],
                   target: Optional[int], require_soft: bool = True, cap_of: Optional[dict[str, int]] = None,
                   fixed_prefix: tuple[dict[str, Any], ...] = (), fixed_pickups: Optional[tuple[int, ...]] = None
                   ) -> Optional[Candidate]:
        if size > len(pool):
            return None
        best: Optional[Candidate] = None
        best_key: Any = None
        for combo in combinations(pool, size):
            self.audit.groups += 1
            if mode == "door_to_door":
                cand, code = self.door_candidate(rq, list(combo), start, target, fixed_prefix, fixed_pickups, cap_of)
            else:
                cand, code = self.shuttle_candidate(rq, list(combo))
            if cand is None:
                self.audit.rej[code] += 1
                continue
            if require_soft and not cand.soft_ok:
                self.audit.rej["SOFT_PREFERENCE"] += 1
                continue
            others_over = [t for t in cand.cap_violations if t != rq.token]
            if others_over:                     # a co-rider would exceed their own cap: not offered
                self.audit.rej["FARE_CAP"] += 1
                continue
            key = (rq.token in cand.cap_violations, cand.shares[rq.token], cand.arrival, tuple(cand.tokens))
            if best_key is None or key < best_key:
                best, best_key = cand, key
        return best

    # ------------------------------------------------------------------ scoring & views
    def gen_cost(self, cand: Candidate, viewer: str) -> Fraction:
        t = self.fx.frac
        travel = cand.arrival - cand.leave_home[viewer]
        return (Fraction(cand.shares[viewer], 1000) + t["J_W_T"] * travel + t["J_W_W"] * cand.wait_min
                + t["J_W_N"] * cand.transfers)

    def utility(self, d_fare: int, d_min: int) -> Fraction:
        t = self.fx.frac
        return 100 - t["UTILITY_W_FARE"] * d_fare - t["UTILITY_W_MIN"] * abs(d_min)

    def option(self, cand: Candidate, plan_id: str, viewer: str, cap: int, deadline: int,
               relaxed: Optional[str] = None, constraint: Optional[str] = None, utility: Optional[Fraction] = None,
               reference: Optional[int] = None, delta_min: int = 0, force_unbookable: bool = False) -> PlanOption:
        toks = cand.tokens
        share = cand.shares[viewer]
        n = len(toks)
        pos = toks.index(viewer)
        if cand.mode == "door_to_door":
            fixed = cand.fixed_each[viewer]
            breakdown = [FareComponent(label="fixed (base + platform fee) / riders", fils=fixed),
                         FareComponent(label="distance while onboard (leg-weighted)", fils=share - fixed)]
            equal = pricing.equal_split(cand.vehicle_total, n)[pos]
        else:
            feeder = cand.pay_now[viewer]
            fixed = cand.fixed_each.get(viewer, 0)
            breakdown = [FareComponent(label="feeder fixed (base + platform fee) / riders", fils=fixed),
                         FareComponent(label="feeder distance / riders", fils=feeder - fixed)]
            if cand.ticket:
                breakdown.append(FareComponent(label="shuttle ticket (charged at boarding)", fils=cand.ticket))
            equal = None
        over = share > cap or any(t != viewer for t in cand.cap_violations)
        bookable = not over and not force_unbookable
        shuttle = None
        if cand.shuttle is not None:
            sp = cand.shuttle
            shuttle = ShuttleLeg(walk_to_meet_min=sp.walk_min, feeder_depart=to_hhmm(sp.feeder_depart),
                                 hub_arrival=to_hhmm(sp.hub_arrival), shuttle_id=sp.shuttle_id,
                                 shuttle_depart=to_hhmm(sp.shuttle_depart), transfer_buffer_min=sp.buffer_min)
        return PlanOption(
            plan_id=plan_id, mode=cand.mode, relaxed=relaxed, relaxed_constraint=constraint,
            utility=None if utility is None else round(float(utility), 2),
            generalized_cost_j=round(float(self.gen_cost(cand, viewer)), 2),
            leave_home=to_hhmm(cand.leave_home[viewer]), arrival=to_hhmm(cand.arrival), deadline=to_hhmm(deadline),
            delta_minutes=delta_min, pickup_order=toks,
            pickups=[PickupStop(position=i + 1, token=t, pickup_time=to_hhmm(p))
                     for i, (t, p) in enumerate(zip(toks, cand.pickups))],
            vehicle_class=cand.vehicle.vehicle_class, vehicle_id=cand.vehicle.vehicle_id,
            fare=FareInfo(your_share_fils=share, vehicle_total_fils=cand.vehicle_total,
                          shares=[FareShare(position=i + 1, token=t, share_fils=cand.shares[t]) for i, t in enumerate(toks)],
                          your_breakdown=breakdown, equal_split_fils=equal, hypothetical_reference_fils=reference,
                          delta_vs_reference_fils=None if reference is None else share - reference,
                          shuttle_ticket_fils_at_boarding=cand.ticket),
            bookable=bookable, cap_status="within_cap" if not over else "CAP_EXCEEDED_REQUIRES_APPROVAL",
            shuttle=shuttle)

    def rejections(self, pool_rej: Counter) -> list[Rejection]:
        out = [Rejection(subject=s, code=c, detail=d) for s, (c, d) in sorted(self.reasons.items())]
        for code, n in sorted(pool_rej.items()):
            out.append(Rejection(subject="candidate_riders", code=code,
                                 detail="aggregated; individual riders are not disclosed", count=n))
        return out


# ============================================================================ planning (+ Best Deal)
@dataclass
class PlanResult:
    status: str
    options: list[tuple[PlanOption, Candidate]]
    comparisons: list[PlanOption]
    rejected: list[Rejection]
    reference_label: Optional[str]
    engine: Engine


def run_planner(s: Session, rq: Requester, desired: int, mode: str, preferred: Optional[int],
                exclude: set[str], allow_best_deal: bool = True, id_prefix: str = "") -> PlanResult:
    eng = Engine(s)
    fx = s.fx
    window = int(fx.tariffs["CLASS_WINDOW_MIN"])
    relax = int(fx.tariffs["DEPARTURE_RELAX_MIN"])
    target = rq.deadline - int(fx.tariffs["TARGET_SLACK_MIN"])
    pool, pool_rej = candidate_pool(fx, rq, s.sim_min, exclude - {rq.token}, window)
    eng.audit.candidates = len(pool)
    eng.audit.rej.update(pool_rej)

    def search(size: int, m: str, shift: int = 0, soft: bool = True) -> Optional[Candidate]:
        if m == "door_to_door":
            if preferred is not None:
                return eng.best_group(rq, pool, size, m, preferred + shift, None, soft)
            return eng.best_group(rq, pool, size, m, None, target + shift, soft)
        if shift:
            return None
        return eng.best_group(rq, pool, size, m, None, None, soft)

    other_mode = "main_road_shuttle" if mode == "door_to_door" else "door_to_door"
    exact = search(desired, mode)
    explain_other = search(desired, other_mode)  # evaluated for "Why this route?" and Best Deal reuse
    comparisons: list[PlanOption] = []
    if exact is not None and rq.token not in exact.cap_violations:
        opt = eng.option(exact, f"{id_prefix}M1", rq.token, rq.fare_cap, rq.deadline)
        return PlanResult("exact_match", [(opt, exact)], [], eng.rejections(pool_rej), None, eng)
    if exact is not None:
        comparisons.append(eng.option(exact, f"{id_prefix}CMP-EXACT", rq.token, rq.fare_cap, rq.deadline,
                                      relaxed="exact request (above fare cap)"))
    scored: list[tuple[Fraction, int, int, PlanOption, Candidate]] = []
    ref_label = None
    if allow_best_deal:
        ref = search(desired, mode, soft=False)
        reference = ref.shares[rq.token] if ref is not None else None
        ref_label = ("hypothetical same-route reference with all requested companions; not an available quote"
                     if reference is not None else "reference unavailable; ranked by generalized cost J")
        base_leave = preferred if preferred is not None else (ref.leave_home[rq.token] if ref else None)
        relaxations: list[tuple[str, str, Optional[Candidate], int]] = []
        if desired > 0:
            relaxations.append(("companions", f"companions {desired}→{desired - 1}", search(desired - 1, mode), 0))
        for shift in (-relax, relax):
            sign = "−" if shift < 0 else "+"
            relaxations.append(("departure", f"departure {sign}{relax} min", search(desired, mode, shift), shift))
        relaxations.append(("pickup_mode", f"pickup mode → {other_mode}", explain_other, 0))
        for constraint, label, cand, _shift in relaxations:
            if cand is None:
                continue
            leave = cand.leave_home[rq.token]
            d_min = 0 if base_leave is None else leave - base_leave
            u = eng.utility(cand.shares[rq.token] - reference, d_min) if reference is not None else None
            opt = eng.option(cand, "PENDING", rq.token, rq.fare_cap, rq.deadline, relaxed=label, constraint=constraint,
                             utility=u, reference=reference, delta_min=d_min)
            if not opt.bookable:
                comparisons.append(opt.model_copy(update={"plan_id": f"{id_prefix}CMP{len(comparisons) + 1}"}))
                continue
            rank = -u if u is not None else eng.gen_cost(cand, rq.token)
            scored.append((rank, cand.shares[rq.token], cand.arrival, opt, cand))
    scored.sort(key=lambda x: (x[0], x[1], x[2], x[3].relaxed or ""))
    options = [(o.model_copy(update={"plan_id": f"{id_prefix}BD{i + 1}"}), c) for i, (_, _, _, o, c) in enumerate(scored[:2])]
    if desired > 0 and allow_best_deal:
        solo = eng.best_group(rq, pool, 0, "door_to_door", None, target, True)
        if solo is not None:
            comparisons.append(eng.option(solo, f"{id_prefix}CMP-SOLO", rq.token, rq.fare_cap, rq.deadline,
                                          relaxed="solo (changes companions to 0; not offered automatically)",
                                          force_unbookable=True))
    if options:
        status = "best_deal_proposed"
    else:
        status = "no_accessible_route" if rq.wheelchair else "no_feasible_route"
    return PlanResult(status, options, comparisons, eng.rejections(pool_rej), ref_label, eng)


def plan(s: Session, req: PlanRequest) -> PlanResponse:
    t0 = time.perf_counter()
    if req.booking == "emergency":
        raise ApiError(422, "USE_EMERGENCY_ENDPOINT", "emergency bookings use /api/trips/emergency")
    eng0 = Engine(s)
    rq = eng0.requester(req.rider_token, req.zone_id, req.campus_id, req.gender_pool, req.service_date.isoformat(),
                        to_min(req.class_start), req.arrival_buffer_min, req.accessibility.wheelchair,
                        req.accessibility.big_car, req.fare_cap_fils)
    s.primary = req.rider_token
    desired = req.desired_companions if req.sharing_opt_in else 0
    preferred = to_min(req.preferred_pickup) if req.preferred_pickup else None
    res = run_planner(s, rq, desired, req.pickup_mode, preferred, s.busy_riders())
    for key in [k for k, p in s.pending.items() if p.kind == "quote" and p.requester == rq.token]:
        del s.pending[key]
    for opt, cand in res.options:
        s.pending[opt.plan_id] = PendingPlan(opt.plan_id, "quote", s.revision, opt, cand, rq.token,
                                             request=req.model_dump(mode="json"))
    return PlanResponse(
        session_id=s.session_id, plan_revision=s.revision, status=res.status,
        exact_match_found=res.status == "exact_match", options=[o for o, _ in res.options],
        unbookable_comparisons=res.comparisons, rejected=res.rejected,
        requires_approval=res.status == "best_deal_proposed", operator_assistance=not res.options,
        reference_label=res.reference_label, compute_ms=_ms(t0), audit=res.engine.audit.model())


# ============================================================================ confirmation & commits
def _fingerprint(req: ConfirmRequest) -> str:
    return f"{req.rider_token}|{req.plan_id}|{req.plan_revision}|{req.accepted_fare_fils}"


def _debit_all(s: Session, trip_id: str, charges: dict[str, int], note: str = "", refund_note: str = "") -> None:
    """Atomic: verify every rider can pay before posting anything. Refunds never fail."""
    for tok, amt in charges.items():
        if amt > 0 and s.wallets[tok] < amt:
            raise ApiError(402, "INSUFFICIENT_FUNDS", "insufficient simulated wallet balance; nothing was charged")
    for tok, amt in charges.items():
        key = (trip_id, s.revision, tok)
        if amt == 0:
            continue
        if key in s.charged:
            raise ApiError(409, "DUPLICATE_CHARGE", "this trip revision was already charged")
        s.charged.add(key)
        s.post(tok, trip_id, "debit" if amt > 0 else "refund", abs(amt), note if amt > 0 else (refund_note or note))


def confirm(s: Session, req: ConfirmRequest) -> ConfirmResponse:
    prior = s.idempotency.get(req.idempotency_key)
    if prior is not None:
        if prior[0] != _fingerprint(req):
            raise ApiError(409, "IDEMPOTENCY_KEY_REUSED", "idempotency key already used for a different request")
        return prior[1].model_copy(update={"idempotent_replay": True})
    p = s.pending.get(req.plan_id)
    if p is None:
        raise ApiError(404, "PLAN_NOT_FOUND", "unknown or expired plan")
    if p.revision != s.revision or req.plan_revision != s.revision:
        raise ApiError(409, "STALE_REVISION", "plan revision is stale; request a new plan", s.revision)
    if p.status != "pending":
        raise ApiError(409, "PLAN_NOT_PENDING", "plan is no longer pending")
    follow_ups: list[str] = []
    if p.kind == "quote":
        resp = _confirm_quote(s, p, req)
    else:
        if req.rider_token not in p.affected:
            raise ApiError(403, "NOT_AFFECTED_RIDER", "rider is not part of this proposal")
        if req.accepted_fare_fils != p.new_fares[req.rider_token]:
            raise ApiError(409, "FARE_MISMATCH", "accepted fare does not match the proposal")
        p.consents.add(req.rider_token)
        waiting = [t for t in p.affected if t not in p.consents]
        charged = 0
        if not waiting:
            before = s.wallets[req.rider_token]
            follow_ups = _commit_proposal(s, p)
            charged = before - s.wallets[req.rider_token]
        trip_id = p.extra.get("new_trip_id") or p.trip_id
        resp = ConfirmResponse(session_id=s.session_id, status="committed" if not waiting else "consent_recorded",
                               trip_id=trip_id, plan_id=p.plan_id, plan_revision=s.revision, charged_fils=charged,
                               wallet_balance_fils=s.wallets[req.rider_token], awaiting_consent_from=waiting,
                               follow_up_proposals=follow_ups)
    s.idempotency[req.idempotency_key] = (_fingerprint(req), resp)
    return resp


def _confirm_quote(s: Session, p: PendingPlan, req: ConfirmRequest) -> ConfirmResponse:
    if req.rider_token != p.requester:
        raise ApiError(403, "NOT_PLAN_OWNER", "only the requesting rider can confirm this quote")
    if not p.option.bookable:
        raise ApiError(409, "CAP_EXCEEDED_REQUIRES_APPROVAL", "plan exceeds the fare cap")
    cand: Candidate = p.candidate
    if req.accepted_fare_fils != cand.shares[p.requester]:
        raise ApiError(409, "FARE_MISMATCH", "accepted fare does not match the quote")
    busy = s.busy_riders()
    if any(t in busy for t in cand.tokens):
        raise ApiError(409, "STALE_REVISION", "a rider in this plan is no longer available", s.revision)
    trip_id = s.new_trip_id()
    _debit_all(s, trip_id, dict(cand.pay_now), note=f"Booking {p.plan_id}")
    prefs = dict(p.request or {})
    prefs["desired_companions"] = len(cand.tokens) - 1
    s.trips[trip_id] = _trip_from_candidate(s, trip_id, cand, p.requester, prefs)
    s.trips[trip_id].option = p.option
    rev = s.bump()
    s.trips[trip_id].plan_revision = rev
    s.pending = {k: v for k, v in s.pending.items() if v.kind != "quote"}
    return ConfirmResponse(session_id=s.session_id, status="booked", trip_id=trip_id, plan_id=p.plan_id,
                           plan_revision=rev, charged_fils=cand.pay_now[p.requester],
                           wallet_balance_fils=s.wallets[p.requester], awaiting_consent_from=[])


def _trip_from_candidate(s: Session, trip_id: str, cand: Candidate, requester: str, prefs: dict[str, Any]) -> Trip:
    shuttle = None
    if cand.shuttle is not None:
        sp = cand.shuttle
        shuttle = {"shuttle_id": sp.shuttle_id, "feeder_depart": sp.feeder_depart, "hub_arrival": sp.hub_arrival,
                   "shuttle_depart": sp.shuttle_depart, "feeder_km": sp.feeder_km, "ticket": cand.ticket,
                   "feeder_share": dict(cand.pay_now), "extended": False, "leave_home": sp.leave_home}
    return Trip(trip_id, prefs.get("service_date", ""), prefs.get("campus_id", ""), prefs.get("zone_id", ""),
                cand.mode, prefs.get("gender_pool", ""), to_min(prefs["class_start"]), requester, cand.tokens,
                dict(zip(cand.tokens, cand.pickups)), cand.arrival, dict(cand.shares), dict(cand.pay_now),
                cand.vehicle.vehicle_id, cand.vehicle.vehicle_class, cand.vehicle.rate, list(cand.leg_km),
                dict(cand.deadlines), prefs, s.revision, "booked", shuttle)


def _commit_proposal(s: Session, p: PendingPlan) -> list[str]:
    cand: Candidate = p.candidate
    if p.kind == "smart_rescue":
        trip = s.trips[p.trip_id]
        charges = {t: cand.pay_now[t] - trip.paid.get(t, 0) for t in cand.tokens}
        _debit_all(s, trip.trip_id, charges, note="Rescue revision — extra share",
                   refund_note="Rescue revision — lower share")
        trip.option = p.option
        trip.flags = []
        trip.members, trip.pickups, trip.arrival = cand.tokens, dict(zip(cand.tokens, cand.pickups)), cand.arrival
        trip.fares = dict(cand.shares)
        trip.paid = {t: trip.paid.get(t, 0) + charges[t] for t in cand.tokens}
        trip.vehicle_id, trip.vehicle_class, trip.rate = cand.vehicle.vehicle_id, cand.vehicle.vehicle_class, cand.vehicle.rate
        trip.leg_km, trip.deadlines = list(cand.leg_km), dict(cand.deadlines)
        if p.extra.get("shuttle_extension") and trip.shuttle is not None:
            trip.shuttle["extended"] = True
            trip.shuttle["ticket"] = 0
        p.status = "committed"
        trip.plan_revision = s.bump()
        return []
    if p.kind == "class_shift":
        old = s.trips[p.trip_id]
        rider = p.requester
        refund = old.paid.get(rider, 0)
        new_id = s.new_trip_id()
        charges = dict(cand.pay_now)
        for tok, amt in charges.items():
            if amt > 0 and s.wallets[tok] + (refund if tok == rider else 0) < amt:
                raise ApiError(402, "INSUFFICIENT_FUNDS", "insufficient simulated wallet balance; nothing was changed")
        if refund:
            s.post(rider, old.trip_id, "refund", refund,       # free release (fixture policy: > 30 min before dispatch)
                   f"Old {to_hhmm(old.class_start)} booking released")
        _debit_all(s, new_id, charges, note=f"New {p.request.get('class_start', '')} booking")
        old.members = [t for t in old.members if t != rider]
        old.paid.pop(rider, None)
        old.fares.pop(rider, None)
        old.pickups.pop(rider, None)
        prefs = dict(p.request)
        s.trips[new_id] = _trip_from_candidate(s, new_id, cand, rider, prefs)
        s.trips[new_id].option = p.option
        p.status = "committed"
        p.extra["new_trip_id"] = new_id
        rev = s.bump()
        s.trips[new_id].plan_revision = rev
        if not [t for t in old.members if t not in s.cancelled]:
            old.status = "released"
            return []
        old.requester = old.members[0]
        old.status = "booked"
        follow = rescue_trip(s, Engine(s), old, "co_rider_class_shift")
        return [follow.plan_id] if follow is not None else []
    if p.kind == "emergency":
        at = s.active_trips[p.trip_id]
        rider = p.requester
        _debit_all(s, p.trip_id, {rider: cand.shares[rider]}, note=f"Emergency seat on {p.trip_id}")
        at["riders"].append({"token": rider, "fare_fils": cand.shares[rider]})
        p.status = "committed"
        rev = s.bump()
        members = [r["token"] for r in at["riders"]]
        s.trips[p.trip_id] = Trip(p.trip_id, at["service_date"], at["campus_id"], fx_zone(s, rider), "door_to_door",
                                  at["gender_pool"], p.extra["class_start"], members[0], members,
                                  {rider: cand.pickups[0]}, cand.arrival,
                                  {r["token"]: r["fare_fils"] for r in at["riders"]}, {rider: cand.shares[rider]},
                                  at["vehicle_id"], "sedan", int(s.fx.tariffs["KM_STD"]), list(cand.leg_km),
                                  dict(cand.deadlines), {}, rev, "en_route", option=p.option)
        return []
    raise ApiError(500, "UNKNOWN_PROPOSAL", "unknown proposal kind")


def fx_zone(s: Session, token: str) -> str:
    return s.fx.riders[token]["zone_id"]


# ============================================================================ smart rescue
def _trip_requester(s: Session, eng: Engine, trip: Trip, viewer: str) -> Requester:
    r = s.fx.riders[viewer]
    prefs = trip.prefs or {}
    is_req = viewer == trip.requester and prefs.get("rider_token") == viewer
    cap = int(prefs.get("fare_cap_fils", r["fare_cap_fils"])) if is_req else int(r["fare_cap_fils"])
    acc = prefs.get("accessibility", {}) if is_req else {}
    priv = dict(r, wheelchair=bool(r.get("wheelchair")) or bool(acc.get("wheelchair")),
                big_car=bool(r.get("big_car")) or bool(acc.get("big_car")))
    return Requester(viewer, priv, trip.zone_id, trip.campus_id, trip.gender_pool, trip.service_date,
                     trip.class_start, trip.deadlines.get(viewer, trip.class_start - 10), priv["wheelchair"],
                     priv["big_car"], cap)


def _register(s: Session, p: PendingPlan) -> PendingPlan:
    base, n = p.plan_id, 2
    while p.plan_id in s.pending and s.pending[p.plan_id].revision == s.revision:
        p.plan_id = f"{base}-{n}"
        n += 1
    p.extra.setdefault("at", s.sim_min)
    s.pending[p.plan_id] = p
    return p


def rescue_trip(s: Session, eng: Engine, trip: Trip, trigger: str) -> Optional[PendingPlan]:
    """Replan an already-booked trip from the CURRENT sim time and position. Returns None when the
    trip is still feasible and unchanged (no proposal needed)."""
    live = [t for t in trip.members if t not in s.cancelled]
    if not live:
        trip.status = "cancelled"
        return None
    viewer = trip.requester if trip.requester in live else live[0]
    rq = _trip_requester(s, eng, trip, viewer)
    if trip.mode == "main_road_shuttle" and trip.shuttle is not None and not trip.shuttle.get("extended"):
        return _rescue_shuttle(s, eng, trip, rq, live, trigger)
    fx = s.fx
    caps = {t: int(fx.riders[t]["fare_cap_fils"]) for t in live}
    caps[viewer] = rq.fare_cap
    first_pickup = min(trip.pickups.values()) if trip.pickups else s.sim_min
    in_transit = s.sim_min >= first_pickup
    onboard = tuple(fx.riders[t] for t in trip.members if t in live and trip.pickups.get(t, 10**6) <= s.sim_min) \
        if in_transit else ()
    fixed_pickups = tuple(trip.pickups[r["token"]] for r in onboard) if onboard else None
    if onboard and onboard[0]["token"] != viewer:
        viewer = onboard[0]["token"]
        rq = _trip_requester(s, eng, trip, viewer)
    others = [fx.riders[t] for t in live if t != viewer and not any(o["token"] == t for o in onboard)]
    start = trip.pickups.get(live[0], first_pickup) if not in_transit else first_pickup
    target = rq.deadline - int(fx.tariffs["TARGET_SLACK_MIN"])
    prefix = onboard if onboard else ()
    cands: list[tuple[str, str, Candidate]] = []

    def add(label: str, desc: str, c: Optional[Candidate], code: str = "") -> None:
        if c is None:
            if code:
                eng.audit.rej[code] += 1
            return
        cands.append((label, desc, c))

    eng.audit.groups += 1
    keep, code = eng.door_candidate(rq, others, start, None, prefix, fixed_pickups, caps)
    add("R1", "continue with current riders", keep, code)
    unchanged = (keep is not None and not keep.cap_violations and keep.tokens == trip.members
                 and keep.shares == trip.fares and keep.arrival == trip.arrival)
    if unchanged and keep.vehicle.vehicle_id == trip.vehicle_id:
        return None
    missing = len(trip.members) - len(live)
    if missing > 0:
        window = int(fx.tariffs["CLASS_WINDOW_MIN"])
        exclude = s.busy_riders(except_trip=trip.trip_id) | set(trip.members)
        pool, pool_rej = candidate_pool(fx, rq, s.sim_min, exclude - {viewer}, window)
        eng.audit.candidates += len(pool)
        eng.audit.rej.update(pool_rej)
        for size in range(missing, 0, -1):
            best = None
            for combo in combinations(pool, size):
                eng.audit.groups += 1
                c, code = eng.door_candidate(rq, others + list(combo), start, None, prefix, fixed_pickups, caps)
                if c is None:
                    eng.audit.rej[code] += 1
                    continue
                if not all(soft_arrival_ok(r, c.arrival, s.sim_min) for r in combo):
                    eng.audit.rej["SOFT_PREFERENCE"] += 1
                    continue
                if c.cap_violations:
                    eng.audit.rej["FARE_CAP"] += 1
                    continue
                if best is None or eng.gen_cost(c, viewer) < eng.gen_cost(best, viewer):
                    best = c
            if best is not None:
                add("R2", f"re-match {size} compatible rider(s)", best)
                break
    if keep is None and not in_transit:
        eng.audit.groups += 1
        c, code = eng.door_candidate(rq, others, None, target, (), None, caps)
        add("R3", "re-timed departure", c, code)
    eng.audit.groups += 1
    solo, code = eng.door_candidate(rq, [], None, target, (), None, caps) if not in_transit else (None, "")
    feasible = [(l, d, c) for l, d, c in cands if not c.cap_violations]
    infeasible = [(l, d, c) for l, d, c in cands if c.cap_violations]
    feasible.sort(key=lambda x: (eng.gen_cost(x[2], viewer), x[0]))
    comparisons = [eng.option(c, l, viewer, rq.fare_cap, rq.deadline, relaxed=d) for l, d, c in infeasible]
    if solo is not None:
        comparisons.append(eng.option(solo, "SOLO", viewer, rq.fare_cap, rq.deadline, relaxed="solo trip",
                                      force_unbookable=True))
    if not feasible:
        chair = any(fx.riders[t].get("wheelchair") for t in live) or rq.wheelchair
        status = "no_accessible_route" if chair else "no_feasible_route"
        p = PendingPlan("ASSIST", "smart_rescue", s.revision, None, None, viewer, trip.trip_id, trigger,
                        status=status, alternatives=comparisons, rejected=eng.rejections(Counter()),
                        old_fares=dict(trip.fares), affected=[])
        p.extra["operator_assistance"] = True
        return _register(s, p)
    label, desc, best = feasible[0]
    opt = eng.option(best, label, viewer, rq.fare_cap, rq.deadline, relaxed=desc)
    alts = [eng.option(c, l, viewer, rq.fare_cap, rq.deadline, relaxed=d) for l, d, c in feasible[1:]] + comparisons
    affected = [t for t in best.tokens
                if t not in trip.fares or best.shares[t] > trip.fares[t]
                or dict(zip(best.tokens, best.pickups))[t] != trip.pickups.get(t)]
    p = PendingPlan(label, "smart_rescue", s.revision, opt, best, viewer, trip.trip_id, trigger,
                    old_fares={t: trip.fares.get(t, 0) for t in best.tokens}, new_fares=dict(best.shares),
                    affected=affected, alternatives=alts, rejected=eng.rejections(Counter()))
    _register(s, p)
    if not affected:                       # e.g. vehicle swap, same fare and times: nothing to approve
        _commit_proposal(s, p)
    return p


def _rescue_shuttle(s: Session, eng: Engine, trip: Trip, rq: Requester, live: list[str], trigger: str) -> Optional[PendingPlan]:
    fx = s.fx
    sh = trip.shuttle
    sid = sh["shuttle_id"]
    n = len(live)
    seats = s.shuttle_seats.get(sid, 0)
    deadline = min(trip.deadlines[t] for t in live)
    hub_ready = max(sh["hub_arrival"], s.sim_min)
    if seats >= n and trip.arrival <= deadline and len(live) == len(trip.members):
        return None
    zone = fx.zones[trip.zone_id]
    hub = zone["hub"]
    campus_point = fx.campuses[trip.campus_id]["gate_point"]
    buffer = int(fx.tariffs["TRANSFER_BUFFER_MIN"])
    for other in sorted(fx.shuttles, key=lambda x: x["depart"]):
        if other["shuttle_id"] == sid or other["hub"] != hub or other["campus_id"] != trip.campus_id:
            continue
        subj = f"shuttle:{other['shuttle_id']}"
        if to_min(other["depart"]) < hub_ready + buffer:
            eng._reason(subj, "TRANSFER_TOO_TIGHT", "departs before a safe transfer")
        elif to_min(other["arrive"]) > deadline:
            eng._reason(subj, "LATE_ARRIVAL", f"arrives {other['arrive']} after deadline {to_hhmm(deadline)}")
        elif s.shuttle_seats.get(other["shuttle_id"], 0) < n:
            eng._reason(subj, "INSUFFICIENT_SEATS", "not enough seats")
    eng.audit.groups += 1
    eng.audit.routes += 1
    ext = leg(fx, hub, campus_point)
    arrival = hub_ready + s.traffic.duration(ext, hub_ready)
    members = [fx.riders[t] for t in live]
    vehicle, vrej = vehicle_for_group(fx, members, trip.zone_id, trip.campus_id, rq.big_car, s.vehicles_out)
    incurred = {t: sh["feeder_share"][t] for t in live}
    if vehicle is None or arrival > deadline:
        for subj, code, detail in vrej:
            eng._reason(subj, code, detail)
        p = PendingPlan("ASSIST", "smart_rescue", s.revision, None, None, rq.token, trip.trip_id, trigger,
                        status="no_feasible_route", rejected=eng.rejections(Counter()), old_fares=dict(trip.fares))
        p.extra["operator_assistance"] = True
        return _register(s, p)
    inc = pricing.shared_segment_split(ext.km, trip.rate, n, False, eng.BASE, eng.FEE)
    shares = {t: pricing.rescue_total(incurred[t], i) for t, i in zip(live, inc.shares)}
    vehicle_total = sum(incurred.values()) + inc.vehicle_total
    pricing.check_conservation(list(shares.values()), vehicle_total)
    cap_viol = [t for t in live if shares[t] > (rq.fare_cap if t == rq.token else int(fx.riders[t]["fare_cap_fils"]))]
    cand = Candidate("main_road_shuttle", members, [sh["feeder_depart"]] * n, arrival,
                     {t: sh["leave_home"] for t in live}, [sh["feeder_km"], ext.km], shares, dict(shares),
                     vehicle_total, VehicleChoice(trip.vehicle_id, trip.vehicle_class, trip.rate),
                     {t: 0 for t in live}, {t: trip.deadlines[t] for t in live}, True, cap_viol)
    opt = eng.option(cand, "R1", rq.token, rq.fare_cap, deadline, relaxed="extend feeder to campus (incurred + incremental)")
    opt = opt.model_copy(update={"fare": opt.fare.model_copy(update={"your_breakdown": [
        FareComponent(label="incurred feeder share", fils=incurred[rq.token]),
        FareComponent(label="incremental extension share", fils=shares[rq.token] - incurred[rq.token])]})})
    affected = [t for t in live if shares[t] > trip.fares[t] or bool(cap_viol)]
    p = PendingPlan("R1", "smart_rescue", s.revision, opt, cand, rq.token, trip.trip_id, trigger,
                    old_fares={t: trip.fares[t] for t in live}, new_fares=shares, affected=affected,
                    rejected=eng.rejections(Counter()))
    p.extra.update(shuttle_extension=True, incurred=incurred,
                   incremental={t: shares[t] - incurred[t] for t in live})
    return _register(s, p)


def proposal_view(p: PendingPlan) -> Proposal:
    riders = [RiderDelta(token=t, old_fare_fils=p.old_fares.get(t, 0), new_fare_fils=p.new_fares.get(t, 0),
                         delta_fils=p.new_fares.get(t, 0) - p.old_fares.get(t, 0), consented=t in p.consents)
              for t in (p.affected or [])]
    return Proposal(proposal_id=p.plan_id, kind=p.kind, trigger=p.trigger, trip_id=p.trip_id or "TRP-NONE",
                    plan_revision=p.revision, status=p.status, option=p.option, alternatives=p.alternatives,
                    rejected=p.rejected, riders=riders, requires_approval=bool(p.affected) and p.status == "pending",
                    operator_assistance=bool(p.extra.get("operator_assistance")))


# ============================================================================ simulation events
def apply_event(s: Session, req: SimulationEventRequest) -> EventResponse:
    t0 = time.perf_counter()
    fx = s.fx
    if req.event == "reset":
        s.reset()
        return EventResponse(session_id=s.session_id, event="reset", target="all", sim_time=to_hhmm(s.sim_min),
                             plan_revision=s.revision, proposals=[], unaffected_trips=[], compute_ms=_ms(t0),
                             audit=Audit().model())
    sim_time = req.sim_time or fx.scenarios.get(_scenario_key(req.event), {}).get("sim_time")
    if sim_time is None:
        raise ApiError(422, "SIM_TIME_REQUIRED", "sim_time is required")
    target = req.target
    if req.event == "rider_cancel" and target not in fx.riders:
        raise ApiError(404, "UNKNOWN_TARGET", "unknown rider")
    if req.event == "shuttle_full" and target not in {x["shuttle_id"] for x in fx.shuttles}:
        raise ApiError(404, "UNKNOWN_TARGET", "unknown shuttle")
    if req.event == "vehicle_unavailable" and target not in {v["vehicle_id"] for v in fx.vehicles}:
        raise ApiError(404, "UNKNOWN_TARGET", "unknown vehicle")
    mult = None
    if req.event == "traffic":
        try:
            mult = Fraction(req.multiplier or fx.scenarios["traffic"]["multiplier"])
        except (ValueError, ZeroDivisionError):
            raise ApiError(422, "BAD_MULTIPLIER", "invalid multiplier") from None
        if not Fraction(1) <= mult <= Fraction(3):
            raise ApiError(422, "BAD_MULTIPLIER", "multiplier must be between 1 and 3")
    s.advance_clock(sim_time)
    s.bump()
    affected: list[Trip] = []
    booked = [t for t in s.trips.values() if t.status == "booked"]
    if req.event == "rider_cancel":
        s.cancelled.add(target)
        for t in booked:
            if target in t.members:
                refund = t.paid.pop(target, 0)
                if refund:
                    s.post(target, t.trip_id, "refund", refund, "Trip canceled — refund")   # fixture: no cancellation fee
                t.fares.pop(target, None)
                affected.append(t)
    elif req.event == "traffic":
        s.traffic_override = TrafficOverride(s.sim_min, mult)
        affected = [t for t in booked if t.arrival > s.sim_min]
    elif req.event == "shuttle_full":
        s.shuttle_seats[target] = 0
        affected = [t for t in booked if t.shuttle and t.shuttle["shuttle_id"] == target and not t.shuttle["extended"]]
    elif req.event == "vehicle_unavailable":
        s.vehicles_out.add(target)
        affected = [t for t in booked if t.vehicle_id == target]
    eng = Engine(s)
    proposals = []
    for t in affected:
        p = rescue_trip(s, eng, t, req.event)
        if p is not None:
            proposals.append(proposal_view(p))
    unaffected = [t.trip_id for t in booked if t.trip_id not in {p.trip_id for p in proposals}]
    return EventResponse(session_id=s.session_id, event=req.event, target=target, sim_time=to_hhmm(s.sim_min),
                         plan_revision=s.revision, proposals=proposals, unaffected_trips=unaffected,
                         compute_ms=_ms(t0), audit=eng.audit.model())


def _scenario_key(event: str) -> str:
    return {"rider_cancel": "cancel", "traffic": "traffic", "shuttle_full": "full", "vehicle_unavailable": "wav_out"}[event]


# ============================================================================ class shift
def class_shift(s: Session, req: ShiftClassRequest) -> ShiftClassResponse:
    t0 = time.perf_counter()
    trip = s.trips.get(req.trip_id)
    if trip is None or trip.status != "booked" or req.rider_token not in trip.members:
        raise ApiError(404, "TRIP_NOT_FOUND", "no booked trip for this rider")
    s.advance_clock(req.request_time)
    if s.timetable is None:
        raise ApiError(409, "NO_TIMETABLE", "confirm a timetable first (parse or manual entry)")
    from datetime import date
    day = DAY_NAMES[date.fromisoformat(trip.service_date).weekday()]
    later = sorted(to_min(c["start"]) for c in s.timetable
                   if c["day"] == day and c.get("start") and to_min(c["start"]) > trip.class_start)
    dispatch = min(trip.pickups.values())
    paid = trip.paid.get(req.rider_token, 0)
    base = dict(session_id=s.session_id, vision_call=False, current_class=to_hhmm(trip.class_start),
                plan_revision=s.revision, refund_fils=0)
    if s.sim_min >= dispatch:
        raise ApiError(409, "ALREADY_DISPATCHED", "trip already dispatched; use Smart Rescue instead")
    free = dispatch - s.sim_min > int(s.fx.tariffs["FREE_RELEASE_MIN"])
    if not later:
        return ShiftClassResponse(**base, status="no_next_class", free_release=free, cancel_only_option={
            "action": "cancel_only", "refund_fils": paid if free else 0,
            "policy": "free release > 30 min before dispatch (fixture); otherwise Jeeny policy"}, compute_ms=_ms(t0))
    if not free:
        return ShiftClassResponse(**base, status="release_requires_operator_policy", next_class=to_hhmm(later[0]),
                                  free_release=False, compute_ms=_ms(t0))
    nxt = later[0]
    prefs = dict(trip.prefs)
    eng0 = Engine(s)
    buffer = int(prefs.get("arrival_buffer_min", 10))
    acc = prefs.get("accessibility", {})
    rq = eng0.requester(req.rider_token, trip.zone_id, trip.campus_id, trip.gender_pool, trip.service_date, nxt,
                        buffer, bool(acc.get("wheelchair")), bool(acc.get("big_car")),
                        int(prefs.get("fare_cap_fils", s.fx.riders[req.rider_token]["fare_cap_fils"])))
    desired = len(trip.members) - 1
    exclude = s.busy_riders(except_trip=trip.trip_id) | (set(trip.members) - {req.rider_token})
    res = run_planner(s, rq, desired, trip.mode, None, exclude, allow_best_deal=True, id_prefix="CS-")
    if not res.options:
        return ShiftClassResponse(**base, status="no_feasible_route", next_class=to_hhmm(nxt), free_release=True,
                                  compute_ms=_ms(t0))
    opt, cand = res.options[0]
    opt = opt.model_copy(update={"plan_id": "CS1"})
    new_prefs = dict(prefs, class_start=to_hhmm(nxt), preferred_pickup=None, desired_companions=len(cand.tokens) - 1)
    p = PendingPlan("CS1", "class_shift", s.revision, opt, cand, req.rider_token, trip.trip_id, "class_canceled",
                    old_fares={req.rider_token: paid}, new_fares={req.rider_token: cand.shares[req.rider_token]},
                    affected=[req.rider_token], request=new_prefs)
    p.extra["refund_fils"] = paid
    _register(s, p)
    others = [t for t in trip.members if t != req.rider_token and t not in s.cancelled]
    charge = cand.pay_now[req.rider_token]
    return ShiftClassResponse(**{**base, "refund_fils": paid}, status="proposed", next_class=to_hhmm(nxt),
                              proposal=proposal_view(p), new_charge_fils=charge, net_change_fils=charge - paid,
                              free_release=True, affected_co_riders=others, compute_ms=_ms(t0))


# ============================================================================ emergency (< 10 min)
def emergency(s: Session, req: EmergencyRequest, allow_insertion: bool = True,
              pre_rejected: Optional[list[Rejection]] = None) -> EmergencyResponse:
    t0 = time.perf_counter()
    fx = s.fx
    rider = fx.rider(req.rider_token)
    if rider is None:
        raise ApiError(404, "RIDER_NOT_FOUND", "unknown rider token")
    s.advance_clock(req.request_time)
    s.primary = req.rider_token
    eng = Engine(s)
    date_s = req.service_date.isoformat()
    deadline = to_min(req.class_start) - req.arrival_buffer_min
    cap = req.fare_cap_fils if req.fare_cap_fils is not None else int(rider["fare_cap_fils"])
    t = fx.tariffs
    rate, base, fee, dwell = int(t["KM_STD"]), int(t["BASE"]), int(t["FEE"]), int(t["DWELL_MIN"])
    max_wait = int(t["EMERGENCY_MAX_PICKUP_MIN"])
    my_cell = home_cell(rider)
    rejected: list[Rejection] = list(pre_rejected or [])
    best = None
    if rider.get("wheelchair"):
        rejected.append(Rejection(subject="emergency_pool", code="NO_RAMP", detail="no verified ramp vehicle en route"))
    for at in sorted(s.active_trips.values(), key=lambda x: x["trip_id"]):
        if rider.get("wheelchair") or not allow_insertion:
            break
        subj = f"trip:{at['trip_id']}"
        eng.audit.groups += 1
        eng.audit.routes += 1

        def rej(code: str, detail: str) -> None:
            rejected.append(Rejection(subject=subj, code=code, detail=detail))
            eng.audit.rej[code] += 1
        if at["service_date"] != date_s or at["campus_id"] != rider["campus_id"]:
            continue
        if at["gender_pool"] != rider["gender_pool"]:
            rej("GENDER_MISMATCH", "different pool")
            continue
        if at["vehicle_id"] in s.vehicles_out:
            rej("VEHICLE_UNAVAILABLE", "vehicle unavailable")
            continue
        existing = [r for r in at["riders"] if r["token"] not in s.cancelled]
        if req.rider_token in {r["token"] for r in existing}:
            raise ApiError(409, "ALREADY_BOOKED", "rider already on this trip")
        if int(at["seats_offered"]) - len(existing) < 1:
            rej("INSUFFICIENT_SEATS", "no free seat")
            continue
        if not adjacent(my_cell, point_cell(fx, at["pass_point"]), 1):
            rej("NOT_ADJACENT", "trip does not pass an adjacent H3 cell")
            continue
        pickup = to_min(at["pass_eta"])
        if pickup < s.sim_min or pickup > s.sim_min + max_wait:
            rej("PICKUP_TOO_LATE", f"pickup must be within {max_wait} min of request")
            continue
        remaining = int(at["remaining_min_after_pickup"])
        if s.traffic_override and pickup + dwell >= s.traffic_override.from_min:
            remaining = math.ceil(remaining * s.traffic_override.multiplier)
        arrival = pickup + dwell + remaining
        if arrival > deadline:
            rej("LATE_ARRIVAL", "newcomer would miss deadline")
            continue
        dls = {r["token"]: rider_deadline(fx.riders[r["token"]], date_s) for r in existing}
        if any(d is None or arrival > d for d in dls.values()):
            rej("INSERTION_HARMS_RIDERS", "an existing rider would miss their deadline")
            continue
        n_after = len(existing) + 1
        km = Fraction(at["remaining_km_after_pickup"])
        exact = Fraction(base + fee, n_after) + km * rate / n_after
        base_share = int(exact) if exact.denominator == 1 else int(exact + Fraction(1, 2))
        fare, premium = pricing.emergency_newcomer_share(base_share, fx.frac["SURGE_EMG"])
        detour = pricing.detour_cost(Fraction(at["detour_km"]), rate)
        if premium < detour:
            rej("PREMIUM_BELOW_DETOUR_COST", "surge premium does not cover the detour")
            continue
        if fare > cap:
            rej("FARE_CAP", "above rider fare cap")
            continue
        if best is None or arrival < best[1]:
            best = (at, arrival, pickup, base_share, fare, premium, detour, existing, dls, km)
    if best is None:
        solo_leg = fx.leg(rider["stop_id"], fx.campuses[rider["campus_id"]]["gate_point"])
        quote = pricing.solo_fare(solo_leg.km, rate, base, fee) if solo_leg else None
        eligible = quote is not None and quote <= cap and not rider.get("wheelchair")
        fallback = {"product": "standard_solo_jeeny", "dispatched": False, "bookable_here": False,
                    "within_fare_cap": bool(quote is not None and quote <= cap), "handoff_eligible": eligible,
                    "note": "hand-off to Jeeny's standard product; simulated quote, no pickup guarantee"}
        if quote is not None:
            fallback["simulated_quote_fils"] = quote
        status = "standard_solo_jeeny" if quote is not None else "no_feasible_route"
        return EmergencyResponse(session_id=s.session_id, status=status, fallback=fallback, rejected=rejected,
                                 requires_approval=False, plan_revision=s.revision, compute_ms=_ms(t0))
    at, arrival, pickup, base_share, fare, premium, detour, existing, dls, km = best
    old_total = sum(r["fare_fils"] for r in existing)
    riders_view = [RiderDelta(token=r["token"], old_fare_fils=r["fare_fils"], new_fare_fils=r["fare_fils"],
                              delta_fils=0, consented=True) for r in existing]
    vt = old_total + fare
    members = [rider] + [fx.riders[r["token"]] for r in existing]
    cand = Candidate("door_to_door", [rider], [pickup], arrival, {req.rider_token: pickup}, [km],
                     {req.rider_token: fare}, {req.rider_token: fare}, vt,
                     VehicleChoice(at["vehicle_id"], "sedan", rate), {req.rider_token: 0},
                     {req.rider_token: deadline, **{k: v for k, v in dls.items()}}, True, [])
    del members
    opt = PlanOption(plan_id="EM1", mode="door_to_door", relaxed="emergency insertion (×1.25 newcomer only)",
                     leave_home=to_hhmm(pickup), arrival=to_hhmm(arrival), deadline=to_hhmm(deadline),
                     pickup_order=[req.rider_token], pickups=[PickupStop(position=1, token=req.rider_token,
                                                                         pickup_time=to_hhmm(pickup))],
                     vehicle_class="sedan",
                     fare=FareInfo(your_share_fils=fare, vehicle_total_fils=vt,
                                   shares=[FareShare(position=1, token=req.rider_token, share_fils=fare)],
                                   your_breakdown=[FareComponent(label="shared share", fils=base_share),
                                                   FareComponent(label="emergency premium (×1.25)", fils=premium)]),
                     bookable=True, cap_status="within_cap")
    p = PendingPlan("EM1", "emergency", s.revision, opt, cand, req.rider_token, at["trip_id"], "emergency",
                    old_fares={req.rider_token: 0}, new_fares={req.rider_token: fare}, affected=[req.rider_token])
    p.extra["class_start"] = to_min(req.class_start)
    _register(s, p)
    ins = EmergencyInsertion(trip_id=at["trip_id"], pickup_time=to_hhmm(pickup), arrival=to_hhmm(arrival),
                             base_share_fils=base_share, fare_fils=fare, surge_premium_fils=premium,
                             detour_cost_fils=detour, existing_riders=riders_view)
    return EmergencyResponse(session_id=s.session_id, status="insertion_proposed", proposal_id=p.plan_id,
                             insertion=ins, rejected=rejected, requires_approval=True, plan_revision=s.revision,
                             compute_ms=_ms(t0))

