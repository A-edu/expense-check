# Specs

What each part of Expense Check must do, written before the code is generated.
A spec states the behaviour; the matching file in [prompts/](../prompts/) is how it was
handed to the coding agent.

| Spec | Phase | Status |
|---|---|---|
| [00-product.md](00-product.md) | All | Living document |
| [01-rules-engine.md](01-rules-engine.md) | M1 | Done, verified |
| [02-pipeline-and-api.md](02-pipeline-and-api.md) | M1 | Built; 3 open items, real-model check pending |
| [03-web-pages.md](03-web-pages.md) | M1 | In progress |

## How to write a spec

1. Goal: one or two sentences.
2. In scope and out of scope.
3. Contracts: inputs, outputs, errors.
4. Acceptance criteria as Given / When / Then, including at least one failure case
   and one boundary case.
5. How it is verified, and the result once checked.

Change a spec when the behaviour changes, and note why in its change log.
