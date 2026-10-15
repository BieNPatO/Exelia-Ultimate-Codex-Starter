---
name: project-delivery
description: Use for orchestrating new-project discovery, multi-agent implementation, stage model selection, quality gates, Git versioning, handoffs and resumable project state.
---

# Project Delivery Contract

## Discovery/approval

Ask conversation language first, independently ask app UI language in discovery. The PRD and other engineering artifacts remain English. Before implementation, build complete English docs and request **one explicit human documentation approval**. Record user evidence using `scripts/project-state.py`; never self-approve.

## Each stage

1. Consult `tasks/STATE.json`, backlog, approved plan and Git diff.
2. Recommend model + reasoning effort in human language. Explain risk, skills and delegation. Verify real availability; do not claim model switched when it hasn't.
3. Partition non-overlapping scopes and assign relevant role agents. Limit concurrency; reviewers are independent of implementers.
4. Implement with minimal complexity, verify behavior, do security review when relevant and update docs/decisions.
5. Set gate outcome `PASS|FAIL|BLOCKED|NOT_RUN` with commands and evidence. Do not use PASS without fresh tool evidence.
6. Create a local Git conventional checkpoint only after successful quality gate. Never push automatically. Write concise human-facing stage summary and move forward.

## State and failure recovery

Treat task state in `tasks/` as authoritative for workflow but always confirm it against Git and real tests. Store only short summaries and evidence paths, not agent transcripts. On failure do root-cause debugging and bounded retries (max 3 before reevaluating plan). A blocked gate pauses completion, not the entire discovery conversation. Resume in-progress work from the current state without assuming prior claims were true.
