"""The planner is not replaying the golden scenario: changing class time, fare cap, companion count,
preferred pickup and vehicle availability produces different, hand-derivable results, and the hard
invariants hold across a grid of 300+ request combinations. Expected numbers below are derived by hand
from fixture geometry and tariff (BASE 600, FEE 300, 240/km sedan, 300/km big car, shuttle 400)."""
from __future__ import annotations

import itertools

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.fixtures import get_fixtures
from backend.tests.test_contract import trip_tsx_plan

FX = get_fixtures()
_n = itertools.count()


@pytest.fixture(scope="module")
def c():
    main.STORE.clear()
    with TestClient(main.app) as client:
        yield client


def plan(c, pre=None, **kw):
    s = f"var{next(_n)}"
    if pre:
        for v in pre:
            c.post("/api/simulation/event", json={"session_id": s, "event": "vehicle_unavailable", "target": v,
                                                   "sim_time": "06:10"})
    r = c.post("/api/plan", json=trip_tsx_plan(s, **kw))
    assert r.status_code == 200, r.text
    return r.json()


def top(r):
    o = r["options"][0]
    return o["plan_id"], o["fare"]["your_share_fils"], o["leave_home"], o["arrival"], len(o["pickup_order"])


# ---------------------------------------------------------------- companion count
def test_companions_2_is_an_exact_match(c):
    r = plan(c, companions=2)
    assert r["status"] == "exact_match" and top(r) == ("M1", 1860, "07:44", "08:17", 3)


def test_companions_1_pair_is_over_cap_so_shuttle_relaxation_wins(c):
    # door pair A+B = 450 + 480 + 13*240/2 = 2490 > cap 2000; shuttle = (900 + 3*240)/2 + 400 = 1210
    r = plan(c, companions=1)
    o = r["options"][0]
    assert r["status"] == "best_deal_proposed" and o["relaxed"] == "pickup mode → main_road_shuttle"
    assert o["fare"]["your_share_fils"] == 1210 and len(o["pickup_order"]) == 2


def test_companions_0_solo_depends_on_cap(c):
    assert plan(c, companions=0)["status"] == "no_feasible_route"              # solo 4260 > 2000
    r = plan(c, companions=0, cap=5000)                                          # 900 + 14*240 = 4260
    assert r["status"] == "exact_match" and top(r) == ("M1", 4260, "07:44", "08:11", 1)   # 07:44+1+26


# ---------------------------------------------------------------- fare cap
@pytest.mark.parametrize("cap,expected", [
    (1000, []), (1500, []), (1564, []), (1565, [1565]), (1859, [1565]), (1860, [1860, 1565]), (5000, [1860, 1565])])
def test_fare_cap_boundaries(c, cap, expected):
    r = plan(c, cap=cap)
    assert [o["fare"]["your_share_fils"] for o in r["options"]] == expected
    assert r["status"] == ("best_deal_proposed" if expected else "no_feasible_route")


# ---------------------------------------------------------------- class time and preferred pickup
def test_earlier_preferred_pickup_shifts_every_stop(c):
    r = plan(c, companions=2, pickup="07:40")
    o = r["options"][0]
    assert r["status"] == "exact_match" and [p["time"] for p in o["pickups"]] == ["07:40", "07:47", "07:52"]
    assert o["arrival"] == "08:13"


def test_late_preferred_pickup_is_not_exact_and_relaxes_one_thing(c):
    r = plan(c, companions=2, pickup="07:54")          # 07:54 → arrival 08:27 > deadline 08:20
    assert r["status"] == "best_deal_proposed"
    labels = [o["relaxed"] for o in r["options"]]
    assert labels == ["pickup mode → main_road_shuttle", "departure −10 min"]
    assert r["options"][1]["leave_home"] == "07:44" and r["options"][1]["arrival"] == "08:17"


def test_11_30_class_uses_a_different_pool(c):
    r = plan(c, class_start="11:30", pickup="10:47", companions=2)
    o = r["options"][0]
    assert r["status"] == "exact_match" and o["pickup_order"] == ["R-7K2", "R-4HN", "R-8PX"]
    assert o["arrival"] == "11:15" and o["deadline"] == "11:20"


@pytest.mark.parametrize("cls", ["08:00", "09:00"])
def test_no_compatible_class_window_gives_honest_no_option(c, cls):
    r = plan(c, class_start=cls)
    assert r["status"] == "no_feasible_route" and r["options"] == [] and r["reason"]["code"] == "NO_FEASIBLE_ROUTE"


# ---------------------------------------------------------------- vehicle availability
SEDANS = [f"SED-0{i}" for i in range(1, 7)]


def test_all_sedans_out_switches_to_big_car_rates(c):
    # door with big car: A = 300 + 2*300 + 1*300/2 + 12*300/3 = 2250 > cap; shuttle = (900 + 3*300)/3 + 400 = 1000
    r = plan(c, pre=SEDANS, companions=2)
    o = r["options"][0]
    assert o["vehicle"]["kind"] == "big_car" and o["fare"]["your_share_fils"] == 1000
    big = plan(c, pre=SEDANS, companions=2, cap=5000)
    assert top(big)[1] == 2250 and big["options"][0]["vehicle"]["kind"] == "big_car"
    assert sum(x["share_fils"] for x in big["options"][0]["fare"]["shares"]) == 900 + 15 * 300


def test_no_vehicles_means_no_option(c):
    r = plan(c, pre=SEDANS + ["BIG-01", "BIG-02"], companions=2)
    assert r["status"] == "no_feasible_route" and r["options"] == []


def test_big_car_requirement_is_never_dropped(c):
    r = plan(c, companions=2, big_car=True)
    assert r["options"] and all(o["vehicle"]["kind"] == "big_car" for o in r["options"])


# ---------------------------------------------------------------- invariants over a grid
GRID = list(itertools.product(["08:00", "08:30", "08:45", "09:00", "11:30"], [0, 1, 2, 3],
                              [1500, 2000, 5000], ["07:30", "07:44", "07:54", "10:47"], [False, True]))


def test_hard_invariants_hold_across_grid(c):
    seen = set()
    for cls, comp, cap, pk, big in GRID:
        r = plan(c, class_start=cls, companions=comp, cap=cap, pickup=pk, big_car=big)
        deadline = f"{int(cls[:2]) * 60 + int(cls[3:]) - 10:04d}"
        dl = f"{int(deadline) // 60:02d}:{int(deadline) % 60:02d}"
        for o in r["options"]:
            shares = [x["share_fils"] for x in o["fare"]["shares"]]
            seen.add((o["fare"]["your_share_fils"], o["arrival"], len(o["pickup_order"])))
            assert sum(shares) == o["fare"]["vehicle_total_fils"] or o["vehicle"]["label"].startswith("Feeder")
            assert o["fare"]["your_share_fils"] <= cap                         # cap never relaxed
            assert o["arrival"] <= dl and o["deadline"] == dl                   # deadline never relaxed
            assert len(o["pickup_order"]) <= min(4, comp + 1)                   # capacity + never more riders
            assert all(FX.riders[t]["gender_pool"] == "female_only" for t in o["pickup_order"])
            assert not big or o["vehicle"]["kind"] == "big_car"
            times = [p["time"] for p in o["pickups"]]
            assert times == sorted(times)
            if o["vehicle"]["label"].startswith("Feeder"):                     # walk to meet point first
                assert o["leave_home"] < times[0]
            else:
                assert o["leave_home"] == times[0]
            if r["status"] == "best_deal_proposed":
                assert o["relaxed"] and o["relaxed"].split()[0] in ("companions", "departure", "pickup")
    assert len(GRID) >= 240 and len(seen) >= 8, f"only {len(seen)} distinct outcomes"
