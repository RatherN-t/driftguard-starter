# Build task board

Mark tasks `[x]` only after acceptance criteria and tests pass.

## P0 — demo-critical

- [x] Backend and frontend boot with documented commands.
- [x] Environment validation and safe config-status endpoint.
- [x] Local demo fixture loader.
- [x] Google Drive folder listing and Google Docs read adapter.
- [x] Heading-aware Google Docs chunker with ranges and revision IDs.
  - [x] Parse current single-tab Google Docs responses without ambiguous cross-tab locators.
  - [x] Demo Markdown chunker with heading hierarchy, exact line locators, and deterministic evidence IDs.
- [x] GitHub PR URL parser.
- [x] GitHub PR metadata and changed-files adapter.
- [x] Full changed-file retrieval at merge/head SHA.
- [x] Evidence registry and unknown-ID rejection.
- [x] Mistral structured document-claim extraction.
- [x] Mistral structured code-change extraction.
- [x] Candidate claim retrieval using exact terms and aliases.
- [x] Mistral drift classification.
- [x] PM and developer explanations.
- [x] Minimal patch proposal.
- [x] Alert API and review UI.
- [x] Approve/reject state machine.
- [x] Google Docs revision-safe update.
- [x] Audit log.
- [x] Reliable demo reset.
- [x] Unified document/repository/PR/transcript linking with exact source provenance.
- [x] Full document before/proposed/applied inspector.
- [x] Restart-safe persistence of the active linked-source review.
- [x] Direct post-write Google Docs verification in the applied inspector.

## P1 — judging boost

- [x] Voxtral audio upload and transcription.
- [x] Speaker/timestamp evidence.
- [x] Decision extraction with proposal/confirmed/rejected distinction.
- [x] Decision log UI.
- [x] Console email preview.
- [x] SMTP delivery.
- [x] Mistral text embeddings for document retrieval.
- [x] Codestral embeddings for code retrieval.
- [x] Evaluation dashboard with seeded precision results.
- [x] Human feedback capture on false positives.

## P2 — only when P0 and P1 are stable

- [ ] Mistral Workflows durable orchestration.
- [ ] Scheduled Google Drive reconciliation.
- [ ] GitHub webhook ingestion.
- [ ] OAuth and multi-user project setup.
- [ ] Additional document platforms.
