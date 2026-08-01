# API contracts

Base path: `/api`

## System

### `GET /health`

Returns process health.

### `GET /api/config/status`

Returns booleans indicating which integrations are configured. Never returns secrets.

## Sources

### `POST /api/sources/google/sync`

```json
{
  "folder_id": "optional-override"
}
```

Returns imported artifacts and changed/unchanged counts.

### `POST /api/sources/github/pr`

```json
{
  "url": "https://github.com/org/repo/pull/42"
}
```

Returns an ingestion job or normalized PR artifact.

### `POST /api/sources/transcript/text`

Accepts pasted transcript text.

### `POST /api/sources/transcript/audio`

Multipart upload. Returns transcription job/result.

## Analysis

### `POST /api/analysis/run`

```json
{
  "document_url": "https://docs.google.com/document/d/document-id/edit",
  "repository_url": "https://github.com/org/repository",
  "pull_request_url": "https://github.com/org/repository/pull/42",
  "transcript_text": "[00:00] Speaker: Optional timestamped transcript.",
  "use_demo_transcript": false
}
```

Validates that the repository and PR match, reads the linked sources, runs extraction/retrieval/drift
classification, and returns the alert together with exact source IDs, source versions, transcript
decisions, and the complete document before/proposed view. Live source analysis requires Mistral;
demo source analysis uses the visibly labelled deterministic fixture path.

### `GET /api/analysis/current`

Returns the active linked-source analysis. Before the first explicit run it returns the labelled demo
workspace. Review state and applied document content are refreshed from durable state.

### `GET /api/alerts`

Filters by severity, relation, status, or source.

### `GET /api/alerts/{id}`

Returns:

- alert;
- claims;
- evidence;
- role explanations;
- proposal;
- audit history.

### `GET /api/alerts/{id}/document-change`

Returns the exact source URI, patch target, full source content, full proposed content, and—after a
successful apply—the actual local content written. Live Google Docs mode returns the linked section
and revision-controlled target.

## Review

### `POST /api/alerts/{id}/approve`

```json
{
  "edited_replacement_text": null,
  "send_notifications": true
}
```

Approval does not automatically write unless the route is configured to call apply in the same transaction.

### `POST /api/alerts/{id}/reject`

```json
{
  "reason_code": "future_state_documentation",
  "comment": "This section intentionally describes the next release."
}
```

### `POST /api/alerts/{id}/apply`

Requires an approved proposal. Revalidates document revision and target content.

## Demo

### `POST /api/demo/reset`

Restores deterministic fixtures.

### `POST /api/demo/load`

Loads the included project without external credentials.

## Error format

```json
{
  "error": {
    "code": "DOCUMENT_REVISION_CONFLICT",
    "message": "The document changed after this proposal was generated.",
    "retryable": true,
    "details": {}
  }
}
```
