# Prompts

The exact prompts sent to the coding agent, one file per prompt, in the order they were run.
Each file records when it was used, which spec it implements, and what came out of it.

| File | Spec | Result |
|---|---|---|
| [01-rules-engine.md](01-rules-engine.md) | [specs/01](../specs/01-rules-engine.md) | Commit `4650dd6`, 21 tests |
| [01a-rules-engine-fixes.md](01a-rules-engine-fixes.md) | [specs/01](../specs/01-rules-engine.md) | Commits `47e3068`, `721077d`, 33 tests |
| [02-pipeline-and-api.md](02-pipeline-and-api.md) | [specs/02](../specs/02-pipeline-and-api.md) | Commit `1464137`, 48 tests |
| [02a-pipeline-fixes.md](02a-pipeline-fixes.md) | [specs/02](../specs/02-pipeline-and-api.md) | Not run on its own; merged into 03 |
| [03-web-pages.md](03-web-pages.md) | [specs/03](../specs/03-web-pages.md) | In progress |

## Rules for this folder

- Save the prompt exactly as sent. If you edit it before sending, save the edited version.
- Never change a prompt after it has been run. Write a new file (`01a`, `01b`, ...) instead.
- Fill in the "Result" section after verifying: commit hashes, test count, and anything the
  agent got wrong.
