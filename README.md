# Expense Check — rules engine

Checks expense lines against `app/policy.json`. Python 3.11+, stdlib only; `pytest` is the
only dependency. No web framework, database, LLM or network.

## Tests

    python -m pip install -r requirements.txt
    python -m pytest

## Demo

    python -m app.rules

Prints the claim for one line ("Dinner for 3", 620 SAR, no receipt) as indented JSON,
flagging MEAL-01 and RCPT-01.

Rule ids and limits live in `app/policy.json`; `app/rules.py` hard-codes none of them.
