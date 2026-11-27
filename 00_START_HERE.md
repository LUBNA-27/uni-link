# UniLink 2.0 — Final competition package (Rev. E)
**27 November 2026 · Track 02: Student & Commuter Mobility · Lubna / Ranad / Rawan**

This folder supersedes all previous playbook versions. **Do not give Claude the older PDF, Rev. D or earlier addenda alongside these files.** The product is a proposed new Jeeny app feature (Campus Commute), not a standalone competing transportation operator. The current codebase is not included or inspected by the document editor.

## Read in this order
| File | Purpose | Owner / usage |
|---|---|---|
| `01_UniLink_2.0_FINAL_Master_Playbook.md` | Authoritative product, API, fixtures, architecture, priorities, owner-specific prompts, Q&A | All; primary coding context |
| `04_UniLink_Rubric_and_3_Minute_Pitch.md` | Actual nine criteria, exact 180-second stage plan and proof checklist | All; Lubna leads |
| `05_UniLink_Survey_and_Evidence.md` | Actual Arabic survey, limitations, follow-up and real evidence templates | Rawan + all |
| `03_UniLink_Business_Model_FINAL.md` | Market sources, competitor pricing, proposed offer, ROI and regulatory caveats | Lubna + Rawan |
| `02_UniLink_Judging_Panel_FINAL.md` | Announced judges/mentors, source links, likely professional lenses and tailored Q&A | All; strategic context only |

If any companion wording conflicts with master §§00, 06, 10–11, 19, 21–22, the master wins; current organizer instructions override all documents. The accompanying survey is an instrument, not results. Use source links as research, not live APIs.

## Confirmed from team/organizer communication
- Iusef: submit **functional MVP/demo** and **presentation to pitch tomorrow including business model**; identify track. A product, service or feature within Jeeny is permitted. We choose **Track 02** and a feature within Jeeny. Team-confirmed pitch: **3 minutes**. Event schedule: submit by 23:59 Amman time; team aims 23:00. No known Q&A length/weights; backup video useful but not inferred as a third required deliverable.
- Saad's nine components: problem/user validation, solution quality, innovation, MVP, technical implementation, AI integration, business model, impact (numbers), pitch + Q&A. No invented weights.

## Today: do not let feature creep beat evidence
P0: real timetable or honest manual fallback, Door-to-Door match, Best Deal, leg-weighted fare, simulated confirmation, cancellation rescue, Class Shift, accessibility/no-option, testing, deployment, real survey/validation and three-minute pitch. P1: Emergency, bilingual labels and fleet controls (required event trigger P0). P2: Shuttle, Split-Link, Ride & Box, voice conversation, prediction, advanced map, institutional-pass UI. Cut P2 first. Do not start a new project if a working one exists. Freeze 20:30 or earlier if behind.

**Important numerical invariants (simulation):** BD1 1,860 + 1,380 + 1,260 = 4,500; BD2 1,565 + 1,085 + 965 + 885 = 4,500; R2 1,900 + 1,420 + 1,180 = 4,500. Event 06:55, shift 07:05; refund actual 1,900 then charge 1,860. Wallet 12,000 → 10,140 → 10,100 → 10,140. S1 begins with 3 seats for group of 3. Fare cap 2,000 excludes pair/solo quote unless explicitly changed. Exact demo times still require actual fixture alignment and tests. Do not hardcode outputs or invent measured metrics.

**Commercial proposal [not a signed contract]:** JOD 500 paid pilot credited toward JOD 2,000 total implementation, then JOD 150/month after acceptance. 2,000 + 12×150 = JOD 3,800 conditional contract revenue. Jeeny keeps approved transport revenue; captain compensation is separate. No real dispatch/payment, no claims of regulatory authorization, no unverified accessibility guarantee or 10-minute real pickup promise. Real deployment contingent on Jeeny/LTRC, insurance and privacy approvals. License vs acquisition are separate.

## Paste into Claude Code (one prompt)
```text
Read all six Markdown files in this folder, starting with 00_START_HERE.md, then the Rev. E master (01) and the rubric (04). Treat the master as authoritative and preserve the current repo and team ownership. Do not implement an older plan or automatically rewrite the project. We have a 3-minute pitch and two required deliverables (functional MVP/demo + presentation including business model); Track 02.

FIRST: inspect the current branch, git status, files, actual endpoints, schemas, fixtures, test status and deploy command. Report a compact P0/P1/P2 gap table: what is already implemented, what is missing, smallest fix, owner, verification method and risk. Identify contradictions between current implementation and Rev. E; do not change other members' files without coordination. Ask only blocking questions. If working code differs from fixture details, preserve genuine behavior and agree on a consistent schema/fixture before editing; never hardcode expected outputs.

SECOND: implement the smallest P0 fixes in the files I own (backend/** for Ranad, Student UI/api/deploy for Lubna, data/** and Fleet for Rawan). Genuine AI timetable inference when credentials work, hard capacity/gender/access/deadline filters, fair integer-fils pricing, Best Deal, consent, cancellation rescue/shift, session revision/idempotency, no unsafe fallback. Maintain clear simulation labels, no real dispatch or money. Keep optional features out unless P0 and evidence are stable.

THIRD: run actual tests and report raw pass/fail counts, commit identifier, real response times and unresolved blockers. Record evidence only if actually observed. Do not generate survey answers, receipts, metrics, purchase agreements or live integrations. No private student response rows in the repo. Proposed B2B fees are separate from simulated passenger fares. Preserve the 3-minute pitch business/impact blocks; recommend slide/evidence changes rather than unnecessary UI. Stop adding scope at 20:30; prioritize deployment, QA, backup recording and submission.
```

## Handoff note
These files were revised from Lubna's Rev. D and the earlier research addenda, plus the organizer message, team-confirmed pitch and actual Arabic questionnaire. The editor checked sample fare arithmetic, chronology, refund and seat capacity, and rechecked selected pricing, transport and regulatory sources; not every historical URL was freshly verified. No repo/test execution, first-hand survey results or commercial acceptance was supplied. Read the audit notes in the master and the limitations in each companion. Use actual team results to populate slides and evidence before presenting; no placeholders or fictional results in the final deck.
