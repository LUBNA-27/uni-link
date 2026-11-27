"""Whitelist-only voice intent classifier (Rev. E §12.2). Deterministic keyword rules, no LLM.

Guardrails: this module NEVER mutates state. Money-moving intents return a read-back of
backend-computed values with requires_confirmation=True and action_taken="none"; execution only
happens through /api/trips/confirm with the matching plan_revision. Gender pool and accessibility
cannot be changed by voice. Confidence < 0.80 asks again.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from .schemas import VoiceIntentResponse
from .state import Session
from .timeutil import to_hhmm

CONFIDENCE_MIN = 0.80
MONEY_INTENTS = {"accept_best_deal", "approve_rescue", "shift_to_next_class", "emergency_ride"}

_RULES: dict[str, tuple[str, ...]] = {
    "accept_best_deal": ("best deal", "first option", "accept the deal", "take option", "الخيار الأول",
                         "بختار الأول", "العرض الأول", "بوافق على العرض"),
    "approve_rescue": ("approve", "i agree", "agree to the change", "موافقة", "بوافق", "موافق على البديل", "تمام وافقت"),
    "decline": ("decline", "no thanks", "don't want", "reject", "مش موافق", "ما بدي", "رفض", "لا شكرا"),
    "shift_to_next_class": ("class was canceled", "class was cancelled", "class canceled", "class cancelled",
                            "next class", "المحاضرة التغت", "التغت المحاضرة", "المحاضرة الجاية"),
    "emergency_ride": ("emergency", "overslept", "i'm late", "urgent ride", "طوارئ", "مستعجل", "نمت", "تأخرت"),
    "read_route": ("read route", "read my route", "when is the pickup", "where is the captain", "pickup time",
                   "اقرأ المسار", "وين الكابتن", "امتى الكابتن", "إمتى بيجي"),
    "repeat": ("repeat", "say that again", "again please", "عيد", "كرر", "مرة ثانية"),
    "plan_trip": ("plan a trip", "plan my trip", "book a ride", "ride to campus", "بدي مشوار", "احجزلي",
                  "خطط رحلة", "بدي روح عالجامعة"),
}
_FORBIDDEN = ("gender", "male", "female", "wheelchair", "ramp", "accessib", "مختلط", "شباب", "بنات", "كرسي", "رامب")
_AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _norm(text: str) -> str:
    text = "".join(ch for ch in unicodedata.normalize("NFKC", text) if unicodedata.category(ch)[0] != "C")
    text = re.sub(r"[إأآ]", "ا", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def classify(transcript: str) -> tuple[str, float]:
    t = _norm(transcript)
    if any(w in t for w in _FORBIDDEN):
        return "unknown", 0.0
    hits = {intent: sum(1 for k in keys if _norm(k) in t) for intent, keys in _RULES.items()}
    hits = {k: v for k, v in hits.items() if v}
    if len(hits) != 1:
        return "unknown", 0.5 if hits else 0.0
    intent, n = next(iter(hits.items()))
    return intent, min(0.99, 0.85 + 0.05 * (n - 1))


def jod_en(fils: int) -> str:
    return f"JOD {fils // 1000}.{fils % 1000:03d}"


def jod_ar(fils: int) -> str:
    return f"{str(fils // 1000).translate(_AR_DIGITS)} دينار و{str(fils % 1000).translate(_AR_DIGITS)} فلس"


def _ar_time(hhmm: str) -> str:
    return hhmm.translate(_AR_DIGITS)


def respond(s: Session, transcript: str, locale: str) -> VoiceIntentResponse:
    intent, conf = classify(transcript)
    plan_id: Optional[str] = None
    fare: Optional[int] = None
    rev = s.revision
    if intent == "unknown" or conf < CONFIDENCE_MIN:
        if any(w in _norm(transcript) for w in _FORBIDDEN):
            ar = "ما بقدر أغيّر إعدادات الأمان أو الإتاحة بالصوت. استخدمي الإعدادات على الشاشة."
            en = "Safety and accessibility settings cannot be changed by voice. Please use the on-screen settings."
        else:
            ar, en = "ما فهمت عليكِ، ممكن تعيدي؟", "Sorry, I didn't catch that. Could you say it again?"
        return VoiceIntentResponse(intent="unknown", confidence=conf, slots={}, readback_ar=ar, readback_en=en,
                                   requires_confirmation=False, plan_revision=rev)
    pending = [p for p in s.pending.values() if p.revision == s.revision and p.status == "pending"]
    ar = en = ""
    if intent == "accept_best_deal":
        q = next((p for p in sorted(pending, key=lambda p: p.plan_id) if p.kind == "quote" and p.option is not None), None)
        if q:
            plan_id, fare = q.plan_id, q.option.fare.your_share_fils
            ar = f"الخيار {plan_id}: بتوصلي {_ar_time(q.option.arrival)} بـ {jod_ar(fare)}. أكدي على الشاشة."
            en = f"Option {plan_id}: arrive {q.option.arrival} for {jod_en(fare)}. Confirm on screen."
    elif intent == "approve_rescue":
        q = next((p for p in pending if p.kind == "smart_rescue" and p.option is not None and s.primary in p.affected), None)
        if q:
            plan_id, fare = q.plan_id, q.new_fares[s.primary]
            d = fare - q.old_fares.get(s.primary, 0)
            ar = f"البديل: بتوصلي {_ar_time(q.option.arrival)}، الفرق {jod_ar(max(d, 0))}. أكدي على الشاشة."
            en = f"Rescue plan: arrive {q.option.arrival}, change {jod_en(max(d, 0))}. Confirm on screen."
    elif intent == "shift_to_next_class":
        ar, en = "رح أجهزلك خيار للمحاضرة الجاية. أكدي على الشاشة.", "I'll prepare an option for your next class. Confirm on screen."
    elif intent == "emergency_ride":
        ar, en = "رح أدورلك مقعد بسيارة ماشية قريبة. أكدي على الشاشة.", "I'll look for a seat on a nearby trip. Confirm on screen."
    elif intent == "read_route":
        trip = next((t for t in s.trips.values() if t.status == "booked" and s.primary in t.members), None)
        if trip:
            pk = to_hhmm(trip.pickups[s.primary])
            ar = f"الكابتن بيجيكي {_ar_time(pk)} وبتوصلي {_ar_time(to_hhmm(trip.arrival))} حسب المحاكاة."
            en = f"Pickup {pk}, arrival {to_hhmm(trip.arrival)} (simulation)."
    elif intent == "decline":
        ar, en = "تمام، ما غيرنا إشي.", "Okay, nothing was changed."
    elif intent == "repeat":
        ar, en = "رح أعيد آخر رسالة على الشاشة.", "Repeating the last message on screen."
    elif intent == "plan_trip":
        ar, en = "افتحي إعداد الرحلة واختاري المحاضرة.", "Open Trip setup and choose your class."
    if not ar:
        ar, en = "ما في خيار جاهز هلأ.", "There is no option ready right now."
    return VoiceIntentResponse(intent=intent, confidence=round(conf, 2), slots={}, readback_ar=ar, readback_en=en,
                               requires_confirmation=intent in MONEY_INTENTS, plan_id=plan_id, plan_revision=rev,
                               fare_fils=fare)
