"""Candidate matching and HARD feasibility filters (Rev. E §11.1).

Order of operations is fixed: hard filters run BEFORE any ranking, and no caller can relax them.
H3 (res 8) cells are computed server-side from private home coordinates; only tokens leave the
server. Coarse fixture zones define the candidate corridor (the synthetic corridor riders are
~2 km apart, wider than an H3 res-8 k=1 disk); H3 grid_disk(k=1) adjacency gates Emergency
insertion and the proximity count in audits.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable, Optional

import h3

from .fixtures import Fixtures
from .timeutil import to_min

H3_RES = 8
MAX_CANDIDATES = 12
PUBLIC_RIDER_FIELDS = ("token",)  # the only rider attribute ever serialised to co-riders


@lru_cache(maxsize=4096)
def cell_of(lat: float, lng: float) -> str:
    return h3.latlng_to_cell(lat, lng, H3_RES)


def home_cell(rider: dict[str, Any]) -> str:
    return cell_of(float(rider["home_lat"]), float(rider["home_lng"]))


def point_cell(fx: Fixtures, point_id: str) -> str:
    lat, lng = fx.points[point_id]
    return cell_of(lat, lng)


def adjacent(cell_a: str, cell_b: str, k: int = 1) -> bool:
    return cell_b in h3.grid_disk(cell_a, k)


def rider_deadline(rider: dict[str, Any], service_date: str) -> Optional[int]:
    start = rider["schedule"].get(service_date)
    if start is None:
        return None
    return to_min(start) - int(rider.get("buffer_min", 10))


def soft_arrival_ok(rider: dict[str, Any], arrival_min: int, sim_min: int) -> bool:
    """Soft preference (relaxable only by Best Deal, never a hard constraint)."""
    pref = rider.get("latest_preferred_arrival")
    flex = rider.get("flexible_from")
    if pref is None or (flex is not None and sim_min >= to_min(flex)):
        return True
    return arrival_min <= to_min(pref)


@dataclass(frozen=True)
class Requester:
    token: str
    rider: dict[str, Any]
    zone_id: str
    campus_id: str
    gender_pool: str
    service_date: str
    class_start: int
    deadline: int
    wheelchair: bool
    big_car: bool
    fare_cap: int


def candidate_pool(fx: Fixtures, req: Requester, sim_min: int, unavailable: Iterable[str],
                   window_min: int) -> tuple[list[dict[str, Any]], Counter]:
    """Riders eligible to share with the requester. Rejections are aggregated by code only, so the
    requester never learns which token was rejected or why (no gender/opt-in leakage)."""
    rej: Counter = Counter()
    blocked = set(unavailable)
    pool = []
    for tok, r in fx.riders.items():
        if tok == req.token or r["zone_id"] != req.zone_id or r["campus_id"] != req.campus_id:
            continue
        start = r["schedule"].get(req.service_date)
        if start is None:
            continue
        if tok in blocked:
            rej["UNAVAILABLE_RIDER"] += 1
        elif r["gender_pool"] != req.gender_pool:
            rej["GENDER_MISMATCH"] += 1
        elif not r.get("opt_in", False):
            rej["NOT_OPTED_IN"] += 1
        elif abs(to_min(start) - req.class_start) > window_min:
            rej["OUTSIDE_TIME_WINDOW"] += 1
        else:
            pool.append(r)
    origin = req.rider["stop_id"]
    pool.sort(key=lambda r: (_km_from(fx, origin, r["stop_id"]), r["token"]))
    return pool[:MAX_CANDIDATES], rej


def _km_from(fx: Fixtures, a: str, b: str):
    leg = fx.leg(a, b)
    return leg.km if leg else 10**6


@dataclass(frozen=True)
class VehicleChoice:
    vehicle_id: str
    vehicle_class: str
    rate: int


def vehicle_for_group(fx: Fixtures, members: list[dict[str, Any]], zone_id: str, campus_id: str,
                      big_car_required: bool, unavailable: Iterable[str]) -> tuple[Optional[VehicleChoice], list[tuple[str, str, str]]]:
    """Hard vehicle filter. Returns the chosen vehicle (or None) and (subject, code, detail) rejections."""
    out = set(unavailable)
    n = len(members)
    chairs = sum(1 for m in members if m.get("wheelchair"))
    big = big_car_required or any(m.get("big_car") for m in members)
    rejections: list[tuple[str, str, str]] = []
    if chairs and fx.campuses[campus_id].get("step_free_dropoff") != "verified":
        return None, [(f"campus:{campus_id}", "ACCESSIBILITY_UNVERIFIED", "step-free drop-off not verified")]
    preferred = ("wav",) if chairs else (("big_car",) if big else ("sedan", "big_car"))
    chosen: Optional[VehicleChoice] = None
    for cls in preferred:
        for v in fx.vehicles:
            if v["class"] != cls or zone_id not in v["zone_ids"]:
                continue
            ok, code, detail = _vehicle_ok(v, n, chairs, out)
            if ok:
                if chosen is None:
                    rate = fx.tariffs["KM_STD"] if cls == "sedan" else fx.tariffs["KM_BIG"]
                    chosen = VehicleChoice(v["vehicle_id"], cls, int(rate))
                continue
            rejections.append((f"vehicle:{v['vehicle_id']}", code, detail))
        if chosen is not None and not chairs:
            return chosen, rejections
    # explain why every other vehicle class is excluded (the "Why this route?" panel)
    for v in fx.vehicles:
        if v["class"] not in preferred and zone_id in v["zone_ids"]:
            ok, code, detail = _vehicle_ok(v, n, chairs, out)
            if not ok:
                rejections.append((f"vehicle:{v['vehicle_id']}", code, detail))
            elif big and v["class"] == "sedan":
                rejections.append((f"vehicle:{v['vehicle_id']}", "INSUFFICIENT_SEATS", "big car required"))
    return chosen, rejections


def _vehicle_ok(v: dict[str, Any], n: int, chairs: int, out: set[str]) -> tuple[bool, str, str]:
    if chairs:
        if not v.get("has_ramp"):
            return False, "NO_RAMP", "wheelchair rider requires a ramp vehicle"
        if not v.get("ramp_verified"):
            return False, "ACCESSIBILITY_UNVERIFIED", "ramp not verified"
    if not v.get("available") or v["vehicle_id"] in out:
        return False, "VEHICLE_UNAVAILABLE", "vehicle unavailable"
    if chairs > int(v.get("wheelchair_slots", 0)) or (n - chairs) > int(v["seats"]):
        return False, "INSUFFICIENT_SEATS", f"capacity {v['seats']}+{v.get('wheelchair_slots', 0)} chair"
    return True, "", ""
