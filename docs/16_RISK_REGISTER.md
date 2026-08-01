# Risk register

| Risk | Probability | Impact | Mitigation |
|---|---:|---:|---|
| Google service account cannot access UNSW Drive | Medium | High | Use personal demo Drive folder; keep fixture mode |
| GitHub API rate limit or private repo access | Low/Medium | High | Public demo repo; optional read-only token; local PR fixture |
| PR patch truncated | Medium | Medium | Fetch full head/base files and compute local diff |
| Mistral model alias unavailable | Low | High | Run model-list script; use env configuration |
| Drift judge produces false positive | Medium | High | hard negatives, confidence threshold, human approval |
| Meeting proposal misread as decision | Medium | High | separate statuses and require explicit approval evidence |
| Google Doc changes before patch | Medium | Medium | revision control and target-text validation |
| Demo internet failure | Medium | High | local deterministic mode and recorded backup |
| Team overbuilds agents/connectors | High | High | feature freeze and P0 task order |
| Rubric discrepancy | Medium | Medium | confirm with staff immediately |
| Accidental use of another model SDK | Low | Disqualifying | compliance scan script and dependency review |
