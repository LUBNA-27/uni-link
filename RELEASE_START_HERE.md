# UniLink 2.0 — merged Replit release candidate

Track 02 — Student & Commuter Mobility. This is the single complete import ZIP, not a patch. All three uploaded archives were reconciled: `unilink-integrated (1).zip` (backend, compatible bundled data and scripts), `unilink_frontend_latest.zip` (Lubna's latest React/Arabic/Insights source, dependencies, competition docs), and `unilink-gemini-update (1).zip` (backend-only Gemini model/evaluation update). The base already included demo A/B and their truth files; those are preserved. No pricing, matching or replanning algorithms were rewritten.

## Replit quick start
1. In the team's existing `uni-link` workspace, select Import > Zip file, and import this ZIP once. Do not also import the separate archives. The ZIP is flat (project root files at archive root), including `.replit`.
2. Add these Replit Secrets in that same application (do not share the key): `GEMINI_API_KEY` (private key), `GEMINI_MODEL` (`gemini-3.8-flash`, or a supported model accessible to your Google project), `GEMINI_THINKING_LEVEL` (`low` for compatible Gemini 3.x models).
3. Click Run. The configured script installs Python dependencies, installs frontend dependencies from the lockfile if needed, builds the UI and starts one FastAPI worker on port 8000. No Agent prompt is needed unless setup fails. If Replit does not supply runtimes automatically, enable Python 3.11+ and a Vite-compatible recent Node runtime (Node 22.12+). Use the same-origin app.
4. Open `/api/health` and the normal app URL. All 11 frontend endpoint flags are now live by default. `?live=mock` is explicitly labeled offline QA only, not a live demonstration. Never hide a live API failure with mock results.
5. From project root, run the verification commands below. Use the stage's separate session IDs for Sara and Zaid.
6. Publish using one instance, one Uvicorn worker (e.g. Reserved VM if your credits allow). State is in memory and resets on restart. Verify the deployment has the Gemini secrets. Test the published URL on another phone and keep the recorded backup.

```bash
python -m pip install -r requirements.txt
python -m pytest backend/tests --ignore=backend/tests/test_gemini_live.py -q
python -m pytest backend/tests/test_gemini_live.py -q -s -rs
# while the application is running:
python -m backend.smoke_live http://localhost:8000
# after publishing, use your actual URL:
# python -m backend.smoke_live https://YOUR-APP.replit.app
# python -m backend.eval.gemini_eval https://YOUR-APP.replit.app
```

Manual launch if Run fails:
```bash
python -m pip install -r requirements.txt
(cd frontend && npm ci --include=dev && npm run build)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## Merge-specific checks (performed on this source tree)
- Python source compilation passed; fixture loader read 60 anonymous synthetic riders.
- Actual fare allocation function reproduced BD1 [1860,1380,1260], BD2 [1565,1085,965,885], R2 [1900,1420,1180], pair [2490,2010], and solo 4260 fils using documented synthetic legs and loaded tariff values.
- Three distinct timetable PNG files decoded successfully, with nonempty corresponding truth JSON.
- Frontend static translation audit: 193 strings used, 0 missing Arabic within the supplied script's scope (excludes DevDrawer, mocks and dynamic text). Not a browser test.
- All 11 endpoint defaults are live, and an explicit mock override is present. Frontend manifest and lockfile dependencies agree. Replit config parsed and shell script passed syntax checks.
- Frontend production build and full backend pytest were NOT independently run to completion on this merged snapshot: H3/Google GenAI unavailable in this environment; dependency retrieval failed or timed out. Actual Gemini inference was NOT executed; no key was used.
- Files in `evidence/` and `BUILD_STATUS.md` are prior team/Claude logs, not new results for this merge. Re-run the full suite and smoke test before quoting any counts. The base log reports 118 passed and 5 live-Gemini checks skipped, before the newest delta was applied.

## Deliberate release changes
- Latest frontend had its mock flags off for live operation despite the separate integration report. Switched every default to live and added `?live=mock` as an explicit QA fallback; updated the drawer helper and existing browser test's simulation chip wording.
- Run/build commands explicitly install the existing requirements and build with the supplied frontend lockfile; set one worker. Preserved deployment target from the source configuration.
- Retained the bundled operational dataset instead of replacing it with an incompatible external dataset. Retained competition docs and prior evidence. No API credentials, node_modules, build caches or Git history are included in this export.

## Remaining known limitations
This is a hackathon prototype: all transportation demand, dispatch, traffic, tariffs, bookings, and Wallet operations remain simulated; no live ride or payment is performed. Gemini requires a valid key and enabled model/quota. This export does not include real survey results, verified actual routes, or completed pilot data. The final URL, browser integration and AI inference still need release verification. `BUILD_STATUS.md` describes earlier known behavior, including the pickup-time default issue. Avoid expanding scope until the actual live flow is checked.
