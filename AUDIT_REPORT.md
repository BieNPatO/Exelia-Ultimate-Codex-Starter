# Exelia Ultimate Codex Starter 2.1.0 — Release audit

**Audit date:** 2026-10-15
**Source baseline:** v2.0.4 ZIP
**Scope:** code, docs, third-party scope, GitHub readiness, offline tests, behavioral limitations

## Implementation traceability

| Requested capability | Concrete implementation | Verification | Limitations |
|---|---|---|---|
| Dynamic Capability Resolver | `exelia/capabilities.py`, `installer/engine.py`, `project.config.json` capability switches | Unit tests; offline fresh-install plan and core-only installation | Skill sources lack pinned Git revisions; `freeze` tracks installed directory content only |
| Git Worktrees + orchestrator | `exelia/worktrees.py`, `exelia/dispatch.py`, task ledger, Codex coordinator instructions | Real temporary Git repository tests: clean/dirty/approval checks, overlap, worktree add, commit, dry-run and confirmed QA-gated merge | Worktrees are file isolation, **not security containers**; Python generates packets but Codex itself must execute subagents |
| Quality/security gates | `exelia/quality.py`, existing `scripts/quality-gate.sh`, worktree integration checks | Product gate refuses missing tests/approval; branch QA precedes merge | Actual project QA is generated only once a real app exists; post-merge QA and integration conflict handling remain explicit operator/coordinator responsibilities |
| Visual QA | `exelia/visual.py`, project-local Playwright templates and run record | Generator unit tests: approval, no overwrite, missing browser refusal | No live browser, running app, axe audit or pixel-diff test has been executed in this environment |
| Persistent state | Existing `tasks/STATE.json`, `tasks/backlog.json`, atomic local `worktrees.json` and dispatch packets | Tests for task planning, status, persisted workspaces | Worktree registry and evidence cache are machine-local and Git-ignored; no background daemon |
| Model routing + agent evaluations | `exelia/models.py`, `exelia/evaluations.py` | Tests for recommended effort and honest token/cost aggregation | Recommendations are **not** runtime model switches; measured agent benchmark automation requires authenticated Codex |
| Public GitHub usability | `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `docs/GITHUB_SETUP.md`, GitHub CI and issue template | Publication scanner, staged whitespace check, archive verification | Cannot validate the owner's real GitHub permissions, repository settings or third-party skill licensing for future downloads |

## Executed checks

- **PASS:** `python3 scripts/validate-starter.py` — structure, 12 roles, custom skills and project documents.
- **PASS:** `python3 -m unittest discover -s tests -q` — **49 unit tests** including 12 new executable-automation tests.
- **PASS:** `python3 tests/integration_smoke.py` — sandboxed simulation with fake host tools, project-local core install, Ponytail skill, first Git commit, idempotent `--resume`, post-discovery plan selecting Next.js/FastAPI/Playwright/security. All external downloads mocked.
- **PASS:** `python3 scripts/check-publication.py` — tracked/publication path check, basic secret markers and presence of legal/docs files. Not a full secret scanner.
- **PASS:** `git diff --cached --check` against a fresh staged repository copy (Git whitespace and line endings).
- **PASS:** first-frame Rich is exercised by unit tests, including `python -S` without global site packages.
- **PASS:** no `npm --global`, `brew install`, `sudo` or global `codex plugin` is invoked by the offline installation simulation.

## Risks and future work

1. **Third-party supply chain:** Pin each upstream skill to a reviewed immutable Git commit or artifact checksum, and verify package provenance/licensing before security-critical reuse. The present SHA-256 lock detects drift only after installation.
2. **Full runtime autonomy:** Codex multiagent spawning and real model switching are not performed by the local CLI. Codex must interpret the task packets in a live authenticated session. A dedicated app-server adapter would be needed for unattended agent launching and telemetry.
3. **Strong isolation:** Neither `workspace-write` nor Git worktrees guarantee containerized process isolation. Enable a reviewed OrbStack execution profile separately before running untrusted code or granting network access.
4. **Full visual QA:** The generated Playwright smoke test is a starting point only; add per-product accessibility, keyboard, flows, error states, traces and responsive visual baselines.
5. **Post-merge validation:** Explicitly rerun quality gates on main; merge conflict resolution and rollback are deliberately not automated or destructive.
6. **Live targets:** Not tested on the user's macOS Ghostty/OrbStack, real npm/skills sources, connected Context7/OpenAI Docs, or GitHub hosting. Windows PowerShell also remains untested here.
7. **GitHub Actions:** Actions use version tags. Pin reviewed full action commit hashes as part of future public repository hardening.

## Decision

**Suitable as a GitHub Template repository and development foundation** following the documented publication review, with the listed limitations. **Not yet a fully autonomous, production-grade agent-hosting platform** or cryptographically reproducible supply-chain package.

For publishing and creating new applications, see [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md). The default installation is scoped to the repository, and nothing is pushed or deployed automatically.
