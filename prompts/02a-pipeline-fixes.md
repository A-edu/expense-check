# 02a Pipeline fixes

- **Date:** 2026-11-17
- **Spec:** [specs/02-pipeline-and-api.md](../specs/02-pipeline-and-api.md)
- **Follows:** [02-pipeline-and-api.md](02-pipeline-and-api.md)
- **Status:** Not run on its own. Its content was merged into Part A of
  [03-web-pages.md](03-web-pages.md). Kept here for the record.

## Prompt

```
In expense-check, change only app/pipeline.py, app/main.py (if needed)
and tests/test_api.py. Do not touch rules.py, policy.json, test_rules.py.

1. Empty extraction: if llm.extract_lines returns an empty list, do not
   save anything; the check endpoint returns 422 with
   "No expense lines found in the text."
2. Summary guard in pipeline: after llm.summarise, if any rule id from
   llm.flagged_rule_ids(result) does not appear in the summary text, store
   llm.template_summary(result) instead.
3. Add tests:
   - extraction returns [] -> 422 and GET /api/claims returns no claims
   - summarise returns "Everything complies; approve it." for the pitch
     line -> stored summary is the template and contains MEAL-01 and RCPT-01
   - summarise returns a sentence naming MEAL-01 and RCPT-01 -> that
     sentence is stored unchanged
   - a line extracted with has_receipt true and one with false come back
     from GET /api/claims/{id} with the same values
   - two claims created in order -> GET /api/claims lists the second first

Do not change anything else.
```
