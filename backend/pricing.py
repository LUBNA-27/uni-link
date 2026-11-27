"""Integer-fils pricing (Rev. E §11.3). No floats touch money: exact Fractions until the single
largest-remainder allocation step, then a hard conservation check.

share_i = (BASE + FEE)/N + Σ_{legs where i is onboard} km_leg * rate / onboard_count
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence


class PricingInvariantError(RuntimeError):
    """Raised (never stripped like `assert`) when shares do not conserve the vehicle total."""


def allocate_largest_remainder(exact: Sequence[Fraction], total: int) -> list[int]:
    """Floor every exact share, hand leftover fils to the largest fractional remainders.
    Ties go to the earliest index (= earliest pickup)."""
    if any(x < 0 for x in exact):
        raise PricingInvariantError("negative share")
    if sum(exact) != total:
        raise PricingInvariantError(f"exact shares {sum(exact)} != total {total}")
    floors = [math.floor(x) for x in exact]
    left = total - sum(floors)
    order = sorted(range(len(exact)), key=lambda i: (-(exact[i] - floors[i]), i))
    for i in order[:left]:
        floors[i] += 1
    check_conservation(floors, total)
    return floors


def check_conservation(shares: Sequence[int], total: int) -> None:
    if sum(shares) != total or any(not isinstance(s, int) for s in shares):
        raise PricingInvariantError(f"sum(shares)={sum(shares)} != vehicle_total={total}")


def equal_split(total: int, n: int) -> list[int]:
    return allocate_largest_remainder([Fraction(total, n)] * n, total)


@dataclass(frozen=True)
class SplitResult:
    shares: list[int]                      # by pickup position
    vehicle_total: int
    fixed_each: list[int]                  # allocated fixed component per rider (display)
    distance_each: list[int]               # share - fixed (display)


def vehicle_total(km_total: Fraction, rate: int, base: int, fee: int) -> int:
    total = Fraction(base + fee) + km_total * rate
    if total.denominator != 1:
        # fractional fils can only arise from fractional km; round half up once, at vehicle level
        return math.floor(total + Fraction(1, 2))
    return int(total)


def leg_weighted_split(leg_km: Sequence[Fraction], rate: int, base: int, fee: int) -> SplitResult:
    """Door-to-door: rider i (pickup position i) is onboard for legs i..n-1 (leg i ends at the next
    pickup or campus). len(leg_km) == number of riders."""
    n = len(leg_km)
    if n == 0:
        raise ValueError("no riders")
    fixed = Fraction(base + fee, n)
    exact: list[Fraction] = []
    for i in range(n):
        dist = sum((leg_km[j] * rate / (j + 1) for j in range(i, n)), Fraction(0))
        exact.append(fixed + dist)
    total = vehicle_total(sum(leg_km, Fraction(0)), rate, base, fee)
    if sum(exact) != total:  # only when total was rounded: rescale fractional excess deterministically
        exact = [x * total / sum(exact) for x in exact]
    shares = allocate_largest_remainder(exact, total)
    fixed_alloc = allocate_largest_remainder([fixed] * n, base + fee)
    return SplitResult(shares, total, fixed_alloc, [s - f for s, f in zip(shares, fixed_alloc)])


def shared_segment_split(km: Fraction, rate: int, n: int, include_fixed: bool, base: int, fee: int) -> SplitResult:
    """All n riders onboard for the whole segment (feeder P→T, or extension T→campus)."""
    fixed = Fraction(base + fee) if include_fixed else Fraction(0)
    total_exact = fixed + km * rate
    total = math.floor(total_exact + Fraction(1, 2)) if total_exact.denominator != 1 else int(total_exact)
    shares = allocate_largest_remainder([Fraction(total, n)] * n, total)
    fixed_alloc = allocate_largest_remainder([fixed / n] * n, int(fixed)) if include_fixed else [0] * n
    return SplitResult(shares, total, fixed_alloc, [s - f for s, f in zip(shares, fixed_alloc)])


def solo_fare(km: Fraction, rate: int, base: int, fee: int) -> int:
    return vehicle_total(km, rate, base, fee)


def apply_multiplier(amount: int, multiplier: Fraction) -> int:
    """Round half up once; used for the emergency surge on the NEWCOMER's share only."""
    return math.floor(amount * multiplier + Fraction(1, 2))


def emergency_newcomer_share(base_share: int, surge: Fraction) -> tuple[int, int]:
    fare = apply_multiplier(base_share, surge)
    return fare, fare - base_share


def detour_cost(detour_km: Fraction, rate: int) -> int:
    return math.ceil(detour_km * rate)


def rescue_total(incurred: int, incremental: int) -> int:
    """Smart Rescue accounting: never re-charge base/fee for an extended vehicle."""
    return incurred + incremental


@dataclass(frozen=True)
class ParcelQuote:
    parcel_fee: int
    insurance: int
    total: int
    driver: int
    jeeny: int


def parcel_quote(km: Fraction, declared_fils: int, box_base: int, box_km: int, ins_bps: int, ins_min: int,
                 driver_pct: int) -> ParcelQuote:
    fee = math.ceil(box_base + box_km * km)
    insurance = max(ins_min, math.ceil(Fraction(declared_fils * ins_bps, 10_000)))
    driver = fee * driver_pct // 100
    jeeny = fee - driver                     # 60/40 split of the parcel fee only; insurance passes through
    return ParcelQuote(fee, insurance, fee + insurance, driver, jeeny)


def b2b_semester_pass(trips: int, share_fils: int, subsidy_pct: int) -> dict[str, int]:
    """B2B institutional subsidy — strictly separate from passenger fare computation."""
    gross = trips * share_fils
    institution = gross * subsidy_pct // 100
    return {"trips": trips, "share_fils": share_fils, "gross_fils": gross,
            "institution_fils": institution, "student_fils": gross - institution}
