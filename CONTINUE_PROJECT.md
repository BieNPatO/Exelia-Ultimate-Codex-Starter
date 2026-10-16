# Resume an existing application — Codex execution prompt

> [!IMPORTANT]
> **For Codex CLI:** Continue the project from evidence, not from assumed progress. Do not start a new requirements interview if the project already has approved documentation.

## 1. Reconstruct the actual state

Read only the relevant sources:

- `AGENTS.md` and `project.config.json` for instructions and language.
- `tasks/STATE.json` and `tasks/backlog.json` for phase, approval and next work.
- `docs/project/IMPLEMENTATION_PLAN.md` plus relevant requirements and architecture documents.
- `git status`, recent commits and actual test evidence.

Do **not** infer completion from an earlier agent's claim or an unchecked task status. If the human's conversation language is saved, use it; keep technical artifacts, code and inter-agent communication in English. The application's UI language follows its PRD and project settings.

## 2. Report a concise handoff

In the saved human language, summarize:

| Item | What to report |
| :--- | :--- |
| Current phase | Discovery, specification, approval, implementation or release preparation |
| Latest verified outcome | Evidence from tests, files and Git — not assumptions |
| Open decisions / blockers | Unresolved `TBD` items and missing prerequisites |
| Approval state | Whether explicit documentation approval is recorded |
| Next step | One bounded, concrete task and expected verification |

## 3. Continue according to the approval gate

- **Still in discovery/specification?** Resume the smallest useful group of questions; complete and cross-check English documentation. Do not implement prematurely.
- **Docs complete, no approval?** Present the review summary and request **one explicit human approval**. Never record approval yourself.
- **Approved?** Announce the next stage's recommended model, reasoning effort and rationale. Use the verified runtime model; delegate bounded work to specialist agents where useful. Then implement, test, review and create a QA-gated **local** checkpoint.

## 4. Maintain boundaries

Do not push, deploy, bypass quality gates, change global plugins, or install dependencies globally. Use project-local Ponytail instructions when relevant; do not require global Ponytail hook trust. Preserve uncommitted work, record uncertainty and leave the project resumable.

**Start by inspecting the actual state and reporting the handoff; do not claim work is complete without evidence.**

## Exelia 2.1.1 workspace recovery

Read `tasks/STATE.json`, `tasks/backlog.json`, `project.config.json` and `git status` first. Run `python3 -m exelia worktrees status` to discover machine-local worktrees; this is not proof that Codex sessions are still running. Recreate task packets with `python3 -m exelia dispatch plan`. Never recreate or delete an existing task branch automatically or claim a worktree is clean without checking it. Re-run product QA and any configured visual tests before completion.

A blocked task can return to `todo` only through `python3 scripts/task-ledger.py resume TASK --evidence 'what changed and where it was verified'`. This preserves history and invalidates previous review evidence; dependency checks still apply when starting it. A `ready_for_review` status alone never proves an independent review. Record a fresh `attest-review` for the exact task commit before integration or completion; see [workflow](docs/automation/WORKFLOW.md).

An empty or dependency-blocked dispatch plan is a successful no-op with zero prepared tasks. Do not create branches merely to make an empty queue appear active. Consult the [candidate audit](docs/audits/REMEDIATION_2.1.1.md) for verified behavior and residual limits.
