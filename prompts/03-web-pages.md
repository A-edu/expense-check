# 03 Web pages (and pending backend fixes)

- **Date:** 2026-11-17
- **Spec:** [specs/03-web-pages.md](../specs/03-web-pages.md), plus the open items in
  [specs/02-pipeline-and-api.md](../specs/02-pipeline-and-api.md)
- **Agent:** (fill in the tool and model used)

## Prompt

```
Extend the expense-check repository with two web pages, plus a few small
backend fixes. Do NOT modify app/rules.py, app/policy.json or
tests/test_rules.py.

PYTHON VERSION
All code must run on Python 3.9: no "X | Y" type unions, no match
statements. Use Optional/Union from typing.

PART A - BACKEND FIXES
1. Add pytest.ini at the repo root:
     [pytest]
     pythonpath = .
     testpaths = tests
2. app/pipeline.py: if llm.extract_lines returns an empty list, save
   nothing and make the check endpoint return 422 with
   "No expense lines found in the text."
3. app/pipeline.py: after llm.summarise, if any rule id from
   llm.flagged_rule_ids(result) is missing from the summary text, store
   llm.template_summary(result) instead.
4. Add to tests/test_api.py:
   - extraction returns [] -> 422 and GET /api/claims returns no claims
   - summarise returns "Everything complies; approve it." for the pitch
     line -> stored summary is the template and contains MEAL-01 and RCPT-01
   - summarise returns a sentence naming MEAL-01 and RCPT-01 -> stored
     unchanged
   - one line with has_receipt true and one false come back from
     GET /api/claims/{id} with the same values
   - two claims created in order -> GET /api/claims lists the second first
   - GET / and GET /review return 200 HTML

PART B - PAGES
Plain HTML, CSS and vanilla JavaScript that call the existing JSON API
with fetch. No frontend framework, no build step, no npm.

Files:
  app/static/staff.html
  app/static/review.html
  app/static/styles.css   (shared)
  app/static/app.js       (shared helpers, including the claim renderer)
In app/main.py: serve staff.html at GET /, review.html at GET /review,
and mount app/static at /static.

SECURITY
Model output and user text must never be inserted with innerHTML.
Build elements with createElement and set textContent.

VISUAL DESIGN
Subject: an internal tool for checking expense claims against a written
policy. It should feel calm, precise and current, like a well-made
finance tool, not a template.
- Font: "Public Sans" from Google Fonts (weights 400, 500, 600), with
  system-ui as fallback. Use font-variant-numeric: tabular-nums for every
  amount. One family only.
- Colours as CSS variables:
    --page    #F3F5F7   page background
    --paper   #FFFFFF   the claim sheet
    --ink     #17212B   main text
    --muted   #5B6573   secondary text
    --rule    #DDE2E8   hairlines and borders
    --action  #2348C9   primary buttons, links, focus ring
    --breach  #B42318   violations
    --review  #8A5A00   items needing review
    --ok      #1E6B45   approved, compliant
  Use each colour only for its meaning.
- Type scale: 14px small, 16px body, 20px section heading, 28px page
  title. Sentence case everywhere. No all-caps labels, no labels above
  every heading, no arrows in button text, no emoji.
- Layout: max width 1120px, generous whitespace, 8px spacing grid.
  Corners: 6px on inputs and buttons, 10px on the claim sheet. One soft
  shadow, on the claim sheet only. No gradients, no decorative animation;
  respect prefers-reduced-motion.
- Visible keyboard focus (2px --action outline). All inputs have labels.
  Status messages use aria-live="polite".
- Responsive down to 375px: columns stack; claim rows become stacked
  blocks with the amount on its own line.

SHARED HEADER
"Expense Check" on the left. On the right, a two-option switch:
"Submit a claim" (/) and "Review claims" (/review); the current page is
shown as selected (aria-current="page").

THE CLAIM SHEET (shared renderer in app.js, used on both pages)
A white sheet showing one claim:
- Top: claim number, submitted by, policy version, and a status pill
  (Draft, Waiting for review, Approved, Returned) in the matching colour.
- A table: Description | Category | Details | Receipt | Amount.
  Category shown as Meal / Taxi / Hotel / Other.
  Details: "3 people" or "2 nights"; blank when both are 1.
  Receipt: "Yes" or "Missing" (Missing in --breach when that line has
  RCPT-01).
  Amount right-aligned, "620.00 SAR".
- Directly under each line that has flags: one row per flag with the
  rule id in a small outlined tag and the message, in --breach for
  violations and --review for review items. Lines without flags show a
  small "Within policy" in --ok.
- Footer row: total, plus "2 violations, 0 for review" (or
  "No issues found" in --ok).
- Below the table: "Summary" heading and the summary text, with a muted
  note "Written by the model from the flags above."
- If the claim has decisions, show the latest: "Returned on <date>:
  <comment>" or "Approved on <date>".

STAFF PAGE (/)
Title: "Submit a claim". Two columns on desktop: form left (about 40%),
claim sheet right.
- Field "Your name" (text, required).
- Field "Expenses" (textarea, 6 rows, required, max 2000 chars) with
  helper text: "One expense per line. Mention people, nights and whether
  you have a receipt." Placeholder:
    Dinner for 3, 620 SAR, no receipt
    Airport taxi 85 SAR, receipt attached
- Button "Check claim". While waiting: button disabled and label
  "Checking..."; status text "Checking your expenses against the policy."
- Before any check, the right column shows a short empty state:
  "Your checked claim will appear here."
- After a successful check: render the claim sheet and a primary button
  "Send to manager". After sending: the pill changes to Waiting for review
  and a confirmation reads "Sent to manager. Claim #<id> is waiting for
  review." Hide the send button. A secondary "Start a new claim" button
  clears the form.
- Errors show under the form in --breach, specific and actionable:
    422 -> the API's detail message
    502 -> "The model did not respond. Try again in a moment."
    503 -> the API's detail message
    network failure -> "Could not reach the server. Is it running?"

REVIEW PAGE (/review)
Title: "Review claims". Two columns on desktop: queue left (about 32%),
selected claim right.
- Queue: claims with status submitted, newest first, from
  GET /api/claims?status=submitted. Each item: submitted by, total, and
  "2 violations" in --breach or "No issues" in --ok, plus relative time
  ("5 min ago"). Items are buttons; the selected one is highlighted.
- Empty queue: "No claims are waiting for review."
- Selecting an item loads GET /api/claims/{id} and shows the claim sheet.
- Under the sheet, a decision panel: "Comment" textarea (helper text:
  "Required when returning a claim."), then "Approve claim" (primary) and
  "Return claim" (secondary, --breach text). Returning with an empty
  comment shows an inline error and sends nothing.
- After a decision: confirmation "Claim approved." or "Claim returned to
  <name>.", the claim leaves the queue, and the next claim is selected
  if there is one.
- On 409, show "This claim was already decided." and refresh the queue.

STYLE
Small readable functions, no inline styles in HTML, no extra pages,
endpoints or features beyond this list.

When finished, list the files you created or changed, and the commands
to run the tests and start the server.
```

## Result

(Fill in after verification: commit hashes, test count, screenshots, issues found.)
