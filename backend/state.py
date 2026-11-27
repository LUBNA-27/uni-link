"""Per-session simulation state. Sessions are fully isolated; every session starts from a deep copy
of read-only fixtures. All mutations happen under the session lock (see main.py)."""
from __future__ import annotations

import copy
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Optional

from .fixtures import Fixtures
from .timeutil import to_hhmm, to_min
from .traffic_adapter import TrafficAdapter, TrafficOverride

INITIAL_SIM_TIME = "06:00"
INITIAL_REVISION = 1
DEFAULT_PRIMARY = "R-7K2"
MAX_SESSIONS = 256


@dataclass
class Trip:
    trip_id: str
    service_date: str
    campus_id: str
    zone_id: str
    mode: str
    gender_pool: str
    class_start: int
    requester: str
    members: list[str]                     # pickup order
    pickups: dict[str, int]
    arrival: int
    fares: dict[str, int]                  # current agreed fare per rider (incl. shuttle ticket)
    paid: dict[str, int]                   # actually debited per rider
    vehicle_id: str
    vehicle_class: str
    rate: int
    leg_km: list[Fraction]
    deadlines: dict[str, int]
    prefs: dict[str, Any]                  # the request preferences as booked
    plan_revision: int
    status: str = "booked"
    shuttle: Optional[dict[str, Any]] = None
    option: Any = None                      # internal PlanOption last agreed (for the wire TripView)
    flags: list[str] = field(default_factory=list)


@dataclass
class PendingPlan:
    """A quote or proposal that may be confirmed. Quotes/proposals have NO financial side effects."""
    plan_id: str
    kind: str                              # quote | smart_rescue | class_shift | emergency
    revision: int
    option: Any                            # schemas.PlanOption (public view)
    candidate: Any                         # replanner.Candidate (private, server-only)
    requester: str
    trip_id: Optional[str] = None
    trigger: str = ""
    old_fares: dict[str, int] = field(default_factory=dict)
    new_fares: dict[str, int] = field(default_factory=dict)
    affected: list[str] = field(default_factory=list)
    consents: set[str] = field(default_factory=set)
    status: str = "pending"
    alternatives: list[Any] = field(default_factory=list)
    rejected: list[Any] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    request: Any = None


@dataclass
class Session:
    session_id: str
    fx: Fixtures
    lock: threading.RLock = field(default_factory=threading.RLock)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.sim_min = to_min(INITIAL_SIM_TIME)
        self.revision = INITIAL_REVISION
        self.primary = DEFAULT_PRIMARY
        self.wallets: dict[str, int] = {t: int(r["wallet_fils"]) for t, r in self.fx.riders.items()}
        self.ledger: list[dict[str, Any]] = []
        self.trips: dict[str, Trip] = {}
        self.pending: dict[str, PendingPlan] = {}
        self.idempotency: dict[str, tuple[str, Any]] = {}
        self.charged: set[tuple[str, int, str]] = set()
        self.cancelled: set[str] = set()
        self.traffic_override: Optional[TrafficOverride] = None
        self.vehicles_out: set[str] = set()
        self.shuttle_seats: dict[str, int] = {s["shuttle_id"]: int(s["seats"]) for s in self.fx.shuttles}
        self.active_trips: dict[str, dict[str, Any]] = {t["trip_id"]: copy.deepcopy(t) for t in self.fx.active_trips}
        self.timetable_draft: Optional[list[dict[str, Any]]] = None
        self.timetable: Optional[list[dict[str, Any]]] = None
        self.trip_seq = 100
        self.entry_seq = 0
        self.last_plan_ids: list[str] = []
        self.wire_idem: dict[str, tuple[str, Any]] = {}

    # ------------------------------------------------------------------ helpers
    @property
    def traffic(self) -> TrafficAdapter:
        return TrafficAdapter(self.fx, self.traffic_override)

    def advance_clock(self, hhmm: Optional[str]) -> None:
        if hhmm is None:
            return
        t = to_min(hhmm)
        if t < self.sim_min:
            from .errors import ApiError
            raise ApiError(409, "CLOCK_BACKWARD", "simulation clock cannot move backwards except by reset")
        self.sim_min = t

    def bump(self) -> int:
        self.revision += 1
        return self.revision

    def new_trip_id(self) -> str:
        self.trip_seq += 1
        return f"TRP-S{self.trip_seq}"

    def busy_riders(self, except_trip: Optional[str] = None) -> set[str]:
        busy = set(self.cancelled)
        for t in self.trips.values():
            if t.status == "booked" and t.trip_id != except_trip:
                busy.update(t.members)
        for t in self.active_trips.values():
            busy.update(r["token"] for r in t["riders"])
        return busy

    def post(self, token: str, trip_id: str, kind: str, amount: int, note: str = "") -> None:
        if amount < 0:
            raise ValueError("ledger amount must be non-negative")
        if kind == "debit":
            self.wallets[token] -= amount
        else:
            self.wallets[token] += amount
        self.entry_seq += 1
        self.ledger.append({"entry_id": f"L{self.entry_seq:05d}", "token": token, "trip_id": trip_id,
                            "plan_revision": self.revision, "kind": kind, "amount_fils": amount,
                            "balance_after_fils": self.wallets[token], "at": to_hhmm(self.sim_min), "note": note})


class SessionStore:
    """Bounded in-memory store (LRU eviction) so arbitrary session ids cannot exhaust memory."""

    def __init__(self, fx: Fixtures, max_sessions: int = MAX_SESSIONS) -> None:
        self.fx = fx
        self.max = max_sessions
        self._s: "OrderedDict[str, Session]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, session_id: str) -> Session:
        with self._lock:
            s = self._s.get(session_id)
            if s is None:
                s = Session(session_id, self.fx)
                self._s[session_id] = s
                while len(self._s) > self.max:
                    self._s.popitem(last=False)
            else:
                self._s.move_to_end(session_id)
            return s

    def clear(self) -> None:
        with self._lock:
            self._s.clear()
