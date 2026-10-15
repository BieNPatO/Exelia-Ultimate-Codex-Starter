# Exelia 2.1 — execution modules

> [!IMPORTANT]
> All CLI operations are **repository-local**. The tool does not start a daemon, clone remote repositories, authenticate Codex, grant sandbox permissions, launch subagents on its own or automatically push/deploy code.

Exelia combines auditable Python commands with native Codex subagents. The coordinator (Codex) reads project decisions and delegates work after the one-time documentation approval. Python handles deterministic state transitions, Git isolation and verification; Codex handles actual coding.

## Quick reference

| Component | Read-only | Explicit action | Does not do |
|---|---|---|---|
| Capabilities | `python3 -m exelia capabilities plan` | `... capabilities freeze` / `... capabilities audit` | Downloads skills or certifies upstream origin |
| Model recommendations | `python3 -m exelia model architecture --risk high` | Configure chosen model in Codex | Silent actual model switch |
| Dispatch | `python3 -m exelia dispatch plan` | `... dispatch prepare` | Launch Codex agents by itself |
| Worktrees | `python3 -m exelia worktrees status` | `... worktrees prepare TASK`; `... integrate TASK --confirm` | Push, force reset or clean up unknown work |
| Quality | `python3 -m exelia quality plan` | `... quality configure` | Pretend absent tests pass |
| Visual QA | `python3 -m exelia visual plan` | `... visual setup`; `... visual run` | Automatically start the app or install browsers globally |
| Evaluation | `python3 -m exelia eval summary` | `... eval record` | Invent token counts or claim model comparisons are scientific benchmarks |

For complete steps and boundaries see [Workflow](WORKFLOW.md), [Quality and visual QA](QUALITY.md), [GitHub publishing](../GITHUB_SETUP.md).
