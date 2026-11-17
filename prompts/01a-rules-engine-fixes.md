# 01a Rules engine fixes

- **Date:** 2026-11-17
- **Spec:** [specs/01-rules-engine.md](../specs/01-rules-engine.md)
- **Follows:** [01-rules-engine.md](01-rules-engine.md)
- **Agent:** (fill in the tool and model used)

## Prompt

```
In expense-check, change app/rules.py and tests/test_rules.py only.

1. Limit comparison. In max_per_person and max_per_night, do not round before
   comparing. Flag when round(amount, 2) > round(limit * people, 2)
   (or limit * nights). Keep the rounded per-person / per-night figure for the
   message only.
2. Validation. If has_receipt is present it must be a real bool, otherwise
   raise ValueError. A missing has_receipt still defaults to False.
   Reject NaN and infinite amounts with ValueError (math.isfinite).
3. check_claim returns each line in its validated form (all six fields, with
   defaults filled in) plus "flags", instead of the original dict.
4. load_policy raises ValueError if a rule's type is not one of the five known
   types, or if any rule other than manual_review lacks a numeric limit.
5. Add tests:
   - meal 450.01 for 3 people -> MEAL-01
   - meal 1050.03 for 7 people -> MEAL-01; meal 1050 for 7 -> no flag
   - hotel 1800.01 for 3 nights -> HOTEL-01
   - meal 300 with no "people" key -> MEAL-01
   - taxi 120 with no "people" or "nights" keys -> TAXI-01 only
   - amount 90 with no "has_receipt" key -> RCPT-01
   - has_receipt "false" (string) -> ValueError
   - amount NaN -> ValueError; amount infinity -> ValueError
   - check_claim output line includes people and nights when the input
     omitted them
   - load_policy rejects an unknown rule type and a missing limit

Do not change anything else. Keep all limits and rule ids out of rules.py.
```

## Result

- Commits `47e3068` and `721077d`. 33 tests passed.
- Every edge case from the 01 review now behaves correctly.
- One planted bug still survives: it changes only the wording of a flag message (the
  per-person figure in the text), never whether a line is flagged. Accepted for now.
