# UniLink 2.0 — Nine Judging Criteria & 3-Minute Pitch (FINAL)

**Jeeny Next Stop | Track 02 | Build-day addendum**  
**Team:** Lubna (frontend, integration, pitch), Ranad (backend, AI), Rawan (data, fleet, QA).  
**Basis:** Nine judging components reported by the team after speaking to Saad. Pitch duration is confirmed by the team: exactly 3 minutes. Numerical weights, Q&A duration and detailed evaluation rules remain unknown.

Use with `01_UniLink_2.0_FINAL_Master_Playbook.md`, `03_UniLink_Business_Model_FINAL.md` and `05_UniLink_Survey_and_Evidence.md`. The master controls product scope and engineering. Organizer message from Iusef requires a functional MVP/demo and presentation including business model; explicitly name Track 02 — Student & Commuter Mobility. UniLink is a proposed new Jeeny app feature. No invented scoring weights.

## 1. Rubric-to-evidence matrix

| Actual rubric component | What UniLink must prove | Concrete evidence to show | Owner |
|---|---|---|---|
| Problem / user validation | Students experience a recurring commuting problem and care about solving it | Anonymous survey with actual sample size, recent-trip costs and delays, interview quotes with consent, and source-backed local research | Rawan |
| Solution quality | The solution addresses the observed problem in a usable, practical, safe way | User testing, real route comparisons, clear price and time trade-offs, no unsafe substitution or unapproved fare changes | Lubna + Rawan |
| Innovation | UniLink does something meaningfully different from existing campus carpool tools | Best-Deal live reveal and concise comparison with Yalla Jam3a, BlaBlaCar Daily/Karos and conventional ride-hailing | Lubna + Ranad |
| MVP | A usable, coherent prototype exists and can be operated live | Deployed URL, full flow from timetable to confirmed simulated booking, reset, backup video, honest simulation disclosure | Lubna |
| Technical implementation | The application genuinely computes valid answers and withstands changing inputs | FastAPI endpoints, constraint tests, route ordering and fare reconciliation, error handling, measured response latency | Ranad |
| AI integration | AI performs useful product work rather than serving as decoration or merely helping generate code | Real image inference on two different timetable screenshots, editable structured output and parser accuracy evidence; grounded retrieval if implemented | Ranad |
| Business model | Jeeny has a reason to pay and UniLink founders have a sustainable way to earn | Public software-vendor prices, proposed implementation + recurring license, pilot terms, cost allocation, buyer feedback if available | Lubna + Rawan |
| Impact (numbers) | The product can plausibly deliver measurable benefits with a credible evaluation method | Observed baseline costs and times; calculated fare differences for matching trips; actual prototype success rates; prospective pilot KPIs | Rawan + Ranad |
| Pitch + Q&A | The story is clear, memorable, commercially relevant and defensible | Timed live demo, a single clear reveal, explicit ask, source appendix, technical tests and consistent team answers | All; Lubna leads |

The owners coordinate the evidence; the work can be shared. No official weights were provided. Treat all nine components as required.

## 2. Turn one demo into evidence for multiple criteria

1. Start with one real, anonymized student commuting insight, and show survey sample size and actual cost or delay result. This earns problem validation and establishes the stakes.
2. Upload a redacted real timetable. Gemini returns editable structured classes. Confirm the first lecture and show the resulting journey, fare and arrival time. This supports AI integration, solution quality and MVP.
3. Enter a strict same-gender group preference and requested number of companions that yields no feasible match. The engine returns a Best-Deal alternative, e.g., one fewer companion or a different departure, with recalculated fare/time and a reason. Do not relax gender preferences, accessibility, actual capacity or the arrival deadline without a permissible user change; keep hard safety/access constraints intact. This is the innovation reveal and technical proof.
4. Accept the changed offer and confirm a simulated Wallet payment. Show exact amounts; charge only once. Show a co-rider cancellation and if ready Class Shift, then accessibility excluding incompatible options. Emergency is optional Q&A; do not imply unimplemented features work. Never claim guaranteed ten-minute pickup, real payments or actual verified accessibility without supporting evidence.
5. End with market validation, measured prototype evidence and a proposed commercial offer to Jeeny. Point to one approved campus pilot and the measurable criteria for expansion.

**Hero feature:** Best-Deal turns an otherwise unsuccessful search into an explainable, opt-in feasible ride. Do not pitch a generic chatbot or describe every optional feature. If one part is not ready, omit that claim or clearly show it as a concept.

## 3. Problem and solution validation protocol (start immediately)

### Survey: actual student evidence

Use the supplied Arabic survey and analysis rules in file 05. Do not infer exact recent-trip costs, times or last-week lateness from its bundled categories. If needed, run the short separate neutral follow-up. Report actual n, item-level denominators, missingness, collection date, convenience-sample limitations, and counts/percentages. Q6 is stated reliance, Q9 stated price preference; neither equals adoption or purchase. Aim for genuine responses and 3–5 interviews; report any actual n honestly.

### Prototype usability test

Ask 5–10 consenting first-time users, if feasible, to upload a timetable or enter a schedule, choose preferences, interpret the plan and accept or reject a Best-Deal option. Record independent task completion, elapsed time, assistance, confusion and feedback. Include at least one strict-query scenario. Test on real devices. Do not equate this with completed transport trips.

### Route and price comparison

Collect 3–5 equivalent origin/destination and time scenarios, using coarse or redacted origins. Record the actual recent expense reported by a commuter (receipt if available), an actual Jeeny quote captured from the app at a noted time, and a UniLink prototype quote computed on the same scenario. Include a bus baseline if the participant normally takes a bus. Record solo-vs-shared distinctions, passenger count, detour and time differences. Do not book real rides as part of the simulation without appropriate authorization.

A real Jeeny quote is not a completed fare; a model-computed UniLink quote is not observed savings. Show comparisons with correct evidence labels, including cases where the current bus is cheaper.

### Evidence record template

| Evidence ID | Category | Actual result / raw evidence | Sample/denominator | Source or path | Date/time | Limitations |
|---|---|---|---|---|---|---|
| P01 | Survey | TO COLLECT | — | Anonymous survey CSV | — | Convenience sample |
| P02 | Interview | TO COLLECT | — | Consented notes | — | Qualitative |
| S01 | Usability | TO COLLECT | — | Anonymized session log | — | Prototype only |
| S02 | Route comparison | TO COLLECT | — | Redacted fare quote + route result | — | Quoted vs modeled; no observed trip |
| T01 | Tests | TO RUN | — | Actual pytest output | — | Fixture-based tests |
| A01 | Vision | TO RUN | — | Redacted images + manually checked ground truth | — | Small test set |
| B01 | Buyer feedback | TO REQUEST | — | Notes from mentor / Jeeny contact | — | Not a signed deal |

## 4. Innovation, MVP, technical implementation and AI are separate criteria

- **Innovation:** Best-Deal with explainable changes that converts a zero-result search into a feasible alternative. Show what was requested, why it failed, exactly what changed, how much it costs and whether the arrival target is preserved. Compare against existing local campus services rather than claiming all carpooling is novel.
- **MVP:** A working end-to-end experience reachable from a second device. A user can complete the journey flow. Record a genuine backup video. Distinguish working behavior, simulated inputs and planned features.
- **Technical implementation:** Backend actually enforces hard constraints, recalculates routes/fares and updates state. Test invalid requests, no-match, no accessible vehicle, capacity, fare rounding, duplicate Wallet confirmation and reset. Show measured performance, not claimed speed. If OR-Tools or H3 is not implemented, say which real algorithm is used instead. Do not claim shortest or globally optimal routes without an appropriate test/objective.
- **AI integration:** The deployed product itself calls a real vision model, validates outputs, flags uncertainty and uses confirmed timetable data as input to the planner. Test two or more distinct timetables and compare fields to manually recorded ground truth. If RAG is implemented, show one grounded answer and an abstention on an unknown fact. Deterministic safety and pricing logic are good engineering; do not mislabel them as trained ML. AI-assisted coding alone is not evidence of product AI integration.

### Suggested technical evidence commands

Run the repository's actual test command (e.g., `python -m pytest -q` from the correct directory). Preserve the output and commit identifier. Record real endpoint response times using the actual `/api/plan` or `/api/timetable/parse` payloads; separate vision-provider latency from local planner latency. Test at least two input variations and no feasible match. Use the real implementation contract; don't blindly add endpoints from this document. All evidence goes into the team's shared notes and slide appendix.

## 5. Business model: distinguish UniLink's revenue from ride fares

**Paying customer:** Jeeny. **End users:** student and professional commuters. **Model:** B2B2C software licensing, with a one-time implementation fee plus recurring maintenance, license and agreed support. Jeeny retains its transportation revenue and pays drivers and relevant operating costs; UniLink earns software revenue. No extra per-ride founder royalty in the proposed starting deal.

| Proposed commercial milestone | Proposed term |
|---|---:|
| Controlled 30-day paid pilot | JOD 500, credited toward implementation |
| Production acceptance | JOD 1,500 remaining implementation balance |
| Ongoing license and agreed support | JOD 150 per paid month |
| Total implementation + 12 paid subscription months | JOD 3,800 |
| Monthly recurring revenue if contracted | JOD 150 |
| Annual recurring revenue if contracted | JOD 1,800 |

These are proposed commercial terms from the earlier addendum, not observed sale prices, actual revenue or verified willingness to pay. Revenue is not profit. Calculate founder labor, support costs, infrastructure, taxes and other expenses separately. Clarify whether Jeeny pays production API and hosting costs directly; set a bounded support scope. Ask Leena and Jeeny commercial/product staff to validate or revise the offer. Confirm IP and competition terms. Licensing and an outright IP acquisition are different commercial arrangements; no acquisition valuation is established.

Public benchmarks previously researched (recheck live pages before using in the final slide): [Onde](https://onde.app/pricing), [ToolRides](https://www.toolrides.com/pricing), [TaxiCaller](https://www.taxicaller.com/us/en/pricing). Competitor and market context: [BlaBlaCar company figures](https://newsroom.blablacar.com/about-us), [Daily](https://www.blablacardaily.com/a-propos), [Karos acquisition announcement](https://karos-mobility.com/magazine/karos-and-daily-join-forces-to-scale-everyday-carpooling-across-europe), [Yalla Jam3a driver terms](https://www.yallajam3a.com/yallaweb/enw/registrationtermsDrv.php). These products have different scopes; price comparisons are benchmarks, not identical offers.

Jeeny's business case: incremental recurring demand, retention, and potential vehicle utilization. Do not claim profit, market share, actual commission or ROI without Jeeny's data. Include potential cannibalization of existing solo bookings. Door-to-door paid pooling requires legal/operations approval before deployment; ask about permitted campus group-booking models. If production data or regulatory approval is unavailable, propose a controlled pilot rather than guaranteed launch.

## 6. Impact: put numbers on the slide, with honest labels

| Metric | Calculation / method | What may be claimed |
|---|---|---|
| Students reporting transportation lateness | For existing Q5: always + sometimes divided by valid answers, label exact categories; only use late-at-least-once from a separate exact follow-up | Observed self-reported problem prevalence in the sample |
| Typical one-way transport cost and time | Median only from real exact-number last-trip follow-up; Q4 mode/price bands cannot support it | Observed baseline for the sample |
| Willingness to try verified sharing | Use separate follow-up yes/maybe/no; current Q6 measures stated reliance on scheduling, not general willingness to share | Stated intent, not actual adoption |
| Prototype task completion | Independent successful testers divided by first-time testers | Observed usability outcome, not operational adoption |
| Timetable extraction accuracy | Correct evaluated fields divided by labeled fields; record unreadable/abstained fields separately | Measured parser performance on the specific tested images |
| Match feasibility | Valid completed test outcomes and all constraint violations recorded | Measured software behavior under test scenarios |
| Per-trip modeled savings | Actual baseline quote/expense minus comparable computed UniLink quote; percentage relative to positive baseline | Modeled potential savings, not money already saved by students |
| Jeeny incremental contribution | Actual incremental bookings contribution minus cannibalization and other incremental costs | Pilot KPI; no value until required data exists |
| Accessible trip fulfillment | Verified suitable trips completed / requests requiring accommodation | Future pilot impact, not proven by synthetic data |
| On-time arrival and wait time | Real trip timestamps and actual arrival against deadline | Future operational impact, not guaranteed by prototype |

Use [JUST transportation information](https://www.just.edu.jo/iso/Pages/Transportation.aspx) as a baseline source (undated; verify fares with today's riders) and the [GJU sustainability report](https://mail-relay.gju.edu.jo/sites/default/files/Sustainability/gju_sus_report_2025_0.pdf) as independent campus context if it is cited accurately. Historical national statistics and external studies are not the team's own survey.

Recommended stage impact block (fill only after results exist):

- **__ of __ respondents** selected always or sometimes for transportation lateness (Q5; wording mixes time periods).
- **JOD __** median last-trip cost only if collected separately; otherwise show Q4 mode/cost-band counts.
- **__ of __ testers** completed the prototype independently.
- **JOD __ vs JOD __** actual baseline and modeled UniLink price for the same example route.
- **__ of __ tests passed** on the submitted version (technical backup, if not on main slide).

If a number is not available, omit it. Do not use generated placeholders in the pitch or label forecasts as results.

## 7. Pitch + Q&A

Exactly 3:00 (confirmed). Follow master §21:

| Time | Seconds | Content | Rubric evidence |
|---|---:|---|---|
| 0:00–0:25 | 25 | Track 02, real student problem, actual survey n + one finding or external GJU | Problem validation |
| 0:25–0:45 | 20 | Proposed Jeeny feature and actual timetable AI | AI integration, solution |
| 0:45–1:20 | 35 | Strict request → Best Deal → fair split/confirm | Innovation, technical, MVP |
| 1:20–1:45 | 25 | Co-rider cancels; approve new plan; Class Shift only if ready | Innovation, technical, solution |
| 1:45–2:00 | 15 | Wheelchair hard filter/no-option | Solution quality, technical |
| 2:00–2:20 | 20 | Actual user test result, real baseline vs modeled quote | Impact, validation |
| 2:20–2:50 | 30 | JOD 2,000 incl. 500 credit + 150/month, Jeeny benefits, real vendor pricing | Business model |
| 2:50–3:00 | 10 | 30-day approved pilot, QR and close | Pitch and Q&A |

**Total: 180 seconds.** Lubna leads, Rawan controls event, Ranad has actual logs/API docs ready. If the live model is slow, show clearly labeled previously recorded inference or manual input, not a fake call. Rehearse to 2:50–2:55 to leave a small cushion. Do not use a separate finance dashboard. Protect the business block.

If time is cut, protect problem evidence, the Best-Deal reveal, business offer and closing ask. Keep the market, legal, cost, API, test and accessibility details available in appendix/Q&A.

Practice nine questions, one per criterion:

1. What did actual students tell you, and how representative is your sample?
2. How does this solve their problems better than their current bus or ride?
3. What is genuinely new relative to Yalla Jam3a and BlaBlaCar Daily/Karos?
4. Can I change the input and use your prototype myself?
5. How do you enforce capacity, route, fare and accessibility constraints?
6. What does AI do at runtime, how well does it perform, and what if it fails?
7. Who pays you, how much, why would Jeeny pay, and what does maintenance cost?
8. What impact have you measured versus projected, and against which baseline?
9. What concrete decision do you want Jeeny to make after today?

Suggested core line: **When a student's preferred ride doesn't exist, UniLink finds the closest feasible alternative, explains the trade-off, and lets the student decide.** Follow with the commercial offer, not a feature list.

## 8. Time-boxed execution and ownership

Keep the existing build schedule. Start evidence collection immediately; do not wait until the MVP is complete. At the next sync, assign one owner per missing evidence item. During development Rawan should run survey collection and fare quotes; Lubna should preserve the demo flow and add commercial/impact slides; Ranad should deliver the planner, vision integration and measurable tests. Conduct first-time-user tests as soon as the flow works. Freeze features at the planned 20:30 or earlier if behind; reserve the remaining time for testing, evidence capture, rehearsal, backup and submission before the 23:59 deadline (team target 23:00). Use the organizers' actual instructions if they differ.

### Rubric readiness checklist (internal, not official scoring)

- [ ] Problem/user validation: real survey export + sample size + student insight.
- [ ] Solution quality: observed usability and realistic comparative trip case.
- [ ] Innovation: Best-Deal shown with a changed soft constraint and genuine fare/time computation.
- [ ] MVP: public URL, full demo, reset and backup recording.
- [ ] Technical implementation: test log, capacity/accessibility/pricing tests and real endpoint behavior.
- [ ] AI integration: real vision result on distinct images, validated editable data and honest fallback.
- [ ] Business model: actual industry benchmarks, labeled commercial offer, founder revenue and Jeeny benefit.
- [ ] Impact: real baseline + honest calculated/observed outcome numbers; no invented claims.
- [ ] Pitch + Q&A: timed rehearsals, clear pilot ask and proof appendix.

## 9. Prompt for Claude Code / team coding agents

> Read this rubric addendum, the Rev. E master and the business-model addendum. Treat the nine judging components reported by the team as acceptance criteria, not as weighted scoring categories. Audit the existing implementation against each criterion. Return a gap table with present evidence, missing evidence, severity, smallest next action, owner, and verification method. Prioritize the Best-Deal end-to-end flow, genuine timetable AI, hard constraints, correct fare splitting, demo reliability, and measured tests. Avoid large rewrites or unrequested features; preserve the current architecture and file ownership. Do not invent survey responses, real fares, market statistics, business commitments, AI accuracy or performance metrics. Label synthetic fixtures and proposed commercial terms distinctly. Produce a concise demo-evidence record from actual test runs and observed inputs only. For nontechnical criteria, recommend slide content and manual research actions rather than building unnecessary UI. Keep the team on its freeze and submission schedule.

## Limitations

The rubric component names are based on the team's report of its conversation with Saad, not a separately published official scoring sheet. Individual weights and Q&A duration are unknown; pitch is 3 minutes. Team assignments, acceptance criteria, targets, timing, hero feature and business deal are recommendations, not official requirements. No survey, buyer interview, ride experiment, or prototype test has been performed by the author of this addendum. The external links are carried forward from the earlier research; they were not independently rechecked in this addendum. Actual implementation and results must be supplied by the team.
