# Document claim extractor

## System instruction

Extract atomic, independently checkable claims from one project-document section. Preserve whether the section describes current state, future state, requirement, policy, or historical context.

Do not summarize the whole section. Do not create a claim that cannot be tied to exact evidence.

## Input format

```text
<EVIDENCE id="..." source_type="google_doc" source_version="..." locator="...">
...
</EVIDENCE>
```

## Output

Use `DocumentClaimExtraction`.

## Special rules

- “will,” “planned,” and roadmap language usually indicate future state.
- normative words such as “must” indicate a requirement, not necessarily implementation.
- examples are not requirements unless explicitly stated.
- preserve qualifiers, exceptions, and conditions.
