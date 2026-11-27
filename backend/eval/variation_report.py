"""Prints a table of /api/plan outcomes for varied inputs (evidence that results are computed, not replayed).
Run: python -m backend.eval.variation_report"""
import sys; sys.path.insert(0,'.')
from fastapi.testclient import TestClient
from backend.main import app
from backend.tests.test_contract import trip_tsx_plan
c=TestClient(app); n=[0]
def show(tag, pre=None, **kw):
    n[0]+=1; s=f"v{n[0]}"
    if pre: pre(s)
    r=c.post("/api/plan",json=trip_tsx_plan(s,**kw)).json()
    if "options" not in r: print(f"{tag:30} ERROR {r['code']}"); return
    print(f"{tag:30} {r['status']:19}", [(o['plan_id'],o['relaxed'],o['fare']['your_share_fils'],o['leave_home'],o['arrival'],len(o['pickup_order']),o['vehicle']['kind']) for o in r['options']], r.get('reason',{}).get('code',''))
for cs in ["08:00","08:30","08:45","09:00","11:30"]: show("class "+cs, class_start=cs)
show("class 11:30 c2 pk10:47", class_start="11:30", pickup="10:47", companions=2)
show("class 11:30 c3 pk10:47", class_start="11:30", pickup="10:47", companions=3)
for cap in [1000,1500,1565,1859,1860,5000]: show(f"cap {cap}", cap=cap)
for k in [0,1,2,3]: show(f"companions {k}", companions=k)
show("companions 0 cap 5000", companions=0, cap=5000)
for pk in ["07:30","07:40","07:50","07:54"]: show("pickup "+pk+" c2", pickup=pk, companions=2)
def out(*vids):
    def f(s):
        for v in vids: c.post("/api/simulation/event", json={"session_id":s,"event":"vehicle_unavailable","target":v,"sim_time":"06:10"})
    return f
sed=[f"SED-0{i}" for i in range(1,7)]
show("all sedans out c2", pre=out(*sed), companions=2)
show("all sedans+big out c2", pre=out(*sed,"BIG-01","BIG-02"), companions=2)
show("big car required c2", companions=2, big_car=True)
