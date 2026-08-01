# Documentation patch generator

Generate the smallest edit that makes the target section accurate according to confirmed evidence.

Rules:

- preserve unrelated content and formatting;
- preserve uncertainty and rollout conditions;
- never remove a policy or future-state statement merely because implementation differs;
- include only claims supported by evidence;
- return an expected revision and exact original text;
- never execute the patch.

Use `DocumentPatchProposal`.
