# Devpost and submission checklist

## Required

- [ ] every team member joined the Devpost team
- [ ] every team member registered through Rubric
- [ ] project repository URL
- [ ] project title and one-line description
- [ ] problem and target user
- [ ] what was built during the hackathon
- [ ] Mistral APIs used
- [ ] screenshots
- [ ] demo video/link if requested
- [ ] testing instructions
- [ ] submission before 12:00 pm on 1 August 2026

## Suggested description

### Inspiration

Teams increasingly create code and documentation faster than they can keep them synchronized. Product managers then make decisions from documents that no longer match implementation or approved meeting decisions.

### What it does

DriftGuard reads project Google Docs, a GitHub pull request, and an optional meeting recording. It detects semantic drift, shows exact evidence, translates the impact for product managers and developers, and proposes a minimal approved documentation update.

### How it was built

- Mistral structured outputs for claim extraction and drift judging
- Mistral Voxtral for meeting transcription
- Mistral embeddings for optional retrieval
- Google Drive and Docs APIs
- GitHub REST API
- FastAPI and Next.js

### Challenges

- distinguishing implementation from product intent;
- avoiding false decisions from meeting discussion;
- grounding every generated statement;
- editing a live document safely after human review.

### Accomplishments

- source-level provenance;
- two role-specific explanations from the same evidence;
- revision-safe Google Docs update;
- evaluation against misleading near-matches.

### What is next

Add enterprise identity, Jira/Confluence/GitLab sources, deployment evidence, organization-level governance, and durable Mistral Workflows.

## Compliance sentence

“All model inference, transcription, and embeddings in DriftGuard are powered exclusively by Mistral APIs.”
