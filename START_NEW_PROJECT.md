# Start a new application — Codex execution prompt

> [!IMPORTANT]
> **For Codex CLI:** Treat this file as instructions to execute, not as an explanation to summarize. The first reply must contain **only** the language question at the end of this document. Do not infer requirements from older projects.

## 1. Scope and initial language decision

You are initiating a **NEW application** with Exelia Ultimate Codex Starter. This repository is a reusable starter, **not** an existing product specification. Never copy requirements, business rules or UI decisions from unrelated applications.

**Before doing any technical analysis**, proposing product features, reading extensive documentation, or asking about the product, ask exactly one question if `conversation_language` has not been selected:

> W jakim języku chcesz rozmawiać i pisać prompty do Codexa — po polsku czy po angielsku? / Would you like to communicate with Codex in Polish or English?

Wait for the human's answer. Then store the preference with:

```bash
python3 scripts/project-state.py language pl   # or: en
```

Use that language for all human-facing dialogue, summaries and stage announcements. **Always use English** for code, identifiers, code comments, tests, agent instructions, agent-to-agent records, project state, task artifacts, templates and technical documentation. The **application UI** language is a separate discovery decision; record it in the PRD and `project.config.json`, using the actual locale values:

```bash
python3 scripts/project-state.py ui-language en,pl
```

The command above is an **example**, not a default UI language selection.

## 2. Inspect the project before acting

Once the language is selected, inspect only the files required for the next step:

- `AGENTS.md`, `starter.yaml`, `project.config.json`, `tasks/STATE.json`.
- Relevant parts of `docs/standards/` and `docs/templates/`.
- Git worktree status, role files under `.codex/agents/`, required skills and configured MCP tools.

Verify that **this repository** contains `.agents/skills/ponytail/SKILL.md`. Apply its minimal-change coding guidance through `AGENTS.md` when relevant, without skipping tests, accessibility or security. It is a project skill: **no global Ponytail plugin or trust required**. An independently installed global plugin may coexist, but its lifecycle and hooks are outside Exelia's control. Avoid duplicating guidance.

The separate Exelia SessionStart hook (`.codex/hooks.json`) belongs to **Exelia, NOT to Ponytail**. Do not claim any skill, hook, tool or MCP is operational merely because configuration files exist. Confirm runtime behavior before claiming success. Never install, trust, modify or depend on global Ponytail hooks for this starter.

## 3. Conduct guided product discovery

Interview the human in focused, manageable batches. Cover:

1. Problem, desired outcomes, personas and key workflows.
2. Functional features, constraints, priorities and measurable acceptance criteria.
3. Data, privacy, authentication, user roles, compliance and integrations.
4. AI/automation needs, error handling, performance and reliability.
5. Visual direction, accessibility and **application UI language(s)**.
6. Infrastructure, deployment, operations, budget, milestones and risks.

Challenge ambiguous requirements constructively. Explain meaningful tradeoffs; never fabricate decisions. Default candidates are React/Next.js and Python/FastAPI, but choose the stack to fit the application. OrbStack is a local development environment, not necessarily the production target.

Use relevant scoped subagents for independent discovery and architecture work when they improve quality.

## 4. Produce and cross-check English specifications

Populate **all 14** documents in `docs/project/` from their corresponding templates:

| Product and design | Engineering and delivery |
| :--- | :--- |
| `PRODUCT`, `PRD`, `UI_UX` | `ARCHITECTURE`, `TECH_STACK`, `DATABASE`, `API_SPEC` |
| `SECURITY`, `TEST_STRATEGY` | `DEPLOYMENT`, `MODEL_POLICY` |
| `DECISIONS` | `IMPLEMENTATION_PLAN`, `BACKLOG` |

Make the content specific to the user's answers. Mark unsupported or unresolved matters `TBD` rather than inventing them. Cross-check security assumptions, API contracts, architecture, testing, UX and backlog. Keep `tasks/STATE.json` and task ledger aligned with the documents.

For each stage, recommend a model and reasoning effort **based only on models confirmed available** in the active Codex runtime. If agent-level routing is unsupported or model availability unknown, inherit the existing model and state the limitation rather than inventing capabilities.

## 5. Mandatory documentation approval gate

> [!CAUTION]
> **Do not implement the application yet.** Before application code, migrations or application dependencies, present a concise summary of the completed specification and request **ONE explicit user approval** of the documentation and architecture.

Only after a clear, real approval from the human may you record it:

```bash
python3 scripts/project-state.py approve --evidence "<exact user approval statement>"
```

Do not manufacture approval, record a paraphrase as if it were a quote, or bypass validation. Until approval is recorded, continue discovery or documentation rather than application implementation. Git bootstrap and QA-validated documentation checkpoints are permitted under the existing project safeguards.

## 6. Autonomous implementation after approval

Once approved, continue within the authorized sandbox, without asking for approval at each ordinary stage:

1. Announce the stage in the chosen conversation language: recommended model, reasoning effort, why, actual executor model **if verifiable**, and planned specialist roles.
2. Delegate bounded tasks to `.codex/agents/` roles; parallelize only when file ownership does not overlap. Use worktrees where appropriate.
3. Apply relevant project skills; implement the smallest correct solution that meets approved acceptance criteria.
4. Run reproducible tests, inspect failures, request an **independent** QA/security review, resolve findings and maintain English documentation and task evidence.
5. Create a **local** Git checkpoint using `scripts/git-checkpoint.sh` **only after** the corresponding quality gate succeeds.

Never automatically push, publish, deploy to production, or access host resources outside the allowed workspace. Do not enable `danger-full-access`, `--yolo`, bypass Git hooks or skip security checks merely to avoid prompts. Keep the repository resumable.

---

## First response — mandatory

**Ask only this question and wait. Do not start discovery yet:**

> W jakim języku chcesz rozmawiać i pisać prompty do Codexa — po polsku czy po angielsku? / Would you like to communicate with Codex in Polish or English?

## 7. Executable Exelia 2.1 delivery controls

After actual written approval and with the chosen stack recorded in `project.config.json`:

1. Show the model and reasoning recommendation (`python3 -m exelia model architecture --risk high`). The recommendation is not proof of actual Codex model routing.
2. Resolve relevant skills (`python3 -m exelia capabilities plan`), review `./install.sh --plan`, then install them project-locally with `./install.sh --resume`; record a content snapshot (`python3 -m exelia capabilities freeze`). Never install globally.
3. Plan real, bounded, dependency-aware tasks in `tasks/backlog.json`, using coordinator-only `scripts/task-ledger.py`. Assign nonoverlapping file scopes for concurrent work.
4. Use `python3 -m exelia dispatch plan` before `dispatch prepare`; the latter creates isolated Git worktrees and packets. Delegate those packets through **native Codex subagents** in the live session, with each worker using the assigned worktree. Never claim the Python CLI itself spawned the agents.
5. Create product QA only from real application structure (`python3 -m exelia quality plan`, then `quality configure` when ready). Add Playwright smoke checks for web projects (`visual plan/setup/run`) and expand tests to product acceptance criteria.
6. Independently review and validate committed worktree changes, move tasks to `ready_for_review`, inspect `worktrees integrate ID`, then perform the explicitly authorized merge with `--confirm` and re-run main QA. No automatic push, deployment or force-reset.
7. Record actual per-agent pass/fail, duration and optional observed token/cost metrics (`python3 -m exelia eval record`), without invented values. Update docs and ledger; make local Git checkpoints.

Consult [automation workflow](docs/automation/WORKFLOW.md) before a multi-agent implementation. CLI enforcement is deterministic but does not replace the Codex sandbox or real approval controls.
