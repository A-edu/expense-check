# 01 Rules engine

## Goal

Decide, deterministically and only from the policy file, which rules each expense line breaks.

## Scope

- In: `app/policy.json`, `app/rules.py`, `tests/test_rules.py`.
- Out: no model calls, no storage, no web, no network. Standard library only.

## Contracts

**Expense line**

| Field | Type | Rule |
|---|---|---|
| description | str | Free text |
| category | str | `meal`, `taxi`, `hotel` or `other` |
| amount | number | Total in SAR, finite, greater than 0 |
| people | int | At least 1, default 1 |
| nights | int | At least 1, default 1 |
| has_receipt | bool | A real boolean, default false |

**Flag:** `rule_id`, `severity` (`violation` or `review`), `message` (a sentence with the
numbers and the rule id).

**Functions**

- `load_policy(path=None)`: loads the policy; raises `ValueError` on duplicate ids, unknown
  rule types, or a missing limit.
- `check_line(line, policy)`: returns the flags for one line; raises `ValueError` on invalid input.
- `check_claim(lines, policy)`: returns `policy_version`, the validated lines with `flags`,
  `total`, `violation_count`, `review_count`.

**Policy (version 2026-11-v1)**

| Id | Rule |
|---|---|
| MEAL-01 | Meal at most 150 SAR per person |
| TAXI-01 | Taxi at most 100 SAR per line |
| HOTEL-01 | Hotel at most 600 SAR per night |
| RCPT-01 | Any line above 50 SAR needs a receipt |
| CAT-01 | Category "other" goes to manual review (severity review) |

No limit or rule id may be hard-coded in `rules.py`.

## Acceptance criteria

- **Pitch example:** Given dinner for 3 people, 620 SAR, no receipt, when checked, then the
  flags are exactly MEAL-01 and RCPT-01.
- **Boundary, inclusive limits:** Given a meal of 450 SAR for 3 people, then no flag.
  Given 450.01 SAR for 3 people, then MEAL-01.
- **Boundary, per night:** Given a hotel of 1800 SAR for 3 nights, then no flag. Given
  1800.01 SAR, then HOTEL-01.
- **Receipt:** Given 50 SAR without a receipt, then no flag. Given 50.01 SAR without a receipt,
  then RCPT-01. Given an over-limit line with a receipt, then only the limit flag.
- **Review:** Given category "other", then CAT-01 with severity review.
- **Defaults:** Given a line with no `people`, `nights` or `has_receipt`, then it is checked
  as 1 person, 1 night, no receipt, and `check_claim` returns those values filled in.
- **Failure:** Given an unknown category, amount 0 or below, NaN or infinite amount,
  people or nights below 1, or `has_receipt` that is not a boolean, then `ValueError`.
- **Policy-driven:** Given the meal limit changed in the policy, then the result changes
  with no code change.

## Verification

- 33 tests pass (`python -m pytest tests/test_rules.py`).
- `python -m app.rules` prints MEAL-01 and RCPT-01 for the pitch example.
- 19 bugs planted one at a time; all that affect a flag are caught. One surviving bug changes
  only the wording of a flag message.

## Change log

- 2026-11-17: First version (prompt 01).
- 2026-11-17: Compare totals without rounding first; stricter validation; return validated
  lines; reject bad policies at load time (prompt 01a).
