# 03 Web pages

## Goal

Give staff a page to check and send a claim, and give the manager a page to review the queue
and decide, both built on the JSON API from spec 02.

## Scope

- In: `app/static/` (two HTML pages, shared CSS and JS), routes `/` and `/review`.
- Out: login, editing lines, resubmitting, history of decided claims.
- Stack: plain HTML, CSS and JavaScript calling the API with fetch. No framework or build step.

## Pages

**Submit a claim (`/`)**: name and expenses fields, "Check claim", the checked claim sheet,
"Send to manager", "Start a new claim".

**Review claims (`/review`)**: queue of submitted claims (newest first), the selected claim
sheet, a comment field, "Approve claim" and "Return claim".

**Claim sheet (shared)**: header with claim number, submitter, policy version and status;
one row per line (description, category, details, receipt, amount); each flag directly under
its line with the rule id; total and counts; the model's summary, labelled as written by the
model; the latest decision if any.

## Design rules

- Calm, precise finance tool. Public Sans, tabular numbers for amounts.
- Colour carries meaning only: red for violations, amber for review, green for compliant or
  approved, blue for actions.
- Sentence case, no all-caps labels, no gradients, no decorative animation.
- Keyboard focus always visible; every input labelled; status messages announced.
- Works down to 375px wide.

## Security

User text and model output are never inserted as HTML; only as text.

## Acceptance criteria

- **Happy path:** Given the three-line example, when Sara checks it, then the dinner and hotel
  lines show their rule tags underneath and the taxi line shows "Within policy".
- **Hand-off:** Given a checked claim, when Sara sends it, then its status reads "Waiting for
  review" and it appears at the top of Nora's queue.
- **Approval gate:** Given a claim in the queue, when Nora clicks "Return claim" with no
  comment, then an inline error appears and nothing is sent. With a comment, the claim leaves
  the queue and the confirmation names Sara.
- **Errors:** Given the model is down, then Sara sees "The model did not respond. Try again in
  a moment." Given the server is down, then "Could not reach the server. Is it running?"
- **Already decided:** Given a claim decided elsewhere, when Nora decides it, then "This claim
  was already decided." and the queue refreshes.
- **Empty states:** No claim yet on the staff page, and an empty queue, each show a short
  message saying what to do.
- **Injection in the page:** Given an expense description containing `<script>`, then it is
  shown as text and nothing runs.

## Verification

Pending: tests, browser walk-through, screenshots at desktop and phone width, keyboard pass.

## Change log

- 2026-11-17: First version (prompt 03).
