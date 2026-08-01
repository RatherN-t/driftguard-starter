# Hackathon alignment

Checked on 31 July 2026.

## Eligibility and rules

The Devpost rules state:

- teams must have 4–5 participants;
- all members must register through Rubric;
- work must be original and built during the hackathon;
- the project must use Mistral APIs rather than other model providers;
- code, description, and requested demo material must be submitted before the deadline.

The public schedule states submissions are due at 12:00 pm on 1 August 2026, with the final seven pitching live for ten minutes each.

## Rubric discrepancy to confirm with staff

The current Devpost overview lists:

- Value + Human Insight: 30%
- Creativity + Design: 30%
- Feasibility + Scalability: 20%
- Technical Execution: 20%

The organizer-provided rubric screenshot in the team chat assigns 15 points each to Value and Technical Execution, and 10 each to Creativity and Feasibility. That changes the relative emphasis between technical execution and design. Confirm the latest rubric with staff.

This build plan is robust to either version by heavily prioritizing Value, Technical Execution, and a coherent review interface.

## How DriftGuard scores

### Value + Human Insight

- Built for a specific PM-to-developer handoff, not “everyone.”
- Solves the costly problem of acting on stale shared knowledge.
- Provides role-specific output and focused review.
- Can be validated through three short interviews: one PM, one developer, one designer/ops person.

Evidence to collect:

- last incident involving stale docs;
- time spent explaining code changes to non-developers;
- how often a decision is reopened;
- what makes documentation updates get skipped.

### Technical Execution

The demo contains non-trivial engineering:

- Google Docs structured ingestion and revision-safe updates;
- GitHub PR and full-file retrieval;
- code/document evidence alignment;
- several schema-constrained Mistral stages;
- evidence-ID validation;
- human approval state machine;
- optional Voxtral speaker/timestamp transcription;
- evaluation against hard negatives.

### Creativity + Design

The primary interface is an evidence-backed alignment review, not a chatbot.

The “why did this not exist?” moment is:

> a PM sees the business meaning, a developer sees technical proof, and both approve one shared correction from the same screen.

### Feasibility + Scalability

The hackathon uses realistic low-friction integrations:

- shared Google Drive folder;
- pasted GitHub PR URL;
- direct audio upload;
- SMTP or email preview.

The core evidence/claim/relation architecture can later support Jira, Confluence, Slack, GitLab, and deployment telemetry without changing the product model.

## Requirements checklist

- [ ] 4–5 registered team members
- [ ] all members registered on Devpost and Rubric
- [ ] no non-Mistral model provider in source or dependencies
- [ ] original work started during hackathon
- [ ] repository accessible for judging
- [ ] project description ready
- [ ] stable demo route and backup fixture mode
- [ ] submission completed before deadline
