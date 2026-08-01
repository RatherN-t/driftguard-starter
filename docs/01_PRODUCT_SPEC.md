# Product specification

## Persona

### Primary user: product manager

A PM responsible for a software feature who needs to answer:

- What changed in the implementation?
- Does it alter customer behavior or scope?
- Does it match the approved decision?
- Which shared document is now misleading?
- Which developer should validate the interpretation?

### Counterpart: developer or technical lead

The developer needs:

- accurate file, symbol, endpoint, schema, and configuration evidence;
- a clear statement of the stale claim;
- protection against product documents being rewritten incorrectly;
- a focused review rather than a generic “please review everything.”

## Core jobs to be done

1. When a meaningful pull request changes behavior, show the PM what changed without forcing them to read the code.
2. When a document conflicts with implementation or a confirmed decision, show the developer exactly why.
3. When evidence is incomplete, say so rather than producing a polished false answer.
4. When both parties agree, update the shared document safely and record why it changed.

## User stories

- As a PM, I can import the project documents I already use.
- As a developer, I can paste a pull-request URL instead of installing an enterprise app.
- As a PM, I can read a plain-language impact statement.
- As a developer, I can inspect exact code evidence.
- As either reviewer, I can reject a false positive and explain why.
- As a document owner, I can approve a minimal patch with revision protection.
- As a new teammate, I can see the decision and evidence history.

## Success metrics

For the hackathon demo:

- 100% of displayed factual claims link to evidence.
- The seeded stale-documentation case is detected.
- At least three seeded non-contradictions do not produce high-severity alerts.
- A PM can explain the change after reading the PM view.
- A developer can identify the affected files without opening the full repository.
- No write occurs without approval.

## Non-goals

- Proving that merged code is correct.
- Automatically changing production code.
- Fully indexing an enterprise repository.
- Replacing product managers, developers, or architecture review.
- Supporting every collaboration platform.
