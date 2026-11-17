# Expense Check

Turns a short expense text into a checked claim. Gemini extracts the lines, the rules
engine in `app/rules.py` decides compliance against `app/policy.json`, and the result is
stored in SQLite and served over a JSON API. Python 3.11+.

## Setup

    python3.11 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    cp .env.example .env

Fill `.env` with your key and model name:

    GEMINI_API_KEY=your-key-here
    GEMINI_MODEL=your-flash-model-name
    EXPENSE_CHECK_DB=expense_check.db

`GEMINI_API_KEY` and `GEMINI_MODEL` are read from the environment; none is hard-coded.
If either is missing the server still starts and the check endpoint answers 503.
`EXPENSE_CHECK_DB` is the SQLite file, created on startup if missing.

## Tests

    python -m pytest

The API tests use a temporary database and fake the model, so no network is needed.

## Run the server

    uvicorn app.main:app --reload

Then open <http://localhost:8000/> to submit a claim and <http://localhost:8000/review> to
work the review queue. Both pages are plain HTML in `app/static/` and talk to the JSON API.

## Send the pitch example

    curl -s -X POST localhost:8000/api/claims/check \
      -H 'content-type: application/json' \
      -d '{"text": "Dinner for 3 people, 620 SAR, no receipt.", "submitted_by": "abdulaziz"}'

The response is a draft claim flagged with MEAL-01 and RCPT-01.

## API

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/api/claims/check` | Extract, check and summarise the text; stores a draft |
| POST | `/api/claims/{id}/submit` | Move a draft to submitted |
| GET | `/api/claims?status=submitted` | List claims, newest first, without lines |
| GET | `/api/claims/{id}` | One claim with its lines, flags and decisions |
| POST | `/api/claims/{id}/decision` | `approve` or `return` a submitted claim |

A claim's status is one of `draft`, `submitted`, `approved`, `returned`. Flags and counts
come only from the rules engine; the model never sets them.

## Demo

    python -m app.rules

Prints the checked claim for one line ("Dinner for 3", 620 SAR, no receipt) as indented
JSON, flagging MEAL-01 and RCPT-01.

Rule ids and limits live in `app/policy.json`; `app/rules.py` hard-codes none of them.
