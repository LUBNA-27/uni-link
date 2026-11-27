"""Replaceable traffic adapter (simulation).

Fixture legs carry off-peak minutes and already-traffic-adjusted peak minutes (Rev. E §06: "do not
multiply again"). In the peak window 07:30–08:30 the adapter returns the fixture peak minutes; off
peak it returns off-peak minutes. A simulation `traffic` event installs an override multiplier
applied ONCE to off-peak minutes and rounded up. Swap this class for a live provider later.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

from .fixtures import Fixtures, Leg
from .timeutil import to_min


@dataclass(frozen=True)
class TrafficOverride:
    from_min: int
    multiplier: Fraction


class TrafficAdapter:
    source = "simulation"

    def __init__(self, fx: Fixtures, override: Optional[TrafficOverride] = None) -> None:
        self.peak_start = to_min(fx.tariffs["PEAK_START"])
        self.peak_end = to_min(fx.tariffs["PEAK_END"])
        self.peak_mult = fx.frac["PEAK_MULT"]
        self.override = override

    def multiplier(self, depart_min: int) -> Fraction:
        if self.override and depart_min >= self.override.from_min:
            return self.override.multiplier
        if self.peak_start <= depart_min < self.peak_end:
            return self.peak_mult
        return Fraction(1)

    def duration(self, leg: Leg, depart_min: int) -> int:
        if self.override and depart_min >= self.override.from_min:
            return math.ceil(leg.off_min * self.override.multiplier)
        if self.peak_start <= depart_min < self.peak_end:
            return leg.peak_min
        return leg.off_min
