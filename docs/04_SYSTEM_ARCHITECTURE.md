# System architecture

## Architecture diagram

```mermaid
flowchart LR
    GD[Google Drive + Docs] --> ING[Ingestion adapters]
    GH[GitHub PR URL] --> ING
    AU[Audio upload] --> VX[Mistral Voxtral]
    VX --> ING
    ING --> EV[Evidence registry]
    EV --> EX[Claim and decision extraction]
    EX --> RET[Candidate retrieval]
    RET --> J[Drift judge]
    J --> TR[Role translation]
    TR --> PA[Patch proposal]
    PA --> UI[Human review UI]
    UI -->|approve| WR[Google Docs write]
    UI -->|reject| FB[Feedback + audit]
    WR --> EM[Email/preview]
```

## Components

### Frontend

Next.js application containing:

- source setup;
- sync/analyze controls;
- drift inbox;
- alert review;
- product/developer toggle;
- evidence drawer;
- patch diff;
- decision log;
- approval actions.

### Backend

FastAPI application containing:

- integration adapters;
- source normalization;
- evidence registry;
- Mistral gateway;
- retrieval and drift pipeline;
- write safety;
- audit store.

### Persistence

Use SQLite for the hackathon. Keep repository interfaces so PostgreSQL can replace it later.

Persist:

- source metadata and hashes;
- evidence spans;
- claims;
- claim relationships;
- decisions;
- alerts;
- proposals;
- approvals;
- audit events.

Raw audio and large artifacts can stay on local disk for the demo.

## Core pipeline

```mermaid
sequenceDiagram
    actor User
    participant API
    participant Docs as Google Docs
    participant GitHub
    participant Mistral
    participant DB

    User->>API: Sync folder / Analyze PR
    API->>Docs: Read documents and revision IDs
    API->>GitHub: Read PR, patch, full files
    API->>DB: Store artifacts and evidence
    API->>Mistral: Extract document claims (schema)
    API->>Mistral: Extract code claims (schema)
    API->>API: Validate evidence IDs
    API->>API: Retrieve candidate claim pairs
    API->>Mistral: Classify drift (schema)
    API->>Mistral: Generate role views and patch
    API->>DB: Store pending proposal
    API-->>User: Show evidence and proposed update
    User->>API: Approve
    API->>Docs: Re-fetch and verify revision
    API->>Docs: batchUpdate
    API->>DB: Audit applied change
```

## Why not one agent

The application uses separate calls because each stage has a different failure mode and test:

- extraction accuracy;
- retrieval recall;
- contradiction precision;
- role translation quality;
- patch grounding.

This is more trustworthy and technically defensible than one autonomous prompt with broad tools.

## Optional Mistral Workflows path

Mistral Workflows can later orchestrate the same stages durably. External I/O and model calls should be activities; workflow code must remain deterministic and activities must be retry-safe. This is an enhancement, not a blocker for the first demo.
