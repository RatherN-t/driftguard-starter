# Evaluations

`gold_cases.jsonl` contains positive cases and hard negatives.

The evaluation runner should:

1. construct evidence objects;
2. run extraction or use fixed atomic claims;
3. call the drift judge;
4. validate schema and evidence references;
5. compare expected relationship and actionability;
6. report confusion matrix, latency, and estimated API usage.

Do not tune only against the main demo case.
