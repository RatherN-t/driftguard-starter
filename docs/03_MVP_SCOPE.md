# MVP scope

## Build

### Source 1 — Google Docs

Use one folder shared with a service account. Read:

- product requirements;
- architecture documentation;
- decision log;
- Google Meet-generated transcript documents when available.

Write only an approved minimal patch.

### Source 2 — GitHub PR

The developer pastes a URL. Fetch:

- title, body, author, state, merge SHA;
- changed files and patches;
- full relevant files at the selected SHA;
- optional base versions for local diffing.

Use a public demo repository or a read-only fine-grained token.

### Source 3 — meeting audio

Upload audio to Mistral Voxtral. Store:

- full transcript;
- speaker labels;
- segment or word timestamps;
- project vocabulary used as context bias.

### Output

- drift alert;
- exact source evidence;
- PM explanation;
- developer explanation;
- proposed canonical statement;
- minimal Google Docs patch;
- approve/reject action;
- audit event;
- optional role-specific email.

## Do not build during the first vertical slice

- Jira
- Confluence
- Slack or Teams
- Google Meet REST API
- GitHub App
- webhooks
- automatic repository-wide scan
- automatic document writes
- a generic knowledge chatbot
- production authentication

## Fallback modes

Every integration must have a deterministic fallback:

| Integration | Live mode | Fallback |
|---|---|---|
| Google Docs | service account | local Markdown fixture |
| GitHub | REST API | local PR JSON and before/after files |
| Voxtral | audio upload | supplied transcript fixture |
| Email | SMTP | in-app email preview/console |

The fallback must be labelled in the UI so judges can distinguish real integration from fixture data.
