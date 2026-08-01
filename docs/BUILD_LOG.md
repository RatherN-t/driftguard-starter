# Build log

Coding agents and team members should append concise entries.

## Template

```text
### YYYY-MM-DD HH:MM — milestone
- Implemented:
- Tests:
- Decisions:
- Blockers:
- Next:
```

### 2026-07-31 20:31 +10:00 — Phase 0 configuration and boot foundation
- Implemented: validated secret-safe settings and readiness status; cleared the credential-like sample value; explicitly labelled local fixture provenance; pinned a Next-compatible TypeScript major; hardened project checks to ignore generated dependency/runtime directories.
- Tests: 12 pytest tests passed; smoke test, Mistral-only provider check, JSON/JSONL validation, and focused Ruff checks passed; Next.js production build passed; backend and frontend returned HTTP 200 on ports 8000 and 3000.
- Decisions: demo mode can boot and load fixtures without external credentials, while analysis readiness remains false until MISTRAL_API_KEY is configured; config status returns capability booleans and missing variable names only.
- Blockers: none for Phase 0. npm reports three high-severity transitive advisories through Next.js dependencies, with only a breaking forced downgrade offered; browser-assisted visual verification was unavailable because the browser sandbox metadata was not provided, so HTTP and production-build verification were used.
- Next: after approval, implement the Phase 1 heading-aware document chunker and deterministic evidence IDs against the labelled demo architecture fixture.

### 2026-07-31 20:44 +10:00 — Phase 1 demo document evidence foundation
- Implemented: heading-aware Markdown chunking for `demo/architecture_doc.md`; typed source identity and heading hierarchy on `EvidenceSpan`; inclusive line locators; normalized content; deterministic, traceable evidence IDs derived from source ID, source version, locator, and content hash.
- Tests: 7 focused document/evidence tests passed; complete backend suite passed with 18 tests; Ruff passed on all changed Python files.
- Decisions: title-only and empty sections do not produce evidence, but their headings remain in descendant hierarchy; duplicate headings remain unique through line locators; content changes are section-local when source version is held constant, while a source-version change invalidates all evidence IDs for that version.
- Blockers: none. The existing Starlette TestClient deprecation warning remains unchanged.
- Next: after approval, harden the canonical GitHub PR URL parser and read-only client boundary, including configured limits and success/failure tests, without starting Mistral orchestration.

### 2026-07-31 20:59 +10:00 — GitHub PR read boundary
- Implemented: strict canonical PR URL parsing; sanitized read-only GitHub client errors; authenticated headers; pagination; file-count and byte limits; full-file reads at an explicit ref; clearly labelled local PR fixture routing for demo mode.
- Tests: 22 focused GitHub tests passed; complete backend suite passed with 38 tests; Ruff passed on all changed Python files.
- Decisions: query strings, fragments, alternate hosts, ports, userinfo, noncanonical PR numbers, unsafe repository paths, and upstream error bodies are rejected; demo data is returned only for the exact known fixture URL.
- Blockers: none. Live private-repository reads still require a read-only GITHUB_TOKEN.
- Next: normalize PR metadata, patches, and selected full-file content into typed evidence with deterministic IDs and duplicate protection.

### 2026-07-31 21:03 +10:00 — GitHub evidence normalization
- Implemented: selected merge/head SHA retrieval; typed PR metadata, patch, changed-file, and full-file evidence; deterministic IDs and line/patch locators; source/version/path preservation; atomic duplicate protection and unknown-reference validation.
- Tests: 17 focused evidence/client tests passed; complete backend suite passed with 45 tests; Ruff passed on all changed Python files.
- Decisions: full-file content must correspond to a declared changed file; unsafe and duplicate paths are rejected; repeated ingestion is ID-stable; content-only changes remain localized when the source version is unchanged.
- Blockers: none.
- Next: implement validated Mistral structured-output extraction with transient retry rules, unknown-evidence rejection, and a deterministic demo fixture fallback.

### 2026-07-31 21:07 +10:00 — Structured claim extraction boundary
- Implemented: strict Pydantic model outputs; Mistral `chat.parse` gateway; bounded transient/schema-repair retries; recursive evidence-reference validation; document/code extraction services; deterministic evidence-derived demo fallback.
- Tests: 8 focused gateway/extraction tests passed; complete backend suite passed with 53 tests; Ruff passed on all changed Python files.
- Decisions: nontransient failures are never retried; upstream failure details are not exposed; demo fallback activates only without a configured gateway and only when labelled fixture evidence matches; live mode without Mistral fails clearly.
- Blockers: none. Live model execution requires MISTRAL_API_KEY and was covered with injected client tests rather than a credentialed call.
- Next: implement deterministic lexical candidate matching followed by validated drift classification and uncertainty handling.

### 2026-07-31 21:09 +10:00 — Candidate matching and drift classification
- Implemented: deterministic lexical candidate scoring across subjects, statements, aliases, headings, files, and symbols; strongest-candidate ordering; evidence-validated Mistral drift classification; conservative demo classification with confidence and missing-evidence reporting.
- Tests: 3 focused matching/classification tests passed; complete backend suite passed with 56 tests; Ruff passed on all changed Python files.
- Decisions: future-state claims are not flagged solely for being unimplemented; disabled behavior is ambiguous; requirements that conflict with observed code are classified as contradictions; the seeded synchronous-to-async scenario is stale documentation.
- Blockers: none.
- Next: generate PM/developer explanations and a minimal non-executing patch from the same validated evidence.

### 2026-07-31 21:11 +10:00 — Grounded role views and patch proposal
- Implemented: PM and developer explanations from one validated candidate/assessment; role-level evidence citations; minimal line-addressed replacement proposal with current text, proposed text, rationale, revision, unresolved item, and evidence IDs.
- Tests: 3 focused output tests passed; complete backend suite passed with 59 tests; Ruff passed on all changed Python files.
- Decisions: non-actionable assessments cannot produce patches; the proposal replaces only the factual paragraph line and does not execute a write; the unresolved failure-message decision remains visible.
- Blockers: none.
- Next: compose the fixture ingestion, extraction, matching, classification, explanations, and proposal into one stable alert API contract.

### 2026-07-31 21:14 +10:00 — End-to-end demo alert API
- Implemented: deterministic fixture pipeline from document/PR evidence through extraction, candidate matching, stale-documentation classification, role views, and minimal patch; stable list/detail alert API contract with provenance, confidence, uncertainty, and all supporting evidence.
- Tests: 3 focused alert API tests passed; complete backend suite passed with 62 tests; Ruff passed on all changed Python files.
- Decisions: the API explicitly labels fixture inference and sources; alert IDs derive from cited evidence; unknown alert IDs return 404; every claim, assessment, explanation, and patch citation must exist in the returned registry.
- Blockers: none.
- Next: replace the static frontend with the API-backed alert review experience and complete loading, empty, error, and credential-unavailable states.

### 2026-07-31 21:19 +10:00 — API-backed alert review experience
- Implemented: responsive alert review UI backed by `/api/alerts`; source/demo badges; evidence disclosures; PM/developer tabs; confidence, uncertainty, and minimal diff; loading, empty, API-error, and missing-live-credential states.
- Tests: frontend TypeScript check and Next.js production build passed; backend suite passed with 62 tests; live HTTP probes confirmed one stale-documentation alert and a rendered loading shell on ports 8000/3000.
- Decisions: review actions remain disabled until the approval state machine exists; demo fallback status is explicit; evidence content is hidden behind deliberate disclosure controls.
- Blockers: browser-assisted visual verification was unavailable because browser sandbox metadata was not provided; build and HTTP fallback checks passed.
- Next: implement explicit approval/rejection transitions and durable audit events before enabling review actions.

### 2026-07-31 21:24 +10:00 — Approval, rejection, and durable audit
- Implemented: SQLite-backed review state; explicit pending→approved/rejected transitions; duplicate/invalid transition protection; actor, timestamp, comment, reason, prior/new state, patch, and evidence audit capture; frontend reviewer controls; deterministic review-state reset.
- Tests: 3 focused state/audit tests passed; complete backend suite passed with 65 tests; Ruff passed; frontend TypeScript check and production build passed.
- Decisions: approval records intent but never applies a write; only an explicit runtime review action changes state; rejected and already-approved alerts cannot be transitioned again.
- Blockers: none.
- Next: implement separately invoked, approval-gated demo local-copy application and mocked revision-safe Google Docs write-back.

### 2026-07-31 21:29 +10:00 — Approval-gated safe write-back
- Implemented: separately invoked apply route; fixed-path atomic demo local-copy update; original-line and fixture-version checks; Google Docs character-range verification, revision re-fetch, and `requiredRevisionId` batchUpdate; applied-state audit; reset removes local output.
- Tests: 3 focused write-back tests passed; complete backend suite passed with 68 tests; Ruff passed; frontend TypeScript check and production build passed.
- Decisions: approval never writes automatically; application requires a second explicit action; live writes reject demo evidence and disabled configuration; duplicate apply is blocked.
- Blockers: no live write was attempted. Live Google application requires service-account credentials, editor access, a live alert target, and GOOGLE_WRITE_ENABLED=true.
- Next: add paginated Google Drive folder reads and heading-aware Google Docs evidence normalization while retaining fixture fallback.

### 2026-07-31 21:32 +10:00 — Google Drive and Docs read ingestion
- Implemented: validated folder IDs; paginated Drive listing; Google Docs retrieval; TITLE/HEADING hierarchy preservation; character-range evidence locators; source/revision identity; duplicate/empty heading handling; credential-free labelled fixture sync.
- Tests: 7 focused Google/demo tests passed; complete backend suite passed with 73 tests; Ruff passed on all changed Python files.
- Decisions: live mode fails clearly without both service-account file and folder ID; connector exceptions are sanitized; fixture mode never presents local data as a live Drive result.
- Blockers: live service-account calls were not executed because credentials are absent; all client behavior was tested with injected services.
- Next: add Voxtral audio and text transcript ingestion, timestamped evidence, and structured decision extraction with a deterministic text fallback.

### 2026-07-31 21:36 +10:00 — Transcript and decision ingestion
- Implemented: timestamped text transcript parser; speaker/time evidence; Voxtral batch upload boundary with diarization, segment timestamps, size limit, and project context bias; structured decision/proposal/unresolved/action extraction; credential-free supplied-transcript fallback.
- Tests: 4 focused transcript tests passed; complete backend suite passed with 77 tests; Ruff passed on all changed Python files.
- Decisions: untimestamped text is rejected; audio never falls back to fabricated transcription; every extracted decision cites known speaker/timestamp evidence; unresolved customer messaging remains explicitly ambiguous.
- Blockers: live Voxtral execution requires MISTRAL_API_KEY and was covered with an injected client, not an external call.
- Next: implement role-safe email preview and optional approval-gated, deduplicated SMTP delivery.

### 2026-07-31 21:43 +10:00 — Approval-gated notifications
- Implemented: credential-free PM/developer email preview; approval-gated SMTP delivery; explicit configuration validation; recipient validation; actor attribution; deterministic duplicate-send protection; safe retry after a failed delivery.
- Tests: 4 focused notification tests passed; complete backend suite passed with 81 tests; Ruff passed on all changed Python files.
- Decisions: preview is always local and never sends; SMTP is disabled by default; sending requires an explicit approved/applied state and a separate runtime request; delivery errors are sanitized and never expose credentials.
- Blockers: no real email was sent. Live delivery requires SMTP configuration and an approved alert; core demo behavior does not depend on email credentials.
- Next: run the labelled evaluation corpus, add stale/ambiguous/no-drift readiness scenarios, expand the end-to-end smoke path, and complete the final demo verification.

### 2026-07-31 21:46 +10:00 — Mistral hybrid evidence retrieval
- Implemented: typed hybrid retrieval over evidence spans; deterministic lexical scoring; Mistral text embeddings for documents/transcripts; Codestral embeddings for code; cosine reranking; stable evidence-ID tie-breaking; malformed-response validation.
- Tests: 4 focused retrieval tests passed; complete backend suite passed with 85 tests; Ruff passed on all changed Python files.
- Decisions: embeddings are an optional reranker after the direct deterministic pipeline; no fabricated local vectors are used; credential-free demo behavior keeps the established lexical path; absent credentials and upstream failures are explicit and sanitized.
- Blockers: live embedding execution requires MISTRAL_API_KEY and was tested with an injected SDK-compatible client rather than an external request.
- Next: expose the transcript decision log in the review UI, then add the seeded evaluation dashboard and human false-positive feedback capture.

### 2026-07-31 21:50 +10:00 — Evidence-linked decision log UI
- Implemented: labelled demo transcript endpoint; confirmed/unresolved/action decision grouping; speaker/timestamp evidence links; status and condition display; responsive decision timeline beneath the alert review.
- Tests: 5 focused transcript tests passed; complete backend suite passed with 86 tests; Ruff passed; frontend TypeScript check and Next.js production build passed; live HTTP probes returned 200 and confirmed one decision, one unresolved item, and five evidence spans.
- Decisions: the decision log is a review surface, not a chatbot; fixture data is visibly labelled; live mode does not silently substitute the demo transcript.
- Blockers: browser-assisted visual inspection remained unavailable because the browser sandbox metadata was not provided; production build and HTTP fallback verification passed.
- Next: evaluate every labelled case, expose seeded precision/readiness results, and capture reviewer false-positive feedback without triggering writes.

### 2026-07-31 21:55 +10:00 — Seeded evaluation and reviewer feedback
- Implemented: reproducible eight-case labelled evaluation; explicit stale/ambiguous/no-drift coverage; relation accuracy, actionable precision, citation coverage, and hard-negative false-positive metrics; API-backed dashboard; durable evidence-linked correct/needs-evidence/false-positive reviewer feedback.
- Tests: 6 focused evaluation/classification tests passed; complete backend suite passed with 89 tests; Ruff passed; frontend TypeScript check and Next.js production build passed.
- Results: 8/8 exact relation/actionability matches, 100% relation accuracy, 100% actionable precision, 100% citation coverage, and zero hard-negative false positives.
- Decisions: evaluation inputs and results are visibly labelled as seeded fixtures; feedback captures reviewer judgment but never changes review state or triggers a write; all result citations resolve to case evidence.
- Blockers: browser-assisted visual inspection remains unavailable because browser sandbox metadata is absent; compilation and API verification remain the fallback.
- Next: expand the end-to-end smoke test, run provider/fixture/readiness checks, update the five-minute demo script, and perform the final release gate.

### 2026-07-31 22:01 +10:00 — MVP vertical slice release gate
- Implemented: full credential-free smoke workflow across fixture ingestion, evidence-backed stale alert, transcript decisions, seeded evaluation, reviewer feedback, email preview, approval, separate local-copy application, audit, and reset; updated five-minute demo and deployment commands.
- Release checks: complete backend suite passed with 89 tests; Ruff passed across `apps` and `scripts`; Mistral-only provider scan passed; 6 JSON/JSONL files validated; end-to-end smoke passed with 8/8 evaluation cases; frontend TypeScript check and Next.js production build passed.
- Boot verification: fresh FastAPI and Next.js processes returned HTTP 200; the live probes returned one alert, one confirmed decision, and 8/8 exact evaluation results. Verification processes were stopped afterward.
- Decisions: P0 and P1 are complete; P2 workflow/webhook/OAuth/platform expansion remains intentionally out of MVP scope; the demo performs no external reads, writes, or sends and requires two explicit runtime actions before even the local-copy write.
- Blockers: no blocker for the credential-free demo. Live Mistral, GitHub private-repository, Google Drive/Docs, Voxtral, and SMTP execution still require their respective credentials/configuration; no live external write or email was attempted. Browser visual automation was unavailable because its sandbox metadata was absent.
- Known warning: Starlette emits one TestClient/httpx deprecation warning. npm previously reported three high-severity transitive advisories in the pinned frontend tree, with only a breaking forced remediation offered; dependency migration should be handled separately from the demo freeze.

### 2026-08-01 02:17 +10:00 — Unified linked-source workspace and document inspector
- Implemented: one setup flow for a Google Doc or labelled local Markdown document, matching GitHub repository and PR URLs, timestamped transcript text, and Voxtral audio; one analysis endpoint now composes those sources into the active review.
- Source clarity: the UI and API name the exact source URI, source ID, revision/SHA, changed files, transcript segment count, and patch target. Demo mode explicitly states that `demo/architecture_doc.md`, local PR metadata, and local changed Python files are used without contacting Google or GitHub.
- Document visibility: added full before/proposed document panes and a third actual-applied pane after the separately approved local-copy write; added a richer hackathon architecture mock with ownership, customer contract, reliability controls, decision history, and one seeded stale claim.
- Safety: repository and PR identity must match; live Google links fail clearly without the service-account file; live source analysis fails clearly without Mistral; tests now forcibly isolate all configured external credentials so they can never make provider calls.
- Verification: 37 focused linked-source/document tests passed; complete backend suite passed with 100 tests; Ruff passed across `apps` and `scripts`; Mistral-only and JSON/JSONL checks passed; end-to-end smoke passed; frontend TypeScript and production build passed; fresh HTTP verification returned four exact sources and the expected synchronous-before/HTTP-202-after document view.
- Blockers: none for the credential-free hackathon demo. Browser visual automation remained unavailable because its sandbox metadata was absent, so production build, server-rendered markers, API payload verification, and live HTTP checks were used.

### 2026-08-01 — Restarted-service local UAT
- Restarted: stopped only the verified DriftGuard uvicorn and Next.js process trees, then started the current backend/frontend on `127.0.0.1:8000` and `127.0.0.1:3000`; health, source form, and current analysis returned HTTP 200.
- Added: reproducible `scripts/uat_test.py` against the running services, covering four-source linking, repository/PR mismatch rejection, meeting decision evidence, approval-without-write, separate document application, actual written-content equality, audit events, frontend response, and final reset.
- Verification: deployed-service UAT passed; complete backend suite passed with 100 tests; Ruff passed across `apps` and `scripts`; Mistral-only scan and frontend TypeScript check passed. The app was opened in the default browser.
- Live status: Mistral is configured. Google read/write and GitHub authentication are absent; `git`, `gh`, and `gcloud` are unavailable. Creating disposable real Google/GitHub resources is therefore blocked pending locally supplied authorization or authenticated connectors.

### 2026-08-01 — Loopback CORS repair and credential handoff
- Fixed: development CORS now accepts both `http://localhost:3000` and `http://127.0.0.1:3000`, while retaining the explicitly configured web origin. This resolves the frontend's false "API unavailable" state when opened through the previously supplied `127.0.0.1` link.
- Verification: focused health/CORS tests passed with 2 tests; complete backend suite passed with 101 tests; Ruff passed across `apps` and `scripts`; restarted-service UAT passed; the restarted backend returned HTTP 200 and the correct CORS header for both loopback origins.
- Documentation: expanded the Google service-account and GitHub fine-grained-token handoff with exact local paths, least-privilege permissions, safe enablement order, canonical URL requirements, and official setup links.
- Safety: no credential values were read or printed. Mistral is configured; Google folder/read/write and GitHub authentication remain intentionally disabled until the user installs credentials locally.

### 2026-08-01 — Live Google Doc seed and tab-aware evidence repair
- Live source: populated the user-authorized empty `Hackathon` Google Doc with the checkout/payments architecture mock in one revision-controlled update, including 11 native heading styles and the intentionally stale synchronous/HTTP-200 contract.
- UAT finding: current Google Docs API responses place body content under `tabs[].documentTab.body` when `includeTabsContent=true`; the legacy top-level-only parser therefore returned zero evidence against the real document.
- Fixed: both evidence normalization and revision-safe target validation now resolve legacy or single-tab bodies. Multiple tabs fail explicitly because character indices would otherwise create ambiguous locators.
- Verification: 9 focused Google evidence/writeback tests passed; complete backend suite passed with 104 tests; Ruff passed across `apps` and `scripts`; the real Doc now yields eight unique heading-aware evidence spans and contains the expected synchronous claim.
- GitHub status: the locally configured token reads the private `esxyz0120/hackathon` repository, but GitHub rejected branch, content, and PR creation with HTTP 403. No GitHub resource was created; the token still needs Contents and Pull requests write permissions for the one-time UAT setup.

### 2026-08-01 — Real Google/GitHub/transcript UAT and applied-document verification
- Live sources: populated the supplied Google Doc, verified it inside the configured Drive folder, created `esxyz0120/hackathon` branch `driftguard-async-checkout-uat`, added `payment_api.py` and `payment_worker.py`, and opened real PR `#1` without modifying `main` directly.
- Live analysis: linked the exact Google Doc, private repository, PR, and timestamped meeting transcript; produced a high-severity cited contradiction targeting `Customer-facing contract > Payment processing` at the exact Google range `chars:599-887`.
- Approval/write gate: unapproved apply returned HTTP 409 and made no change; separate reviewer approval and apply produced exactly two audit events; Google accepted the revision-controlled write; direct provider read verified the stale synchronous paragraph was absent and the HTTP 202/pending statement was present.
- UAT fixes: added current single-tab Google Docs parsing; short model-facing citation aliases with restoration to full deterministic IDs; deterministic exact Google paragraph targeting; ranked-candidate evaluation that skips compatible pairs; change-signal ranking for synchronous/async, pending-state, status-code, and idempotency conflicts; active-analysis persistence across restarts; and actual post-write Google content in the applied inspector.
- Safety: model-selected evidence remains validated against the registry; model text cannot choose the write target/range; multi-tab documents fail explicitly; active-analysis tests use isolated SQLite files; no secret value was printed or stored in the active-analysis payload.
- Verification: 110 backend tests passed with one existing Starlette/httpx deprecation warning; Ruff passed across `apps` and `scripts`; Mistral-only provider scan passed; direct Google verification and real GitHub PR creation succeeded.
- Final restart acceptance: cleanly restarted both services, then confirmed backend health and frontend HTTP 200; the persisted applied alert restored all four source roles, PR `#1`, both approval/write audit events, and Google-fetched applied content exactly matching the proposed HTTP 202/pending replacement.
