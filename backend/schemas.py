"""FROZEN API contracts (Rev. E §10). All money is integer fils; times are local HH:MM on a service date.

Every response model uses extra="forbid" so no field (e.g. home_lat/lng, names, phones) can leak
through a response by accident: anything not declared here cannot be serialised.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

SessionId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
RiderToken = Annotated[str, StringConstraints(pattern=r"^R-[A-Z0-9]{3}$")]
HHMM = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
PlanId = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9-]{1,40}$")]
TripId = Annotated[str, StringConstraints(pattern=r"^TRP-[A-Z0-9-]{1,32}$")]
IdemKey = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{8,64}$")]
Fils = Annotated[int, Field(ge=0, le=10_000_000)]
SignedFils = Annotated[int, Field(ge=-10_000_000, le=10_000_000)]
CampusId = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2,10}$")]
ZoneId = Annotated[str, StringConstraints(pattern=r"^[a-z_]{2,32}$")]

PickupMode = Literal["door_to_door", "main_road_shuttle"]
GenderPool = Literal["female_only", "male_only"]
Day = Literal["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
Source = Literal["simulation"]
RejectCode = Literal["GENDER_MISMATCH", "LATE_ARRIVAL", "INSUFFICIENT_SEATS", "NO_RAMP", "ACCESSIBILITY_UNVERIFIED",
                     "VEHICLE_UNAVAILABLE", "TRANSFER_TOO_TIGHT", "FARE_CAP", "INSERTION_HARMS_RIDERS", "STALE_PLAN",
                     "NOT_OPTED_IN", "OUTSIDE_TIME_WINDOW", "SOFT_PREFERENCE", "BACKWARD_LEG", "ROUTE_DATA_MISSING",
                     "NOT_ADJACENT", "PICKUP_TOO_LATE", "PREMIUM_BELOW_DETOUR_COST", "PAST_PICKUP", "UNAVAILABLE_RIDER"]


class _In(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ----------------------------------------------------------------------------- requests
class Accessibility(_In):
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
    pickup_mode: PickupMode = "door_to_door"
    gender_pool: GenderPool
    desired_companions: int = Field(ge=0, le=3)
    booking: Literal["day_ahead", "emergency"] = "day_ahead"
    preferred_pickup: Optional[HHMM] = None
    fare_cap_fils: Fils
    accessibility: Accessibility = Accessibility()
    sharing_opt_in: bool = True


class ConfirmRequest(_In):
    session_id: SessionId
    rider_token: RiderToken
    plan_id: PlanId
    plan_revision: int = Field(ge=1, le=1_000_000)
    accepted_fare_fils: Fils
    idempotency_key: IdemKey


class ShiftClassRequest(_In):
    session_id: SessionId
    trip_id: TripId
    rider_token: RiderToken
    request_time: HHMM


class EmergencyRequest(_In):
    session_id: SessionId
    rider_token: RiderToken
    class_start: HHMM
    request_time: HHMM
    service_date: date
    arrival_buffer_min: int = Field(default=10, ge=0, le=60)
    fare_cap_fils: Optional[Fils] = None


class SimulationEventRequest(_In):
    session_id: SessionId
    event: Literal["rider_cancel", "traffic", "shuttle_full", "vehicle_unavailable", "reset"]
    target: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,32}$")] = "all"
    sim_time: Optional[HHMM] = None
    multiplier: Optional[Annotated[str, StringConstraints(pattern=r"^\d{1,2}(/\d{1,2})?$")]] = None


class TimetableClass(_In):
    day: Day
    course: Optional[Annotated[str, StringConstraints(max_length=80)]] = None
    start: Optional[HHMM] = None
    end: Optional[HHMM] = None
    building: Optional[Annotated[str, StringConstraints(max_length=60)]] = None


class TimetableManualRequest(_In):
    session_id: SessionId
    classes: list[TimetableClass] = Field(min_length=1, max_length=40)


class SplitInviteRequest(_In):
    session_id: SessionId
    trip_id: TripId
    rider_token: RiderToken
    invitee_token: RiderToken


class ParcelQuoteRequest(_In):
    session_id: SessionId
    trip_id: TripId
    declared_value_fils: Annotated[int, Field(ge=0, le=500_000)]
    size: Literal["small", "medium"]
    weight_g: Annotated[int, Field(ge=1, le=20_000)]


class VoiceIntentRequest(_In):
    session_id: SessionId
    transcript: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    locale: Literal["ar-JO", "en"] = "ar-JO"


class VoiceUnderstandRequest(_In):
    """Optional Gemini understanding for the prototype assistant. Read-only: never books or pays."""
    transcript: Annotated[str, StringConstraints(min_length=1, max_length=300)]
    locale: Literal["ar-JO", "en"] = "en"
    places: dict[Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{1,24}$")],
                 Annotated[str, StringConstraints(max_length=60)]] = Field(default_factory=dict, max_length=20)
    destinations: dict[Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{1,24}$")],
                       Annotated[str, StringConstraints(max_length=60)]] = Field(default_factory=dict, max_length=20)


# ----------------------------------------------------------------------------- responses
class ErrorBody(_Out):
    code: str
    message: str


class ErrorResponse(_Out):
    error: ErrorBody


class HealthResponse(_Out):
    status: Literal["ok"]
    fixture_version: str
    fixture_source: str
    gemini_ready: bool
    source: Source = "simulation"


class TimetableResponse(_Out):
    session_id: SessionId
    classes: list[TimetableClass]
    uncertain_fields: list[str]
    inference_source: Literal["gemini", "manual"]
    model: Optional[str] = None
    confirmed: bool
    vision_call: bool
    usage: Optional[dict[str, int]] = None
    compute_ms: float


class PickupStop(_Out):
    position: int
    token: RiderToken
    pickup_time: HHMM


class FareShare(_Out):
    position: int
    token: RiderToken
    share_fils: Fils


class FareComponent(_Out):
    label: str
    fils: Fils


class FareInfo(_Out):
    your_share_fils: Fils
    vehicle_total_fils: Fils
    shares: list[FareShare]
    your_breakdown: list[FareComponent]
    equal_split_fils: Optional[Fils] = None
    hypothetical_reference_fils: Optional[Fils] = None
    delta_vs_reference_fils: Optional[SignedFils] = None
    shuttle_ticket_fils_at_boarding: Fils = 0


class ShuttleLeg(_Out):
    walk_to_meet_min: int
    feeder_depart: HHMM
    hub_arrival: HHMM
    shuttle_id: str
    shuttle_depart: HHMM
    transfer_buffer_min: int


class PlanOption(_Out):
    plan_id: PlanId
    mode: PickupMode
    relaxed: Optional[str] = None
    relaxed_constraint: Optional[Literal["companions", "departure", "pickup_mode"]] = None
    utility: Optional[float] = None
    generalized_cost_j: Optional[float] = None
    leave_home: HHMM
    arrival: HHMM
    deadline: HHMM
    delta_minutes: int = 0
    pickup_order: list[RiderToken]
    pickups: list[PickupStop]
    vehicle_class: str
    vehicle_id: Optional[str] = None
    fare: FareInfo
    bookable: bool
    cap_status: Literal["within_cap", "CAP_EXCEEDED_REQUIRES_APPROVAL"]
    shuttle: Optional[ShuttleLeg] = None


class Rejection(_Out):
    subject: str
    code: RejectCode
    detail: str
    count: int = 1


class Audit(_Out):
    candidate_riders_considered: int
    groups_evaluated: int
    routes_evaluated: int
    rejections_by_code: dict[str, int]


class PlanResponse(_Out):
    session_id: SessionId
    plan_revision: int
    status: Literal["exact_match", "best_deal_proposed", "no_feasible_route", "no_accessible_route"]
    exact_match_found: bool
    options: list[PlanOption]
    unbookable_comparisons: list[PlanOption]
    rejected: list[Rejection]
    requires_approval: bool
    operator_assistance: bool
    reference_label: Optional[str] = None
    source: Source = "simulation"
    compute_ms: float
    audit: Audit


class RiderDelta(_Out):
    token: RiderToken
    old_fare_fils: Fils
    new_fare_fils: Fils
    delta_fils: SignedFils
    consented: bool


class Proposal(_Out):
    proposal_id: PlanId
    kind: Literal["smart_rescue", "class_shift", "emergency"]
    trigger: str
    trip_id: TripId
    plan_revision: int
    status: Literal["pending", "committed", "declined", "no_feasible_route", "no_accessible_route"]
    option: Optional[PlanOption] = None
    alternatives: list[PlanOption] = []
    rejected: list[Rejection] = []
    riders: list[RiderDelta] = []
    requires_approval: bool
    operator_assistance: bool = False


class LedgerEntry(_Out):
    entry_id: str
    trip_id: TripId
    plan_revision: int
    kind: Literal["debit", "refund"]
    amount_fils: Fils
    balance_after_fils: SignedFils


class ConfirmResponse(_Out):
    session_id: SessionId
    status: Literal["booked", "consent_recorded", "committed"]
    trip_id: TripId
    plan_id: PlanId
    plan_revision: int
    charged_fils: SignedFils
    wallet_balance_fils: SignedFils
    awaiting_consent_from: list[RiderToken]
    follow_up_proposals: list[PlanId] = []
    idempotent_replay: bool = False
    source: Source = "simulation"


class ShiftClassResponse(_Out):
    session_id: SessionId
    status: Literal["proposed", "no_next_class", "no_feasible_route", "release_requires_operator_policy"]
    vision_call: bool
    current_class: HHMM
    next_class: Optional[HHMM] = None
    proposal: Optional[Proposal] = None
    refund_fils: Fils = 0
    new_charge_fils: Fils = 0
    net_change_fils: SignedFils = 0
    free_release: bool = False
    cancel_only_option: Optional[dict[str, str | int]] = None
    affected_co_riders: list[RiderToken] = []
    plan_revision: int
    source: Source = "simulation"
    compute_ms: float


class EmergencyInsertion(_Out):
    trip_id: TripId
    pickup_time: HHMM
    arrival: HHMM
    base_share_fils: Fils
    fare_fils: Fils
    surge_premium_fils: Fils
    detour_cost_fils: Fils
    existing_riders: list[RiderDelta]


class EmergencyResponse(_Out):
    session_id: SessionId
    status: Literal["insertion_proposed", "standard_solo_jeeny", "no_feasible_route"]
    proposal_id: Optional[PlanId] = None
    insertion: Optional[EmergencyInsertion] = None
    fallback: Optional[dict[str, str | int | bool]] = None
    rejected: list[Rejection]
    requires_approval: bool
    dispatched: Literal[False] = False
    plan_revision: int
    source: Source = "simulation"
    compute_ms: float


class TripView(_Out):
    trip_id: TripId
    status: Literal["booked", "released", "cancelled", "en_route"]
    class_start: HHMM
    mode: PickupMode
    pickups: list[PickupStop]
    arrival: HHMM
    your_fare_fils: Optional[Fils] = None
    plan_revision: int


class StateResponse(_Out):
    session_id: SessionId
    sim_time: HHMM
    plan_revision: int
    primary_rider: RiderToken
    wallet_balance_fils: SignedFils
    ledger: list[LedgerEntry]
    trips: list[TripView]
    pending_proposals: list[Proposal]
    traffic_multiplier: str
    timetable_confirmed: bool
    source: Source = "simulation"


class EventResponse(_Out):
    session_id: SessionId
    event: str
    target: str
    sim_time: HHMM
    plan_revision: int
    proposals: list[Proposal]
    unaffected_trips: list[TripId]
    source: Source = "simulation"
    compute_ms: float
    audit: Audit


class SplitInviteResponse(_Out):
    invite_token: str
    trip_id: TripId
    invitee_token: RiderToken
    invitee_share_fils: Fils
    expires_at: HHMM
    source: Source = "simulation"


class ParcelQuoteResponse(_Out):
    trip_id: TripId
    corridor_km: str
    parcel_fee_fils: Fils
    insurance_fils: Fils
    total_fils: Fils
    driver_share_fils: Fils
    jeeny_share_fils: Fils
    shipment_created: Literal[False] = False
    source: Source = "simulation"


class VoiceUnderstandResponse(_Out):
    intent: Literal["plan", "late", "box", "wallet", "route", "timetable", "unknown"]
    origin: str
    destination: str
    time: str
    pool: Literal["female", "male", ""]
    reply: str
    action_taken: Literal["none"] = "none"
    inference_source: Literal["gemini"] = "gemini"
    model: str
    inference_ms: float


class VoiceIntentResponse(_Out):
    intent: Literal["plan_trip", "read_route", "accept_best_deal", "approve_rescue", "decline",
                    "shift_to_next_class", "emergency_ride", "repeat", "unknown"]
    confidence: float
    slots: dict[str, str]
    readback_ar: str
    readback_en: str
    requires_confirmation: bool
    action_taken: Literal["none"] = "none"
    plan_id: Optional[PlanId] = None
    plan_revision: int
    fare_fils: Optional[Fils] = None
    source: Source = "simulation"


class InsightsResponse(_Out):
    requests_by_hour: dict[str, int]
    requests_by_zone: dict[str, int]
    accessible_requests: int
    opted_in_riders: int
    shuttle_seats: dict[str, int]
    wav_available: int
    wav_total: int
    b2b_semester_pass_example: dict[str, int]
    prediction: Optional[dict[str, str | bool]] = None
    source: Source = "simulation"


class B2BSubsidy(_Out):
    trips: int
    share_fils: Fils
    gross_fils: Fils
    institution_fils: Fils
    student_fils: Fils

    @field_validator("student_fils")
    @classmethod
    def _sum(cls, v: int, info):  # noqa: ANN001
        d = info.data
        if d.get("institution_fils", 0) + v != d.get("gross_fils", -1):
            raise ValueError("subsidy split must conserve gross")
        return v
