# UI and UX specification

## Design principle

Do not make chat the main experience. The product is a review surface for shared truth.

## Screen 1 — project setup

Cards:

- Google Drive folder status
- GitHub PR URL input
- meeting audio/text upload
- Mistral connection status
- demo mode

Primary action: **Build alignment view**

## Screen 2 — drift inbox

Each alert card shows:

- relation and severity;
- one-line PM impact;
- source pair;
- confidence;
- requested reviewers;
- status.

Filters:

- stale docs;
- undocumented implementation;
- unimplemented decision;
- ambiguous;
- resolved.

## Screen 3 — alert review

Three-column desktop layout:

1. **What the document says**
2. **What changed / was decided**
3. **Proposed shared wording**

Top toggle:

- Product view
- Developer view

Evidence drawer:

- exact excerpt;
- file/line or document section;
- commit SHA or revision;
- transcript timestamp;
- source link.

Actions:

- Approve and update
- Edit proposal
- Reject
- Mark intentional exception
- Need more evidence

## Screen 4 — decision log

Timeline with:

- proposed/confirmed/rejected status;
- speaker and timestamp;
- decision owner;
- linked PR/doc;
- superseded decisions;
- unresolved conditions.

## Copy principles

Product view:

- state behavior and impact first;
- define unavoidable technical terms;
- avoid implementation trivia.

Developer view:

- name files, symbols, routes, flags, and schemas;
- state what the document currently gets wrong;
- preserve uncertainty.

## Demo polish

- source badges with recognizable icons;
- a visible evidence count;
- confidence shown as language and number;
- smooth transition from analysis to review;
- a clear success state opening the updated document;
- no fake “AI typing” animation.
