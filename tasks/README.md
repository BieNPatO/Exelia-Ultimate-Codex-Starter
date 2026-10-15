# Task ledger and approval state

`STATE.json` stores phase and the **one-time human approval record**. `backlog.json` stores tasks with ID, owner, scope, dependencies, acceptance criteria, status and QA evidence. These files are tracked and provide the portable record across machines; approvals are a workflow convention, not tamper-resistant authentication.

Use `python3 scripts/task-ledger.py add ID --title '...' --owner backend-engineer --scope api/src --acceptance '...' --deps OTHER`. Only the coordinator writes the ledger. Use `start`, `review`, `complete --evidence '...'`, `block --evidence '...'` to transition tasks.

See [automation workflow](../docs/automation/WORKFLOW.md) for dependency-aware planning and Git worktrees. Worktrees, browser results and run metrics live in git-ignored `.exelia/` and can be rebuilt locally. Prevent overlapping file ownership for parallel tasks.
