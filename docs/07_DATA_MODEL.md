# Data model

## Conceptual model

```mermaid
erDiagram
    PROJECT ||--o{ ARTIFACT : contains
    ARTIFACT ||--o{ EVIDENCE_SPAN : has
    PROJECT ||--o{ CLAIM : has
    CLAIM }o--o{ EVIDENCE_SPAN : grounded_by
    CLAIM ||--o{ CLAIM_RELATION : left
    CLAIM ||--o{ CLAIM_RELATION : right
    PROJECT ||--o{ DECISION : has
    PROJECT ||--o{ DRIFT_ALERT : has
    DRIFT_ALERT ||--o{ CHANGE_PROPOSAL : creates
    CHANGE_PROPOSAL ||--o{ AUDIT_EVENT : records
```

## Core records

### Artifact

- source type
- external ID
- URI
- title
- version or commit SHA
- content hash
- observed time
- raw normalized content

### EvidenceSpan

- stable ID
- artifact ID
- locator type
- start/end locator
- exact excerpt
- hash

### Claim

- subject
- predicate
- object/statement
- claim type
- scope
- status
- confidence
- effective dates
- evidence IDs

### Decision

- statement
- status
- owner
- approvers
- alternatives
- conditions
- timestamp evidence

### DriftAlert

- relationship
- severity
- confidence
- concise reason
- conflicting claim IDs
- missing evidence
- recommended reviewers
- status

### ChangeProposal

- target document
- expected revision
- patch operations
- PM explanation
- developer explanation
- approval status

### AuditEvent

- actor
- action
- object
- timestamp
- evidence/model/prompt metadata

## SQLite schema

See `schemas/db.sql`.

## Pydantic schemas

See `apps/api/app/domain/schemas.py`.
