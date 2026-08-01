# Test and evaluation plan

## Unit tests

- GitHub PR URL parsing
- Google Docs text/range extraction
- evidence ID generation
- unknown evidence ID rejection
- file filtering
- revision conflict handling
- approval required before write
- notification deduplication
- relation enum validation

## Integration tests

- demo documents → extracted claims
- demo PR → implementation claims
- seeded pair → stale-documentation alert
- approved proposal → local fixture update
- rejected proposal → no write
- configured Google Docs sandbox → real update and revision increment

## Evaluation cases

Use `evals/gold_cases.jsonl`.

Include hard negatives:

- future-state documentation versus current code;
- code behind a disabled feature flag;
- rejected meeting proposal;
- renamed component with unchanged behavior;
- test-only code change;
- formatting-only document edit;
- implementation bug that should not rewrite approved product intent.

## Metrics

- extraction precision by claim type;
- candidate retrieval recall;
- actionable drift precision;
- false-positive rate on hard negatives;
- decision-status accuracy;
- citation coverage;
- patch grounding;
- median analysis time;
- model cost per run.

## Hackathon acceptance targets

- 8/8 schema-valid outputs on demo evaluation set;
- 100% evidence coverage;
- correct relation on the main demo case;
- no high-severity false alert in at least three hard negatives;
- zero unapproved writes.

## Human test

Ask one PM-like user and one developer:

1. What changed?
2. Why does it matter?
3. Which source proves it?
4. Would you approve the wording?

Record time and confusion points.
