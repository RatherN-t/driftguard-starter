# Data ingestion

## Google Drive and Docs

### Hackathon authentication

Use a service account:

1. Create a Google Cloud project.
2. Enable Drive API and Docs API.
3. Create a service account.
4. Save its credential JSON under `secrets/`.
5. Share the demo folder with the service-account email.
6. Start with viewer permission; add editor permission only for write-back.

If an organizational domain blocks the share, use a personal Google account for the demo folder.

### Folder sync

Use Drive `files.list` with a parent-folder query. Store:

- file ID;
- name;
- MIME type;
- modified time;
- version/revision metadata;
- browser link.

Use a manual Sync button. Do not build push notifications first.

### Document reading

Use Docs `documents.get`. Traverse structural elements and preserve:

- paragraph text;
- heading/style;
- start and end indexes;
- document revision ID.

Chunk by heading. Generate evidence IDs from source ID, revision, and character range.

Example:

```text
gdoc:architecture-doc:rev-19:120-288
```

### Document write

Use `documents.batchUpdate` with `writeControl.requiredRevisionId`.

Before writing:

- re-fetch the document;
- verify revision;
- verify original text at target indexes;
- apply delete/insert operations;
- abort safely on conflict.

## GitHub

### Input

Accept only canonical PR URLs:

```text
https://github.com/{owner}/{repo}/pull/{number}
```

Validate host and path. Reject arbitrary URLs.

### Read flow

1. Get PR metadata.
2. Confirm the selected state and SHA.
3. List changed files.
4. Filter files.
5. Fetch full important files at head or merge SHA.
6. Optionally fetch base files and compute a local unified diff.

### File filters

Ignore by default:

- lockfiles;
- generated files;
- vendor directories;
- minified assets;
- binaries;
- snapshots;
- files over configured size.

Prefer:

- API handlers;
- services;
- schemas;
- models;
- migrations;
- configuration;
- tests that reveal behavior;
- documentation.

### Evidence

A code evidence ID must encode repository, SHA, path, and line range.

```text
github:team/repo:abc123:src/payments/api.py:40-67
```

## Audio and transcripts

Preferred path:

- upload an audio file;
- call `audio.transcriptions.complete` using `voxtral-mini-latest`;
- request diarization and timestamps;
- add project-specific context bias terms.

Alternative:

- enable Google Meet transcription;
- move the generated transcript Google Doc into the project folder;
- process it through the normal Docs adapter.

Fallback:

- upload or paste plain transcript text.

## Normalization

Convert every source into:

```text
Artifact
  └── EvidenceSpan[]
        └── source type, URI, version, locator, content, observed time
```

Models never receive an unlabelled blob. Every evidence block has a stable ID.
