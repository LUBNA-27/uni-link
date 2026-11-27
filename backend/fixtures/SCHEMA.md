# Fixture schema (for Rawan) — SYNTHETIC, simulation only

These files are generated deterministically (seed 2026). Every value is fictional. `ramp_verified`, `access_verified` and `step_free_dropoff` mean "verified **in this simulated fixture**". They are not real-world accessibility verification, and the API never presents them that way. To use `data/` instead of these files, keep the same field names and set `UNILINK_DATA_DIR=data`.

| File | Shape | Notes |
|---|---|---|
| `meta.json` | `{fixture_version, source, note}` | version shown in `/api/health` |
| `tariffs.json` | `BASE 600, FEE 300, KM_STD 240, KM_BIG 300, SHUTTLE 400` (fils); `SURGE_EMG "5/4"`, `PEAK_MULT "5/4"`, `PEAK_START/END "07:30"/"08:30"`; `DWELL_MIN 1`, `DWELL_WHEELCHAIR_MIN 3`, `TARGET_SLACK_MIN 5`, `TRANSFER_BUFFER_MIN 5`, `DEPARTURE_RELAX_MIN 10`, `CLASS_WINDOW_MIN 15`; utility/J weights as rational strings | rationals are strings so money math stays exact |
| `zones.json` | `points{id:{lat,lng}}` (server-only), `zones{id:{campus_ids, meet_point, walk_to_meet_min, hub}}`, `campuses{id:{gate_point, step_free_dropoff}}` | coordinates never leave the server |
| `hubs.json` | `legs{"A>B":{km, peak_min, off_min}}` | `km` decimal string; `peak_min` is already traffic-adjusted (07:30–08:30) and is not multiplied again |
| `vehicles.json` | `{vehicle_id, class: sedan\|big_car\|wav, seats, wheelchair_slots, has_ramp, ramp_verified, available, zone_ids[]}` | sedan 4 seats; WAV 2 seats + 1 chair |
| `shuttles.json` | `{shuttle_id, campus_id, hub, depart, arrive, seats, access_verified}` | S1 has 3 seats |
| `active_trips.json` | `{trip_id, service_date, campus_id, gender_pool, vehicle_id, seats_offered, riders[{token, fare_fils}], pass_point, pass_eta, detour_km, remaining_km_after_pickup, remaining_min_after_pickup}` | Emergency only |
| `riders.json` | `{token, display_name, phone, zone_id, campus_id, gender_pool, schedule{date:HH:MM}, buffer_min, stop_id, home_lat, home_lng, desired_companions, fare_cap_fils, opt_in, wheelchair, big_car, wallet_fils, latest_preferred_arrival, flexible_from}` | `display_name`, `phone`, `home_*` and `stop_id` are server-only. `latest_preferred_arrival` is a **soft** preference; `flexible_from` is the sim time it lifts (R-5LP at 06:55) |
| `scenarios.json` | `cancel / traffic / full / wav_out → {event, target, sim_time[, multiplier]}` | used by Fleet buttons |

**Golden invariants (tested):**
- On 2026-11-29 at 08:30 there are exactly two female, opted-in irbid_east companions with no soft limit (R-3QM, R-9TD).
- R-5LP prefers to arrive by 08:10 until 06:55.
- R-4HN and R-8PX have the 11:30 class.
- Corridor A→B 2 km, B→C 1 km, C→D 1 km, D→JUST 11 km.
