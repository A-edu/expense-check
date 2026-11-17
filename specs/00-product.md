# 00 Product

## Problem

Expense lines are checked by hand against a policy document. Violations surface late, after
the claim is already queued for approval, and reviewers repeat the same lookups for every claim.

## What Expense Check does

Staff paste expense lines in plain text. The model turns them into structured lines with a
category. A rules engine checks each line against a versioned policy file and flags every
violation with the rule it breaks. The model drafts a short summary. A manager approves or
returns the claim. Nothing is approved without a person.

## Core principle

The model extracts and summarises. It never decides compliance. Every flag comes from code
reading the policy file, so every flag can be traced to a written rule.

## Users

| Person | Role | Needs |
|---|---|---|
| Sara | Staff, submits claims | To know before sending whether a line is allowed, and why not |
| Nora | Manager, approves | Line-level evidence to approve or return with confidence |

## M1 scope

- Paste expense lines, get them extracted, categorised, checked and summarised.
- Send a checked claim to the manager.
- Manager queue, approve, or return with a comment.
- Policy in one JSON file: meal per person, taxi per line, hotel per night, receipt above
  a threshold, manual review for "other".
- Local web app: Python, FastAPI, SQLite, Gemini Flash, plain HTML/CSS/JS.

## Non-goals

- No payments, reimbursement, or card or bank integration.
- No receipt image reading.
- No real employee data; synthetic examples only.
- No currencies other than SAR.
- No user accounts in M1 (a page switch stands in for the two roles).

## Phases

| Phase | Focus |
|---|---|
| M1 | Thinnest working pipeline, end to end |
| M2 | Accounts and roles, manager edit and override, return-and-resubmit loop |
| M3 | Reliability: test set of expense texts, model consistency, prompt-injection defence |
| M4 | Polish, documentation, deployment |

## Change log

- 2026-11-17: First version.
