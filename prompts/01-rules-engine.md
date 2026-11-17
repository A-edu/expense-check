# 01 Rules engine

- **Date:** 2026-11-17
- **Spec:** [specs/01-rules-engine.md](../specs/01-rules-engine.md)
- **Agent:** (fill in the tool and model used)

## Prompt

```
Build the rules engine for "Expense Check", a small app that checks expense
lines against a written policy. This task is ONLY the rules engine: no web
framework, no database, no LLM calls, no network access.

STACK
- Python 3.11+, standard library only. pytest is the only dependency.

FILES TO CREATE (and nothing else)
expense-check/
  app/__init__.py
  app/policy.json
  app/rules.py
  tests/test_rules.py
  requirements.txt        (pytest only)
  README.md               (how to run the tests and the demo, under 20 lines)

DATA CONTRACT
An expense line is a dict:
  description  str    free text, e.g. "Dinner for 3"
  category     str    one of: "meal", "taxi", "hotel", "other"
  amount       float  total for the line, in SAR
  people       int    default 1
  nights       int    default 1
  has_receipt  bool

A flag is a dict:
  rule_id   str   e.g. "MEAL-01"
  severity  str   "violation" or "review"
  message   str   plain sentence that includes the numbers and the rule id

POLICY FILE (app/policy.json)
{
  "version": "2026-11-v1",
  "currency": "SAR",
  "rules": [
    {"id": "MEAL-01",  "type": "max_per_person",        "category": "meal",  "limit": 150},
    {"id": "TAXI-01",  "type": "max_per_line",          "category": "taxi",  "limit": 100},
    {"id": "HOTEL-01", "type": "max_per_night",         "category": "hotel", "limit": 600},
    {"id": "RCPT-01",  "type": "receipt_required_above", "category": "*",    "limit": 50},
    {"id": "CAT-01",   "type": "manual_review",         "category": "other"}
  ]
}
Add a short "text" field to each rule stating it in one sentence.

FUNCTIONS (app/rules.py)
- load_policy(path=None) -> dict
    Loads app/policy.json by default. Raises ValueError if rule ids are not unique.
- check_line(line, policy) -> list of flags
    Applies every rule whose category matches the line ("*" matches all).
    Limits are inclusive: an amount exactly at the limit is allowed.
    MEAL-01 compares amount / people. HOTEL-01 compares amount / nights.
    RCPT-01 flags a line with has_receipt false and amount above the limit.
    CAT-01 returns a flag with severity "review"; all others are "violation".
- check_claim(lines, policy) -> dict with keys:
    policy_version, lines (each original line plus a "flags" list),
    total (sum of amounts), violation_count, review_count
- Validation: raise ValueError for an unknown category, amount <= 0,
  people < 1 or nights < 1.
- All limits and rule ids must come from the policy dict. Do not hard-code
  any limit or rule id in rules.py.
- Add an `if __name__ == "__main__":` block that runs check_claim on this one
  line and prints the result as indented JSON:
    {"description": "Dinner for 3", "category": "meal", "amount": 620,
     "people": 3, "nights": 1, "has_receipt": false}

TESTS (tests/test_rules.py)
Tests must build their own policy dict in a fixture, not read policy.json,
except one test that checks the shipped policy.json loads and has unique ids.
Cover at least:
- the demo line returns exactly MEAL-01 and RCPT-01
- meal at exactly 150 per person: no flag; at 150.01 per person: MEAL-01
- taxi at 100: no flag; at 101: TAXI-01
- hotel 1200 for 2 nights: no flag; 1300 for 2 nights: HOTEL-01
- amount 50 without receipt: no flag; 50.01 without receipt: RCPT-01
- over-limit line WITH a receipt returns only the limit flag
- category "other" returns CAT-01 with severity "review"
- each validation error case raises ValueError
- changing the meal limit in the policy dict changes the result
- check_claim totals and counts are correct for a three-line claim

STYLE
- Plain functions, type hints, no classes, no extra features, no CLI flags.
- Do not add anything not listed here.

When finished, list the files you created and the two commands to run:
the tests and the demo.
```

## Result

- Commit `4650dd6`. 21 tests passed; the demo printed MEAL-01 and RCPT-01; no limits or rule ids
  hard-coded in `rules.py`.
- 17 of 19 planted bugs were caught by the tests.
- Found in review:
  - The per-person and per-night figures were rounded before comparing, so slightly
    over-limit lines passed (450.01 SAR for 3 people under a 150 cap).
  - `has_receipt: "false"` (a string) counted as having a receipt.
  - NaN and infinite amounts passed validation.
  - Default values for `people` and `has_receipt` were untested.
  - `check_claim` returned the original line, without filled-in defaults (a gap in this prompt).
  - A rule with a missing limit crashed at check time instead of at load time.
- Fixed by [01a](01a-rules-engine-fixes.md).
