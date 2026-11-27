"""UniLink 2.0 FastAPI app — frozen endpoints (Rev. E §10), per-session state, uniform errors,
single-origin static hosting of frontend/dist on 0.0.0.0:$PORT (Replit).

Run:  uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
"""
from __future__ import annotations

import logging
import os
import re
import secrets
from collections import Counter
from datetime import date
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

from typing import Optional

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import contract as C
from . import pricing, vision, voice, wire
from .errors import ApiError
from .fixtures import get_fixtures
from .predict import suggest_tomorrow
from .schemas import (HealthResponse, InsightsResponse, ParcelQuoteRequest, ParcelQuoteResponse, SplitInviteRequest,
                      SplitInviteResponse, VoiceIntentRequest, VoiceIntentResponse)
from .state import Session, SessionStore
from .timeutil import to_hhmm

log = logging.getLogger("unilink")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
FIXTURES = get_fixtures()
STORE = SessionStore(FIXTURES)

app = FastAPI(title="UniLink 2.0 API (simulation)", version="rev-e",
              docs_url="/docs" if os.environ.get("UNILINK_DOCS", "1") == "1" else None, redoc_url=None)

_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
            if o.strip() and o.strip() != "*"]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.middleware("http")
async def security_headers(request: Request, call_next: Callable):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


def _err(status: int, code: str, message: str, current_revision: Optional[int] = None) -> JSONResponse:
    # frontend parser reads top-level {code, message, current_revision}; nested copy kept for older clients
    body: dict[str, Any] = {"code": code, "message": message}
    if current_revision is not None:
        body["current_revision"] = current_revision
    body["error"] = {"code": code, "message": message}
    return JSONResponse(status_code=status, content=body)


@app.exception_handler(ApiError)
async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
    return _err(exc.status, exc.code, exc.message, exc.current_revision)


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # report field locations only; never echo submitted values back
    locs = sorted({".".join(str(p) for p in e.get("loc", ()) if p != "body") for e in exc.errors()})
    return _err(422, "VALIDATION_ERROR", "invalid request fields: " + ", ".join(locs)[:300])


@app.exception_handler(StarletteHTTPException)
async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _err(exc.status_code, "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR", "request failed")


@app.exception_handler(Exception)
async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled error: %s", type(exc).__name__)
    return _err(500, "INTERNAL_ERROR", "unexpected server error")


def _session(session_id: str) -> Session:
    if not SESSION_RE.match(session_id or ""):
        raise ApiError(422, "INVALID_SESSION", "session_id must be 1-64 characters [A-Za-z0-9_-]")
    return STORE.get(session_id)


def _locked(session_id: str, fn: Callable[[Session], Any]) -> Any:
    s = _session(session_id)
    with s.lock:
        return fn(s)


# ============================================================================ endpoints
@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", fixture_version=FIXTURES.version, fixture_source=FIXTURES.data_dir,
                          gemini_ready=vision.gemini_ready())


@app.post("/api/timetable/parse", response_model=C.TimetableResponse, response_model_exclude_none=True)
async def timetable_parse(session_id: str = Form(...), image: Optional[UploadFile] = File(None),
                          file: Optional[UploadFile] = File(None)) -> C.TimetableResponse:
    s = _session(session_id)
    upload = image or file                    # frontend sends "image"; "file" kept for curl/tests
    if upload is None:
        raise ApiError(422, "VALIDATION_ERROR", "invalid request fields: image")
    data = await upload.read(vision.MAX_BYTES + 1)
    await upload.close()
    mime = vision.sniff_image(data, upload.content_type)
    classes, uncertain, usage, ms, model = vision.parse_image(data, mime)   # real Gemini call only
    del data                                   # no raw image retention
    with s.lock:
        return wire.parse_response(s, classes, uncertain, usage, ms, model)


@app.post("/api/timetable/manual", response_model=C.TimetableResponse, response_model_exclude_none=True)
def timetable_manual(req: C.TimetableRequest) -> C.TimetableResponse:
    return _locked(req.session_id, lambda s: wire.manual(s, req))


@app.post("/api/timetable/confirm", response_model=C.TimetableConfirmResponse)
def timetable_confirm(req: C.TimetableRequest) -> C.TimetableConfirmResponse:
    return _locked(req.session_id, lambda s: wire.confirm_timetable(s, req))


@app.post("/api/plan", response_model=C.PlanResponse, response_model_exclude_none=True)
def plan(req: C.PlanRequest) -> C.PlanResponse:
    return _locked(req.session_id, lambda s: wire.plan(s, req))


@app.post("/api/trips/confirm", response_model=C.ConfirmResponse, response_model_exclude_none=True)
def trips_confirm(req: C.ConfirmRequest) -> C.ConfirmResponse:
    return _locked(req.session_id, lambda s: wire.confirm(s, req))


@app.post("/api/trips/shift-class", response_model=C.ShiftResponse, response_model_exclude_none=True)
def trips_shift_class(req: C.ShiftRequest) -> C.ShiftResponse:
    return _locked(req.session_id, lambda s: wire.shift(s, req))


@app.post("/api/trips/emergency", response_model=C.EmergencyResponse, response_model_exclude_none=True)
def trips_emergency(req: C.EmergencyRequest) -> C.EmergencyResponse:
    return _locked(req.session_id, lambda s: wire.emergency(s, req))


@app.post("/api/trips/split-invite", response_model=SplitInviteResponse)
def trips_split_invite(req: SplitInviteRequest) -> SplitInviteResponse:
    def run(s: Session) -> SplitInviteResponse:
        trip = s.trips.get(req.trip_id)
        if trip is None or trip.status not in ("booked", "en_route"):
            raise ApiError(404, "TRIP_NOT_FOUND", "unknown trip")
        if req.rider_token not in trip.members or req.invitee_token not in trip.members \
                or req.rider_token == req.invitee_token:
            raise ApiError(403, "NOT_AUTHORIZED", "invitee must be another rider on this trip")
        expires = min(s.sim_min + 120, 23 * 60 + 59)
        return SplitInviteResponse(invite_token=secrets.token_urlsafe(16), trip_id=trip.trip_id,
                                   invitee_token=req.invitee_token, invitee_share_fils=trip.fares[req.invitee_token],
                                   expires_at=to_hhmm(expires))
    return _locked(req.session_id, run)


@app.post("/api/parcels/quote", response_model=ParcelQuoteResponse)
def parcels_quote(req: ParcelQuoteRequest) -> ParcelQuoteResponse:
    def run(s: Session) -> ParcelQuoteResponse:
        trip = s.trips.get(req.trip_id)
        if trip is None or trip.status != "booked":
            raise ApiError(404, "TRIP_NOT_FOUND", "unknown trip")
        if any(s.fx.riders[t].get("wheelchair") for t in trip.members) or trip.vehicle_class == "wav" \
                or (trip.prefs.get("accessibility") or {}).get("wheelchair"):
            raise ApiError(409, "PARCEL_NOT_ALLOWED", "Ride & Box is never offered on wheelchair trips")
        t = s.fx.tariffs
        if req.weight_g > int(t["BOX_MAX_KG"]) * 1000:
            raise ApiError(422, "PARCEL_TOO_HEAVY", "sealed items up to 5 kg only")
        km = sum(trip.leg_km, Fraction(0))
        q = pricing.parcel_quote(km, req.declared_value_fils, int(t["BOX_BASE"]), int(t["BOX_KM"]),
                                 int(t["BOX_INS_BPS"]), int(t["BOX_INS_MIN"]), int(t["BOX_DRIVER_PCT"]))
        km_s = str(km.numerator) if km.denominator == 1 else f"{float(km):.1f}"
        return ParcelQuoteResponse(trip_id=trip.trip_id, corridor_km=km_s, parcel_fee_fils=q.parcel_fee,
                                   insurance_fils=q.insurance, total_fils=q.total, driver_share_fils=q.driver,
                                   jeeny_share_fils=q.jeeny)
    return _locked(req.session_id, run)


@app.get("/api/simulation/state", response_model=C.SimState, response_model_exclude_none=True)
def simulation_state(session_id: str = Query(...)) -> C.SimState:
    return _locked(session_id, wire.state)


@app.post("/api/simulation/event", response_model=C.SimState, response_model_exclude_none=True)
def simulation_event(req: C.SimEventRequest) -> C.SimState:
    return _locked(req.session_id, lambda s: wire.event(s, req))


@app.post("/api/voice/intent", response_model=VoiceIntentResponse)
def voice_intent(req: VoiceIntentRequest) -> VoiceIntentResponse:
    return _locked(req.session_id, lambda s: voice.respond(s, req.transcript, req.locale))


@app.get("/api/insights", response_model=InsightsResponse)
def insights(session_id: str = Query(...), service_date: date = Query(date(2026, 11, 29))) -> InsightsResponse:
    def run(s: Session) -> InsightsResponse:
        fx = s.fx
        day = service_date.isoformat()
        by_hour: Counter = Counter()
        by_zone: Counter = Counter()
        accessible = opted = 0
        for r in fx.riders.values():
            start = r["schedule"].get(day)
            if start is None:
                continue
            by_hour[start[:2] + ":00"] += 1
            by_zone[r["zone_id"]] += 1
            accessible += bool(r.get("wheelchair"))
            opted += bool(r.get("opt_in"))
        wavs = [v for v in fx.vehicles if v["class"] == "wav"]
        wav_ok = sum(1 for v in wavs if v["available"] and v["vehicle_id"] not in s.vehicles_out)
        share = next((t.fares.get(s.primary) for t in s.trips.values() if t.status == "booked" and s.primary in t.fares), None)
        example = pricing.b2b_semester_pass(40, share or 1860, int(fx.tariffs["B2B_AAU_SUBSIDY_PCT"]))
        return InsightsResponse(requests_by_hour=dict(sorted(by_hour.items())), requests_by_zone=dict(sorted(by_zone.items())),
                                accessible_requests=accessible, opted_in_riders=opted,
                                shuttle_seats=dict(sorted(s.shuttle_seats.items())), wav_available=wav_ok,
                                wav_total=len(wavs), b2b_semester_pass_example=example,
                                prediction=suggest_tomorrow(s.timetable, service_date))
    return _locked(session_id, run)


# ============================================================================ static frontend (same origin)
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
