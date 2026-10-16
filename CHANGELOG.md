## 2.1.1 — Stability & Security Release Candidate (2026-10-16)

- Normalize task scopes, reject traversal and escaping symlinks, and serialize portable case aliases and parent/child ownership.
- Propagate Visual QA failures through the CLI; use Chromium-compatible desktop and Pixel 7 smoke projects.
- Audit selected skills, optional selectors, source records and content drift; exercise core, React, Python and combined configurations.
- Handle empty dispatch queues without worktree creation; reopen blocked tasks with evidence and preserved history.
- Require structured independent review evidence tied to the exact task commit before integration and completion.
- Share nested sensitive-file protection, redact synthetic credential formats in installer logs, and scan release content and reachable local Git history.
- Harden checkpoint scope, installation fixtures and dependency policies; preserve project-local isolation and first-frame Rich.
- Accept documented language, script, region and variant UI tags separately from Polish/English conversation settings.
- See the [remediation audit](docs/audits/REMEDIATION_2.1.1.md) for executed tests, dependency provenance, infrastructure pinning status and residual limitations. Final independent audit and public publication approval remain separate.

## 2.1.0 — Intelligent development foundation (2026-10-15)

- Added project capability selection driven by the actual stack and optional visual/security policies; bootstrap defaults to core skills and installs chosen extensions locally with a later `--resume`.
- Added a locally stored skills content lock with SHA-256 directory digests and drift auditing; upstream source revision pins are still pending.
- Added an offline, dependency-aware task scheduler and dispatcher, local Git worktree creation, scope-overlap checks, approval gates, review-only integration dry-run and explicitly confirmed QA-gated merges.
- Added strict project QA command generation and optional browser smoke templates, two device profiles, locally scoped browser cache and factual run records.
- Added model/reasoning recommendations (not undocumented switching) and local metric logging for agent evaluations.
- Added public GitHub template guidance, MIT license for original starter code, third-party license notice, contributing instructions, security policy, a publication scanner and optional VS Code Markdown extensions.
- Hardened default Codex permissions: workspace sandbox, `on-request` exceptions and network disabled by default.
- Downloaded third-party skills are Git-ignored to avoid unreviewed redistribution in a public starter; source revision pinning and reproducibility remain a disclosed gap.
- Bundled first-frame Rich installer, custom agent roles, docs approval gate and project-local Ponytail behavior retained from 2.0.4.

## 2.0.4 — First-frame Rich dashboard

- Bundled Rich 15.0.0 and pure-Python runtime dependencies inside `installer/_vendor`, with upstream license texts.
- The first `--plan` is a real Rich dashboard without a pip download or global installation.
- Added read-only `--ui-demo` to view the actual rendering without hardware or network setup.
- Collapsed repetitive inventory into a concise overview; full detail remains under `--verbose`.
- Added persistent progress for local tools and project skills, improved adaptive tables and final summary.
- Maintained project-local Ponytail and local-only skills; no global hooks/plugins installed.

# Changelog

## 2.0.3 — 2026-10-15

### Documentation design and onboarding

- Rebuilt `README.md` as a navigable product overview with a workflow diagram, scoped installation map and command reference.
- Reworked `START_HERE.md` into a step-by-step user walkthrough with expected outcomes and recovery links.
- Reformatted `START_NEW_PROJECT.md` into an explicit, sectioned Codex prompt; preserved first-language question, English engineering artifacts and one-time approval gate.
- Reworked `CONTINUE_PROJECT.md` into an evidence-driven resume prompt with phase-dependent instructions.
- Added `docs/installer/TROUBLESHOOTING.md` for PARTIAL, Impeccable, MCP, custom agents, Git and Rich.
- Rewrote `docs/installer/PONYTAIL.md` to distinguish local skill, global plugin and Exelia SessionStart hook.
- Kept installer operations, security and strict project-local installation behavior unchanged in 2.0.3.

## 2.0.2 — 2026-10-15

### Terminal UI and Ponytail consistency

- Replaced hand-aligned status printouts with actual project-local Rich panels, tables, rules and animated step progress (plus readable no-dependency bootstrap).
- Added a compact action-oriented final screen showing missing skills, precise Impeccable completion command, Git status and MCP checks.
- Clearly distinguishes `CONFIGURED` project MCP/hooks from tested/connected external services.
- Corrected contradictory references to Ponytail plugin/hook trust in `START_NEW_PROJECT.md`, root `AGENTS.md` and Exelia `SessionStart` hook.
- Documented that global Ponytail plugin hooks may coexist but are not installed, required or automatically trusted.
- Added terminal UI and Ponytail local-mode policy docs, offline unit tests and simulated fresh-install tests.

### Retained guarantees from 2.0.1

- **Strict project-only installations:** npm CLIs under `.exelia-tools/node`, Python tools under `.exelia-tools/python`, all skills under `.agents/skills`; global binaries and plugins are not altered.
- Ponytail installed locally as a skill and loaded through project AGENTS.md, rather than through global Codex plugin hooks.
- OpenAI Docs and Context7 MCP configured only in project `.codex/config.toml`.
- Fixed initial Git checkpoint blocked by trailing spaces in upstream Vercel markdown with narrowly scoped `.gitattributes`. Application whitespace checks remain intact.
- More precise checkpoint failure diagnostics and project-local scope detection; global skill copies are not treated as ready.
- Professional Rich-enabled project-local terminal output (ANSI fallback).
- Fresh project integration smoke validates no global package/plugin installation, first local commit and idempotent resume.
- Distinct live connectivity statuses; no misleading claim that MCP or Codex agents are verified from an offline fixture.


## 2.0.0 — 2026-10-14

### Full self-contained release

- Replaces the 0.1.x distribution; no earlier folder or ZIP required.
- Adds modular Python standard-library full installer plus macOS/Linux/WSL2 shell launcher and Windows WSL2 guidance.
- Introduces detailed read-only system discovery, tool version checks, Docker daemon check, Git state inspection, global/project skills reuse, Ponytail plugin detection and MCP configuration reporting.
- Adds check, plan, apply, resume, repair, verify, report and safe local rollback modes, with JSON output, colored TTY statuses and concise status messages.
- Adds installer journal, lock, local backups, Git identity setup and automatic QA-gated Git baseline, but never Git push.
- Updates integration commands to re-use existing components. Adds official Ponytail install support and vendor skills/Playwright workflows with explicit manual trust/auth steps.
- Adds installer-specific security, platform and rollback documentation and offline mocked clean-project integration test.
- Preserves all 12 agent roles, existing custom skills, language policy, one-time documentation approval, autonomous local workflow, task ledger and docs templates.

### Known limitations

- Real Codex plugin hooks and live MCP OAuth cannot be verified without trusted user credentials and Codex UI; not falsely counted as passed.
- Native Windows automated install is not provided; use WSL2.
- Impeccable's interactive installer and Context7 OAuth need a manual step when missing.
- OS-level upgrades or Docker installation can require trusted package-manager/user approval and may need a restart.

## 0.1.0 — 2026-10-14

- First reusable starter with Git, 12 roles, project docs, QA gate and custom skills.
