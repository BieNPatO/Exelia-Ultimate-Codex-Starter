# Stage model policy

Before **each stage** make a short announcement to the human in `project.config.json` language: stage goal, recommended model, reasoning effort, rationale, proposed agents, actual selected model (if verifiable), and whether requested routing was applied. This is not an approval request.

## Default reasoning policy

| Stage type | Suggested effort | Rationale |
|---|---|---|
| Discovery and product analysis | high | Ambiguity, scope risk |
| Architecture, auth, security | high / xhigh when supported | Deep tradeoffs and threat modeling |
| Standard backend / frontend code | medium / high | Balance reliability and cost |
| Small formatting / documentation fixes | low / medium | Bounded deterministic edits |
| Root-cause debugging | high | Nonlocal dependencies and regressions |
| QA and independent review | high | Detect defects missed by implementer |

Use `codex --help`, `/model` and current official docs to check available models, rather than assuming a suggested model ID is valid. Agent role files inherit the parent model unless explicitly configured; many files set only `model_reasoning_effort`. To enforce different per-role models, **configure them after availability check** in `.codex/agents/*.toml` or via supported spawn controls; record the outcome in `docs/project/MODEL_POLICY.md`. Do not claim runtime model switched by merely mentioning it in text.

For programmatic stage-level routing across primary Codex sessions, an additional external controller would be required and is not included in v0.1.0. The initial ZIP implements policy, guidance and agent-side settings; not an autonomous primary-session model switcher.
