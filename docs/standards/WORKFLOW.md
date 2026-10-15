# Interview, approval, implementation and QA

**Workflow states:** `discovery` -> `specification` -> explicit `approval` -> `implementation` -> `verified` -> `release_ready`. `tasks/STATE.json` persists the current state, but is not itself proof of code correctness.

## Discovery

Ask language first; retain human language for dialogue. Ask application UI locale during product analysis, record with `python3 scripts/project-state.py ui-language en,pl` (actual locales), and document independently. Product Analyst and Solution Architect analyze needs. Ask in compact batches and challenge weak assumptions. Write English documents from templates; each feature must have a PRD ID and measurable acceptance.

## Approval

Run documentation completeness check and an independent consistency review across PRD/API/security/architecture/tests. Present summary in human language, ask for one explicit written approval. Record the actual reply text and timestamp in state. Approval is a procedural control: the local script can store supplied text but cannot cryptographically authenticate who typed it.

## Implementation

Before every stage, provide model and reasoning explanation without asking permission again. Allocate clear file ownership, obtain relevant skills, run implementation agents, independent reviewer, QA and security reviewer for sensitive changes. A fix with three failed attempts triggers architecture reevaluation.

## Quality

Every task: acceptance -> implementation -> reproducible automated checks -> independent findings -> fixes -> pass evidence -> Git checkpoint. Mark tests PASS, FAIL, BLOCKED, NOT_RUN. Don't confuse compile success with UI usability or API security; test with browser for relevant workflows.

## Context efficiency

Use short per-task handoffs and targeted searches. Ponytail is expected to be active; it reduces unnecessary code but never exempts critical logic, tests or protections. No RTK/Headroom/router add-ons in this starter.

## Task ledger commands

Coordinator is the sole writer to `tasks/backlog.json`; no concurrent writes. Use `python3 scripts/task-ledger.py add AUTH-001 --title "Add login" --owner backend-engineer --scope "backend/auth/**" --acceptance "Auth tests pass"`, then `start AUTH-001`, `review AUTH-001`, `complete AUTH-001 --evidence "pytest ... PASS; independent review ..."`. Completion **executes the application quality gate** and refuses to mark done if checks fail. Block via `block ID --evidence "reason"`.
