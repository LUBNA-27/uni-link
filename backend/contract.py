"""EXTERNAL wire contract — mirrors frontend/src/types.ts (round 2) exactly.

The engine keeps its internal models in schemas.py; wire.py translates between the two. Response
models forbid unknown fields so nothing private (coordinates, stop ids) can be serialised.
A few additive fields (compute_ms, audit, rejected, unbookable_comparisons) are measured engine
evidence; TypeScript ignores extra fields.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_serializer

from .schemas import Audit, CampusId, HHMM, IdemKey, RiderToken, SessionId, ZoneId

Weekday = Literal["Sun", "Mon", "Tue", "Wed", "Thu"]
EditableField = Literal["course", "weekday", "start", "end", "room"]
ClassId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]{1,64}$")]
PlanIdIn = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9-]{0,40}$")]
TripIdIn = Annotated[str, StringConstraints(pattern=r"^TRP-[A-Z0-9-]{1,32}$")]
Fils = Annotated[int, Field(ge=0, le=10_000_000)]


class _In(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ----------------------------------------------------------------------------- timetable
class ClassItem(_In):
    id: ClassId
    course: Annotated[str, StringConstraints(max_length=80)] = ""
    weekday: Weekday
    start: Union[HHMM, Literal[""]]
    end: Optional[Union[HHMM, Literal[""]]] = None
    room: Optional[Annotated[str, StringConstraints(max_length=60)]] = None


class ClassItemOut(_Out):
    id: str
    course: str
    weekday: Weekday
    start: str
    end: Optional[str] = None
    room: Optional[str] = None


class UncertainField(_Out):
    class_id: str
    field: EditableField
    reason: str


class TimetableRequest(_In):
    session_id: SessionId
    classes: list[ClassItem] = Field(min_length=1, max_length=40)

    @field_validator("classes")
    @classmethod
    def _unique_ids(cls, v: list[ClassItem]) -> list[ClassItem]:
        if len({c.id for c in v}) != len(v):
            raise ValueError("class ids must be unique")
        return v


class TimetableResponse(_Out):
    session_id: str
    classes: list[ClassItemOut]
    uncertain_fields: list[UncertainField]
    inference_source: Literal["gemini_vision", "manual", "fixture"]
    model: Optional[str] = None
    source: Literal["simulation", "inference"]
    # additive evidence, only when the model was really called (never contains credentials)
    inference_ms: Optional[float] = None
    usage: Optional[dict[str, int]] = None


class TimetableConfirmResponse(_Out):
    session_id: str
    confirmed: bool
    class_count: int
    invalidated_plans: bool


# ----------------------------------------------------------------------------- plan
class AccessibilityIn(_In):
    wheelchair: bool = False
    big_car: bool = False


class PlanRequest(_In):
    session_id: SessionId
    rider_token: RiderToken
    campus_id: CampusId
    zone_id: ZoneId
    service_date: date
    class_start: HHMM
    arrival_buffer_min: int = Field(default=10, ge=0, le=60)
    pickup_mode: Literal["door_to_door", "main_road_shuttle"] = "door_to_door"
    gender_pool: Literal["female_only", "male_only"]
    desired_companions: int = Field(ge=0, le=3)
    booking: Literal["day_ahead", "on_demand"] = "day_ahead"
    preferred_pickup: Optional[HHMM] = None
    fare_cap_fils: Fils
    accessibility: AccessibilityIn = AccessibilityIn()
    sharing_opt_in: bool = True


class AccessibleDropoff(_Out):
    label: str
    source: str
    verified: bool


class Pickup(_Out):
    rider_token: str
    landmark: str
    time: str
    is_you: bool


class FareShare(_Out):
    rider_token: str
    share_fils: int


class Fare(_Out):
    your_share_fils: int
    shares: Optional[list[FareShare]] = None
    vehicle_total_fils: int
    hypothetical_reference_fils: Optional[int] = None
    delta_vs_reference_fils: Optional[int] = None


class Vehicle(_Out):
    kind: Literal["sedan", "big_car", "wav"]
    label: str
    wheelchair_accessible: bool


class PlanOption(_Out):
    plan_id: str
    relaxed: Optional[str]
    utility: Optional[float] = None
    leave_home: str
    arrival: str
    deadline: Optional[str] = None
    pickup_order: list[str]
    pickups: Optional[list[Pickup]] = None
    fare: Fare
    vehicle: Optional[Vehicle] = None
    accessible_dropoff: Optional[AccessibleDropoff] = None
    hard_filters_passed: Optional[list[str]] = None
    flags: Optional[list[str]] = None

    @model_serializer(mode="wrap")
    def _keep_relaxed(self, handler):  # noqa: ANN001
        # responses drop None optionals (types.ts uses `?:`), but `relaxed: string | null` is required
        data = handler(self)
        data.setdefault("relaxed", None)
        return data


class Reason(_Out):
    code: str
    message: str


class Assistance(_Out):
    message: str


class RejectionOut(_Out):
    subject: str
    code: str
    detail: str
    count: int = 1


class PlanResponse(_Out):
    session_id: str
    plan_revision: int
    status: Literal["exact_match", "best_deal_proposed", "no_feasible_route", "no_accessible_route"]
    exact_match_found: bool
    options: list[PlanOption]
    reason: Optional[Reason] = None
    assistance: Optional[Assistance] = None
    requires_approval: bool
    source: Literal["simulation"] = "simulation"
    # additive, measured engine evidence (not in types.ts; ignored by the UI)
    unbookable_comparisons: list[PlanOption] = []
    rejected: list[RejectionOut] = []
    compute_ms: float = 0.0
    audit: Optional[Audit] = None


# ----------------------------------------------------------------------------- confirm / consent
class ConfirmRequest(_In):
    session_id: SessionId
    rider_token: RiderToken
    plan_id: PlanIdIn
    plan_revision: int = Field(ge=0, le=1_000_000)
    accepted_fare_fils: Fils
    idempotency_key: IdemKey
    decision: Literal["accept", "decline", "cancel_trip"] = "accept"
    replaces_trip_id: Optional[TripIdIn] = None


class ConsentEntry(_Out):
    rider_token: str
    label: str
    state: Literal["pending", "accepted", "declined"]


class Wallet(_Out):
    balance_fils: int


class ConfirmResponse(_Out):
    session_id: str
    revision: int
    status: Literal["confirmed", "awaiting_consent", "declined", "canceled"]
    trip_id: Optional[str] = None
    plan: Optional[PlanOption] = None
    amount_paid_fils: Optional[int] = None
    wallet: Optional[Wallet] = None
    pending_consents: Optional[list[ConsentEntry]] = None
    idempotent_replay: Optional[bool] = None
    source: Literal["simulation"] = "simulation"


# ----------------------------------------------------------------------------- proposals
class ProposalAlternative(_Out):
    label: str
    your_share_fils: int
    delta_fils: int
    flags: Optional[list[str]] = None
    selectable: bool


class Proposal(_Out):
    proposal_id: str
    kind: Literal["smart_rescue", "class_shift", "emergency"]
    message: str
    plan_revision: int
    plan: PlanOption
    previous_your_share_fils: Optional[int] = None
    delta_fils: int
    refund_fils: Optional[int] = None
    new_charge_fils: Optional[int] = None
    next_class: Optional[ClassItemOut] = None
    requires_approval: bool
    consents: list[ConsentEntry]
    alternatives: Optional[list[ProposalAlternative]] = None


class LedgerEntry(_Out):
    at: str
    kind: Literal["debit", "refund"]
    amount_fils: int
    note: str


class TripView(_Out):
    trip_id: str
    status: Literal["confirmed", "awaiting_consent", "dispatched", "canceled", "completed"]
    class_start: str
    plan: PlanOption
    amount_paid_fils: int
    has_next_class: bool


class WalletState(_Out):
    balance_fils: int
    ledger: list[LedgerEntry]


class SimState(_Out):
    session_id: str
    revision: int
    sim_time: str
    service_date: str
    trips: list[TripView]
    pending_proposals: list[Proposal]
    wallet: WalletState
    source: Literal["simulation"] = "simulation"


# ----------------------------------------------------------------------------- shift / emergency / events
class ShiftRequest(_In):
    session_id: SessionId
    trip_id: TripIdIn
    rider_token: RiderToken
    request_time: HHMM


class CancelOnly(_Out):
    refund_fils: int
    terms: str


class ShiftResponse(_Out):
    session_id: str
    revision: int
    status: Literal["shift_proposed", "no_next_class"]
    trip_id: str
    proposal: Optional[Proposal] = None
    cancel_only: Optional[CancelOnly] = None
    message: str
    source: Literal["simulation"] = "simulation"


class EmergencyRequest(_In):
    session_id: SessionId
    rider_token: RiderToken
    campus_id: CampusId
    zone_id: ZoneId
    service_date: date
    class_start: HHMM
    arrival_buffer_min: int = Field(default=10, ge=0, le=60)
    request_time: HHMM
    gender_pool: Literal["female_only", "male_only"]
    fare_cap_fils: Fils
    accessibility: AccessibilityIn = AccessibilityIn()
    sharing_opt_in: bool = True


class EmergencyResponse(_Out):
    session_id: str
    revision: int
    status: Literal["emergency_proposed", "no_option", "solo_handoff_eligible"]
    proposal: Optional[Proposal] = None
    newcomer_fare_fils: Optional[int] = None
    existing_riders_fares_unchanged: Optional[bool] = None
    reason: Optional[Reason] = None
    message: str
    source: Literal["simulation"] = "simulation"


class SimEventRequest(_In):
    session_id: SessionId
    event: Literal["cancel", "rider_cancel", "traffic", "shuttle_full", "vehicle_unavailable", "reset", "peer_consent"]
    target: Optional[Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,40}$")]] = None
    sim_time: Optional[HHMM] = None
    multiplier: Optional[Annotated[str, StringConstraints(pattern=r"^\d{1,2}(/\d{1,2})?$")]] = None
