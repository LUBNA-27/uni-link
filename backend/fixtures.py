"""Read-only fixture loader.

Default: the reference fixtures bundled in backend/fixtures/. Set UNILINK_DATA_DIR to point at the
team's data/ folder once its schema matches. Fixtures are loaded once and never mutated; every
session works on deep copies.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any

_BUNDLED = Path(__file__).resolve().parent / "fixtures"
_REQUIRED = ("meta.json", "tariffs.json", "zones.json", "hubs.json", "vehicles.json", "shuttles.json",
             "active_trips.json", "riders.json", "scenarios.json")


class FixtureError(RuntimeError):
    pass


@dataclass(frozen=True)
class Leg:
    km: Fraction
    peak_min: int
    off_min: int


@dataclass(frozen=True)
class Fixtures:
    version: str
    data_dir: str
    tariffs: dict[str, Any]
    points: dict[str, tuple[float, float]]
    zones: dict[str, dict[str, Any]]
    campuses: dict[str, dict[str, Any]]
    legs: dict[tuple[str, str], Leg]
    vehicles: tuple[dict[str, Any], ...]
    shuttles: tuple[dict[str, Any], ...]
    active_trips: tuple[dict[str, Any], ...]
    riders: dict[str, dict[str, Any]]
    scenarios: dict[str, dict[str, Any]]
    frac: dict[str, Fraction] = field(default_factory=dict)

    def leg(self, a: str, b: str) -> Leg | None:
        return self.legs.get((a, b))

    def rider(self, token: str) -> dict[str, Any] | None:
        return self.riders.get(token)


def _load(path: Path, name: str) -> dict[str, Any]:
    try:
        with (path / name).open(encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureError(f"cannot load fixture {name}") from exc


@lru_cache(maxsize=1)
def get_fixtures() -> Fixtures:
    data_dir = Path(os.environ.get("UNILINK_DATA_DIR") or _BUNDLED).resolve()
    missing = [n for n in _REQUIRED if not (data_dir / n).is_file()]
    if missing:
        raise FixtureError(f"fixture files missing: {', '.join(missing)}")
    raw = {n: _load(data_dir, n) for n in _REQUIRED}
    tariffs = raw["tariffs.json"]
    # numeric strings ("5/4", "2") are exact rationals; "HH:MM" strings stay times
    frac = {k: Fraction(v) for k, v in tariffs.items() if isinstance(v, str) and k != "source" and ":" not in v}
    zones = raw["zones.json"]
    legs = {}
    for key, leg in raw["hubs.json"]["legs"].items():
        a, b = key.split(">")
        legs[(a, b)] = Leg(Fraction(str(leg["km"])), int(leg["peak_min"]), int(leg["off_min"]))
    riders = {r["token"]: r for r in raw["riders.json"]["riders"]}
    if len(riders) != len(raw["riders.json"]["riders"]):
        raise FixtureError("duplicate rider tokens")
    return Fixtures(
        version=raw["meta.json"]["fixture_version"],
        data_dir="bundled" if data_dir == _BUNDLED.resolve() else "UNILINK_DATA_DIR",
        tariffs=tariffs,
        points={k: (float(v["lat"]), float(v["lng"])) for k, v in zones["points"].items()},
        zones=zones["zones"], campuses=zones["campuses"], legs=legs,
        vehicles=tuple(raw["vehicles.json"]["vehicles"]), shuttles=tuple(raw["shuttles.json"]["shuttles"]),
        active_trips=tuple(raw["active_trips.json"]["trips"]), riders=riders,
        scenarios=raw["scenarios.json"]["scenarios"], frac=frac)
