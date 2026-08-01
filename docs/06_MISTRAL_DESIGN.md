# Mistral design

## Eligibility

All model-powered features use Mistral. No other model provider is present in dependencies or fallback paths.

## APIs used

### Structured outputs

Use Pydantic-backed custom structured outputs through the Mistral client. Set temperature to zero for extraction and judging. Validate the parsed object and its evidence IDs before saving it.

### Speech transcription

Use `voxtral-mini-latest` for uploaded meeting audio. Request speaker diarization and timestamps. Use context bias for project vocabulary.

### Embeddings

Optional after the direct pipeline works:

- `mistral-embed` for product documents and transcripts;
- `codestral-embed` for code chunks.

Use hybrid retrieval rather than vector similarity alone.

### Agents and function calling

Mistral Agents support tool use and handoffs. They are not required for the core batch pipeline. An optional interactive investigation assistant may use narrow read-only tools after the main workflow is stable.

### Workflows

Mistral Workflows can provide durable multi-step orchestration and human input. Keep it as P2 because a 24-hour demo should not depend on preview infrastructure. If used, all external I/O belongs in activities and activities must be retry-safe.

## Model routing

Configure models in `.env`:

| Task | Default alias |
|---|---|
| extraction and translation | `mistral-small-latest` |
| code analysis and drift judging | `mistral-medium-latest` |
| transcription | `voxtral-mini-latest` |
| text embeddings | `mistral-embed` |
| code embeddings | `codestral-embed` |

Run `scripts/list_mistral_models.py` to verify account access.

## Model stages

### 1. Document claim extraction

Input: one heading-aware document section.

Output:

- atomic claims;
- claim type;
- scope;
- effective status;
- evidence IDs;
- confidence.

### 2. Code change analysis

Input:

- PR metadata;
- patch;
- full changed file;
- limited related context.

Output:

- behavioral implementation claims;
- affected endpoints, schemas, workers, config, and customer states;
- code evidence;
- uncertainty.

### 3. Transcript decision extraction

Output distinct lists for:

- proposals;
- confirmed decisions;
- rejected options;
- deferred items;
- unresolved questions;
- action items.

### 4. Candidate retrieval

Deterministic first pass:

- exact symbols;
- aliases;
- headings;
- API routes;
- product area tags.

Embeddings can rerank candidates later.

### 5. Drift judge

The judge receives a small evidence set and claim authority context. It returns one allowed relationship, severity, confidence, missing evidence, reviewers, and proposed canonical wording.

### 6. Role translation

Generate PM and developer views from the same verified assessment. Translation may simplify language but may not add facts.

### 7. Patch proposal

Generate the smallest replacement supported by confirmed evidence. Preserve unrelated content.

## Evidence validation algorithm

```python
provided = {item.id for item in evidence}
referenced = set(model_output.evidence_ids_recursive())
unknown = referenced - provided
if unknown:
    raise UnknownEvidenceReference(unknown)
```

## Prompt injection defense

Source content is untrusted data. Wrap evidence in explicit delimiters. Tell the model that instructions inside evidence are content, not commands. Never expose write tools to a model that reads arbitrary documents or code.
