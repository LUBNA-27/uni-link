"""Deterministic route construction (Rev. E §11.2). Fixture distances/durations are the source of truth.

door_to_door (DEFAULT): requester first, then companions in corridor progression toward campus.
Every successive stop must be strictly closer to campus (no backward leg). Times are scheduled
backwards from a target arrival (class_start - buffer - slack) or forwards from a preferred pickup,
then always replayed forwards and verified. Pickup time = arrival at the door; dwell follows.

main_road_shuttle: walk → shared feeder (meet point → hub) → shuttle, with ≥ TRANSFER_BUFFER_MIN.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Optional

from .fixtures import Fixtures, Leg
from .traffic_adapter import TrafficAdapter

_ZERO = Leg(Fraction(0), 0, 0)
SEARCH_HORIZON_MIN = 240


class RouteError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def leg(fx: Fixtures, a: str, b: str) -> Leg:
    if a == b:
        return _ZERO
    found = fx.leg(a, b)
    if found is None:
        raise RouteError("ROUTE_DATA_MISSING", f"no fixture leg {a}->{b}")
    return found


@dataclass(frozen=True)
class DoorRoute:
    order: tuple[str, ...]                 # tokens, pickup order
    stops: tuple[str, ...]                 # private stop ids (never serialised)
    dwell: tuple[int, ...]
    leg_km: tuple[Fraction, ...]           # leg i ends at next pickup (or campus)
    pickups: tuple[int, ...] = ()
    arrival: int = 0

    @property
    def leave_home(self) -> int:
        return self.pickups[0]

    @property
    def total_km(self) -> Fraction:
        return sum(self.leg_km, Fraction(0))


def corridor_order(fx: Fixtures, campus_point: str, first: dict[str, Any], others: list[dict[str, Any]],
                   fixed_prefix: tuple[dict[str, Any], ...] = ()) -> list[dict[str, Any]]:
    """Requester (or fixed onboard prefix) first, then remaining riders farthest-from-campus first,
    i.e. nearest to the requester first. Raises BACKWARD_LEG if the corridor is not monotone."""
    head = list(fixed_prefix) if fixed_prefix else [first]
    tail = sorted(others, key=lambda r: (-leg(fx, r["stop_id"], campus_point).km, r["token"]))
    seq = head + tail
    remaining = [leg(fx, r["stop_id"], campus_point).km for r in seq]
    for a, b, ra, rb in zip(seq, seq[1:], remaining, remaining[1:]):
        if a["stop_id"] != b["stop_id"] and not rb < ra:
            raise RouteError("BACKWARD_LEG", "pickup order would move away from campus")
    return seq


def build_door_route(fx: Fixtures, campus_point: str, ordered: list[dict[str, Any]]) -> DoorRoute:
    d_std, d_chair = int(fx.tariffs["DWELL_MIN"]), int(fx.tariffs["DWELL_WHEELCHAIR_MIN"])
    stops = tuple(r["stop_id"] for r in ordered)
    nxt = list(stops[1:]) + [campus_point]
    kms = tuple(leg(fx, a, b).km for a, b in zip(stops, nxt))
    return DoorRoute(tuple(r["token"] for r in ordered), stops,
                     tuple(d_chair if r.get("wheelchair") else d_std for r in ordered), kms)


def replay(fx: Fixtures, traffic: TrafficAdapter, route: DoorRoute, campus_point: str, start: int,
           fixed_pickups: Optional[tuple[int, ...]] = None) -> DoorRoute:
    """Forward replay from first pickup at `start`. `fixed_pickups` pins already-completed pickups."""
    t = start
    pickups: list[int] = []
    nxt = list(route.stops[1:]) + [campus_point]
    for i, (stop, to, dwell) in enumerate(zip(route.stops, nxt, route.dwell)):
        if fixed_pickups and i < len(fixed_pickups):
            t = fixed_pickups[i]
        pickups.append(t)
        t += dwell
        t += traffic.duration(leg(fx, stop, to), t)
    return DoorRoute(route.order, route.stops, route.dwell, route.leg_km, tuple(pickups), t)


def schedule_forward(fx, traffic, route, campus_point, start, fixed_pickups=None) -> DoorRoute:
    return replay(fx, traffic, route, campus_point, start, fixed_pickups)


def schedule_backward(fx: Fixtures, traffic: TrafficAdapter, route: DoorRoute, campus_point: str,
                      target_arrival: int, earliest_start: int) -> Optional[DoorRoute]:
    """Latest first-pickup such that the forward replay arrives by target_arrival."""
    for start in range(target_arrival - 1, max(earliest_start, target_arrival - SEARCH_HORIZON_MIN) - 1, -1):
        r = replay(fx, traffic, route, campus_point, start)
        if r.arrival <= target_arrival:
            return r
    return None


@dataclass
class ShuttlePlan:
    shuttle_id: str
    walk_min: int
    leave_home: int
    feeder_depart: int
    hub_arrival: int
    shuttle_depart: int
    arrival: int
    feeder_km: Fraction
    buffer_min: int
    rejections: list[tuple[str, str, str]] = field(default_factory=list)


def plan_main_road_shuttle(fx: Fixtures, traffic: TrafficAdapter, zone_id: str, campus_id: str, group_size: int,
                           wheelchair: bool, deadline: int, sim_min: int, seats_left: dict[str, int]
                           ) -> tuple[Optional[ShuttlePlan], list[tuple[str, str, str]]]:
    zone = fx.zones[zone_id]
    meet, hub, walk = zone["meet_point"], zone["hub"], int(zone["walk_to_meet_min"])
    buffer = int(fx.tariffs["TRANSFER_BUFFER_MIN"])
    rejections: list[tuple[str, str, str]] = []
    try:
        feeder = leg(fx, meet, hub)
    except RouteError as e:
        return None, [(f"zone:{zone_id}", e.code, e.detail)]
    best: Optional[ShuttlePlan] = None
    from .timeutil import to_min, to_hhmm
    for s in sorted((s for s in fx.shuttles if s["campus_id"] == campus_id and s["hub"] == hub),
                    key=lambda s: s["depart"]):
        sid, dep, arr = s["shuttle_id"], to_min(s["depart"]), to_min(s["arrive"])
        subject = f"shuttle:{sid}"
        if wheelchair and not s.get("access_verified"):
            rejections.append((subject, "ACCESSIBILITY_UNVERIFIED", "shuttle accessibility not verified"))
            continue
        if arr > deadline:
            rejections.append((subject, "LATE_ARRIVAL", f"arrives {to_hhmm(arr)} after deadline {to_hhmm(deadline)}"))
            continue
        if seats_left.get(sid, int(s["seats"])) < group_size:
            rejections.append((subject, "INSUFFICIENT_SEATS", f"{seats_left.get(sid, s['seats'])} seats for group of {group_size}"))
            continue
        target_hub = dep - buffer
        feeder_dep = None
        for start in range(target_hub - 1, target_hub - SEARCH_HORIZON_MIN, -1):
            if start + traffic.duration(feeder, start) <= target_hub:
                feeder_dep = start
                break
        if feeder_dep is None or feeder_dep - walk < sim_min:
            rejections.append((subject, "TRANSFER_TOO_TIGHT", f"cannot reach hub {buffer} min before departure"))
            continue
        hub_arr = feeder_dep + traffic.duration(feeder, feeder_dep)
        plan = ShuttlePlan(sid, walk, feeder_dep - walk, feeder_dep, hub_arr, dep, arr, feeder.km, dep - hub_arr)
        if best is None or plan.shuttle_depart > best.shuttle_depart:
            best = plan
    return best, rejections
