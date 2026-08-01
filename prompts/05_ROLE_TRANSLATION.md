# Role translator

Generate two explanations from an already verified drift assessment.

## PM view

Answer:

- What changed?
- Why does it matter?
- What customer, scope, timeline, operational, or risk impact exists?
- What decision or confirmation is needed?

Avoid unnecessary implementation detail. Define unavoidable technical terms.

## Developer view

Answer:

- Which files, symbols, routes, schemas, or flags changed?
- Which documented claim is stale or uncertain?
- What exact review is needed?

Do not introduce evidence not present in the assessment.

## Output

Use `RoleSpecificExplanation`.
