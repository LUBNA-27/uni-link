"""Generates backend/fixtures/*.json — deterministic (seed 2026), synthetic, simulation-only."""
import json, random, pathlib
OUT = pathlib.Path("/home/claude/unilink/backend/fixtures")
SUN, MON = "2026-11-29", "2026-11-30"
rnd = random.Random(2026)

def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

meta = {"fixture_version": "unilink-backend-ref-2026.11.27-revE", "source": "simulation",
        "note": "Reference fixtures bundled with backend/. Set UNILINK_DATA_DIR to use data/ once schemas are aligned."}
dump("meta.json", meta)

dump("tariffs.json", {
    "source": "simulation", "BASE": 600, "FEE": 300, "KM_STD": 240, "KM_BIG": 300, "SHUTTLE": 400,
    "SURGE_EMG": "5/4", "PEAK_MULT": "5/4", "PEAK_START": "07:30", "PEAK_END": "08:30",
    "DWELL_MIN": 1, "DWELL_WHEELCHAIR_MIN": 3, "TARGET_SLACK_MIN": 5, "TRANSFER_BUFFER_MIN": 5,
    "DEPARTURE_RELAX_MIN": 10, "CLASS_WINDOW_MIN": 15, "FREE_RELEASE_MIN": 30, "EMERGENCY_MAX_PICKUP_MIN": 10,
    "BOX_BASE": 300, "BOX_KM": 30, "BOX_INS_BPS": 150, "BOX_INS_MIN": 150, "BOX_DRIVER_PCT": 60, "BOX_MAX_KG": 5,
    "B2B_AAU_SUBSIDY_PCT": 30, "UTILITY_W_FARE": "1/20", "UTILITY_W_MIN": "2",
    "J_W_T": "1/25", "J_W_W": "2/25", "J_W_N": "1/5"})

points = {
    "A": [32.5560, 35.8700], "B": [32.5480, 35.8880], "C": [32.5440, 35.8970], "D": [32.5400, 35.9060],
    "JUST_GATE": [32.4950, 35.9910], "P_irbid_east": [32.5530, 35.8760], "T_irbid": [32.5300, 35.9280],
    "X_TRP0002": [32.5523, 35.8775], "W": [32.0220, 35.8390], "AAU_GATE": [32.0430, 35.8610],
    "H_sweileh": [32.0300, 35.8450], "N1": [32.5650, 35.8500], "N2": [32.5700, 35.8450],
    "S1P": [32.0250, 35.8350], "S2P": [32.0200, 35.8420]}
dump("zones.json", {
    "source": "simulation",
    "points": {k: {"lat": v[0], "lng": v[1]} for k, v in points.items()},
    "zones": {
        "irbid_east": {"campus_ids": ["JUST"], "meet_point": "P_irbid_east", "walk_to_meet_min": 5, "hub": "T_irbid"},
        "irbid_nuzha": {"campus_ids": ["JUST"], "meet_point": "N2", "walk_to_meet_min": 6, "hub": "T_irbid"},
        "sweileh": {"campus_ids": ["AAU"], "meet_point": "S2P", "walk_to_meet_min": 7, "hub": "H_sweileh"}},
    "campuses": {
        "JUST": {"gate_point": "JUST_GATE", "step_free_dropoff": "verified"},
        "AAU": {"gate_point": "AAU_GATE", "step_free_dropoff": "verified"}}})

# km as decimal strings; peak = already traffic-adjusted peak minutes; off = off-peak minutes
legs = {
    "A>B": ["2", 6, 5], "B>C": ["1", 4, 4], "C>D": ["1", 2, 2], "B>D": ["2", 4, 3],
    "A>C": ["3", 10, 9], "A>D": ["4", 12, 10],
    "D>JUST_GATE": ["11", 18, 15], "C>JUST_GATE": ["12", 20, 16], "B>JUST_GATE": ["13", 24, 20],
    "A>JUST_GATE": ["14", 26, 22], "W>AAU_GATE": ["6", 17, 17],
    "P_irbid_east>T_irbid": ["3", 8, 7], "T_irbid>JUST_GATE": ["9.5", 15, 12],
    "S2P>H_sweileh": ["2", 6, 5]}
dump("hubs.json", {"source": "simulation", "legs": {k: {"km": v[0], "peak_min": v[1], "off_min": v[2]} for k, v in legs.items()}})

dump("vehicles.json", {"source": "simulation", "vehicles":
    [{"vehicle_id": f"SED-0{i}", "class": "sedan", "seats": 4, "wheelchair_slots": 0, "has_ramp": False,
      "ramp_verified": False, "available": True, "zone_ids": ["irbid_east", "irbid_nuzha", "sweileh"]} for i in range(1, 7)] +
    [{"vehicle_id": f"BIG-0{i}", "class": "big_car", "seats": 6, "wheelchair_slots": 0, "has_ramp": False,
      "ramp_verified": False, "available": True, "zone_ids": ["irbid_east", "irbid_nuzha", "sweileh"]} for i in (1, 2)] +
    [{"vehicle_id": "WAV-01", "class": "wav", "seats": 2, "wheelchair_slots": 1, "has_ramp": True,
      "ramp_verified": True, "available": True, "zone_ids": ["sweileh"]},
     {"vehicle_id": "WAV-02", "class": "wav", "seats": 2, "wheelchair_slots": 1, "has_ramp": True,
      "ramp_verified": True, "available": False, "zone_ids": ["sweileh"]}]})

dump("shuttles.json", {"source": "simulation", "shuttles": [
    {"shuttle_id": "S1", "campus_id": "JUST", "hub": "T_irbid", "depart": "07:55", "arrive": "08:13", "seats": 3, "access_verified": True},
    {"shuttle_id": "S2", "campus_id": "JUST", "hub": "T_irbid", "depart": "08:15", "arrive": "08:33", "seats": 30, "access_verified": True},
    {"shuttle_id": "AAU-SH1", "campus_id": "AAU", "hub": "H_sweileh", "depart": "08:20", "arrive": "08:40", "seats": 20, "access_verified": False}]})

dump("active_trips.json", {"source": "simulation", "trips": [{
    "trip_id": "TRP-0002", "service_date": MON, "campus_id": "JUST", "gender_pool": "female_only", "vehicle_id": "SED-05",
    "seats_offered": 3, "riders": [{"token": "R-6EM", "fare_fils": 1500}, {"token": "R-2EM", "fare_fils": 1260}],
    "pass_point": "X_TRP0002", "pass_eta": "08:01", "detour_km": "0.8", "remaining_km_after_pickup": "12",
    "remaining_min_after_pickup": 16, "baseline_arrival": "08:15"}]})

def rider(token, name, zone, campus, gender, sched, stop, desired=2, cap=2000, opt_in=True, wheelchair=False,
          big_car=False, wallet=10000, latest_pref=None, flexible_from=None, buffer=10):
    p = points[stop]
    _ = "".join(str(rnd.randint(0, 9)) for _ in range(8))   # keep RNG sequence identical; no phone is stored
    return {"token": token,
            "zone_id": zone, "campus_id": campus, "gender_pool": gender, "schedule": sched, "buffer_min": buffer,
            "stop_id": stop, "home_lat": round(p[0] + rnd.uniform(-0.0004, 0.0004), 6),
            "home_lng": round(p[1] + rnd.uniform(-0.0004, 0.0004), 6), "desired_companions": desired,
            "fare_cap_fils": cap, "opt_in": opt_in, "wheelchair": wheelchair, "big_car": big_car, "wallet_fils": wallet,
            "latest_preferred_arrival": latest_pref, "flexible_from": flexible_from}

riders = [
    rider("R-7K2", "Sara (synthetic)", "irbid_east", "JUST", "female_only", {SUN: "08:30", MON: "08:30"}, "A", desired=3, wallet=12000),
    rider("R-3QM", "Synthetic B", "irbid_east", "JUST", "female_only", {SUN: "08:30"}, "B"),
    rider("R-9TD", "Synthetic C", "irbid_east", "JUST", "female_only", {SUN: "08:30"}, "C"),
    rider("R-5LP", "Synthetic D", "irbid_east", "JUST", "female_only", {SUN: "08:30"}, "D", latest_pref="08:10", flexible_from="06:55"),
    rider("R-4HN", "Synthetic E", "irbid_east", "JUST", "female_only", {SUN: "11:30"}, "B"),
    rider("R-8PX", "Synthetic F", "irbid_east", "JUST", "female_only", {SUN: "11:30"}, "C"),
    rider("R-6EM", "Synthetic G", "irbid_east", "JUST", "female_only", {MON: "08:30"}, "B"),
    rider("R-2EM", "Synthetic H", "irbid_east", "JUST", "female_only", {MON: "08:30"}, "C"),
    rider("R-W01", "Zaid (synthetic)", "sweileh", "AAU", "male_only", {SUN: "09:00"}, "W", desired=0, cap=3000, wheelchair=True),
    # adversarial fillers in Sara's corridor: must never match her
    rider("R-M01", "Synthetic male", "irbid_east", "JUST", "male_only", {SUN: "08:30"}, "B"),
    rider("R-M02", "Synthetic male", "irbid_east", "JUST", "male_only", {SUN: "11:30"}, "C"),
    rider("R-OPT", "Synthetic opt-out", "irbid_east", "JUST", "female_only", {SUN: "08:30"}, "C", opt_in=False),
    rider("R-T10", "Synthetic 10:00", "irbid_east", "JUST", "female_only", {SUN: "10:00"}, "B"),
]
alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
used = {r["token"] for r in riders}
while len(riders) < 60:
    tok = "R-" + "".join(rnd.choice(alphabet) for _ in range(3))
    if tok in used:
        continue
    used.add(tok)
    zone = rnd.choice(["irbid_nuzha", "sweileh"])
    campus = "JUST" if zone == "irbid_nuzha" else "AAU"
    stop = rnd.choice(["N1", "N2"] if zone == "irbid_nuzha" else ["S1P", "S2P"])
    start = rnd.choice(["08:00", "08:30", "10:00", "11:30", "13:00"])
    riders.append(rider(tok, "Synthetic rider", zone, campus, rnd.choice(["female_only", "male_only"]), {SUN: start}, stop,
                        desired=rnd.randint(1, 3), wheelchair=(rnd.random() < 0.05)))
dump("riders.json", {"source": "simulation", "seed": 2026, "riders": riders})

dump("scenarios.json", {"source": "simulation", "scenarios": {
    "cancel": {"event": "rider_cancel", "target": "R-9TD", "sim_time": "06:55"},
    "traffic": {"event": "traffic", "target": "all", "sim_time": "07:00", "multiplier": "8/5"},
    "full": {"event": "shuttle_full", "target": "S1", "sim_time": "07:47"},
    "wav_out": {"event": "vehicle_unavailable", "target": "WAV-01", "sim_time": "07:00"}}})
print("ok", len(riders))
