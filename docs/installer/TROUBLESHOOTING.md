# Troubleshooting — Exelia Ultimate Starter

[← Quick start](../../START_HERE.md) · [Command reference](../../README.md#command-reference) · [Ponytail guidance](PONYTAIL.md)

> [!IMPORTANT]
> **Diagnose before repairing.** `--check`, `--plan` and `--verify` are read-only. Review planned commands before `--apply`, `--repair` or `--resume`; third-party downloads are not automatically security-audited.

## Quick symptom lookup

| What you see | Likely meaning | Start here |
| :--- | :--- | :--- |
| `INSTALLATION PARTIAL` | A manual step or unverified integration remains | [Partial setup](#installation-partial) |
| `impeccable` skill missing, CLI ready | CLI and Codex skill are separate | [Impeccable](#impeccable-cli-ready-but-skill-missing) |
| Ponytail asks for hook trust | An independently installed **global plugin** is asking, not the local skill | [Ponytail](#ponytail-hook-trust-dialog) |
| Context7 / OpenAI Docs `CONFIGURED` | Configuration exists; live connection not yet tested | [MCP](#mcp-is-configured-but-not-verified) |
| `/agents` shows a task dashboard | That UI lists sessions/tasks, not the 12 custom role definitions | [Agent roles](#where-are-the-12-agents) |
| Git initial commit fails | Whitespace, local identity, secrets or QA gate may be blocking | [Git checkpoint](#initial-git-checkpoint-fails) |
| Rich styling not visible | Bundled renderer missing, non-TTY or `NO_COLOR` may be active | [Rich UI](#rich-does-not-appear) |

## Installation `PARTIAL`

A `PARTIAL` result does **not** automatically mean the install failed. Review the specific missing skills, manual actions and quality checks in the latest report:

```bash
./install.sh --report
./install.sh --verify
```

Reports are also written under `.exelia-install/` in the project. These logs can include tool output; review before sharing.

If an explicitly required manual component has been installed, rerun:

```bash
./install.sh --resume
```

Do not repeatedly run `--apply` without reading the report; it is designed to avoid duplicate installation, but new downloads may still occur for missing dependencies.

## Impeccable CLI ready, but skill missing

The `impeccable` **CLI** under `.exelia-tools/node` and the **skill** under `.agents/skills/impeccable/` are different.

```bash
./scripts/local-tool.sh impeccable install
```

During the interactive upstream installer select **Codex** and **Project**, never Global. Then verify:

```bash
./install.sh --resume
./install.sh --verify
```

Expected skill path:

```text
.agents/skills/impeccable/SKILL.md
```

If the CLI offers different choices from these, do not guess. Check its prompts before proceeding.

## Ponytail hook trust dialog

Exelia installs a **project-local skill** at `.agents/skills/ponytail/SKILL.md`, not the global `ponytail@ponytail` plugin. The skill is usable without trusting global lifecycle hooks.

- If a **global Ponytail** plugin asks for trust, review the plugin source and exact hook command separately. No global trust is required for Exelia.
- If the hook references `.codex/hooks/session_start.py` **inside this repository**, that is Exelia's distinct project-state reminder hook. Review its code before approving.
- Neither hook type may be assumed trusted or active just because files are present.

[Read the full Ponytail contract](PONYTAIL.md).

## MCP is configured but not verified

`CONFIGURED` in the installer is weaker than a successful tool call. Launch Codex in the current project, check the MCP status (for example with `/mcp` where available) and **invoke one read-only tool** from Context7 and OpenAI Developer Docs.

A connection marked `connected` verifies a session link; it does not guarantee every request will succeed or that an OAuth grant covers every resource.

Avoid pasting access tokens into project documentation or issue reports.

## Where are the 12 agents?

Custom agent **definitions** are files in `.codex/agents/*.toml`. They are not necessarily listed in the Codex **`/agents` task dashboard**. A genuine integration test is to ask Codex to spawn two clearly named custom roles on **read-only, non-overlapping** tasks, then inspect the spawn result or subagent session view if supported by your runtime.

Do not claim that agents are running merely because 12 TOML files exist.

## Initial Git checkpoint fails

Run:

```bash
git status --short
git diff --cached --check
bash scripts/quality-gate.sh --starter
```

Possible causes include missing local Git author identity, staged credentials, oversized tracked files, an actual whitespace violation or a failing quality gate. Check the exact error; **never disable all whitespace verification** to fix one vendor skill.

For an existing repository, supply exact task files to `scripts/git-checkpoint.sh` or use `--staged` after reviewing the index. A first clean baseline uses `--initial` and `MANIFEST.sha256`; unlisted unignored files are refused. Preserve neighboring user files and investigate inventory differences rather than blanket-staging them.

The distribution's `.gitattributes` exempts **trailing end-of-line spaces only in two upstream Vercel skill directories**. Your own files remain checked.

## Rich does not appear

Rich is bundled in `installer/_vendor`, so the very first `--plan` and `--check` already use the Rich interface. Use `./install.sh --ui-demo` to verify the actual renderer without installing anything. Plain fallback is used if the bundled files are absent or incompatible. `NO_COLOR` disables terminal colors; for a full animation use a real interactive terminal (Ghostty, iTerm2, Terminal.app).

```bash
./install.sh --verify
```

If output is redirected, `NO_COLOR` is set, or the terminal lacks color/TTY capabilities, the installer may present a plain fallback. The output is still functional. See [terminal rendering modes](TERMINAL_UI.md).

## Interrupted install or rollback

1. Inspect `./install.sh --plan` and `.exelia-install/` logs.
2. Continue with `./install.sh --resume`.
3. If an installer-managed local configuration change must be reverted, read [rollback limits](ROLLBACK.md) and use `./install.sh --rollback` only after reviewing its scope.

Rollback does **not** remove Git commits, user work, global software or third-party skills automatically.

---

**Still blocked?** Capture the exact command, final error, `./install.sh --report` and `git status --short`. Redact private paths, tokens and any sensitive content before sharing.

## 2.1.1 workflow diagnostics

- **Empty dispatch:** zero prepared tasks is a successful no-op when no tasks are dependency-ready. Inspect dependencies rather than creating dummy worktrees.
- **Scope refused:** use repository-relative paths without traversal. Aliases, parent/child paths and case aliases cannot run concurrently; escaping symlinks are rejected.
- **Review missing/stale:** `ready_for_review` alone is insufficient. Record an independent `attest-review` with the exact task commit and an existing repository-relative report. Review again after later task commits.
- **Blocked task:** use `scripts/task-ledger.py resume TASK --evidence 'verified resolution'`; history is retained and previous review evidence is cleared.
- **Visual QA fails:** inspect the actual CLI exit status and `.exelia/visual/last-run.json`. Both generated projects use Chromium (Desktop Chrome and Pixel 7). Install the package in `app/` and Chromium in `.exelia/browsers`; do not use global browser binaries as a workaround.
- **Capability drift:** compare selectors, installed names, source records and content hashes. An intentional stack change requires a reviewed refreshed snapshot; unexplained content drift requires investigation.

Actual release checks and limitations are in the [2.1.1 remediation audit](../audits/REMEDIATION_2.1.1.md). Generated browser tests and simulated installation runners are not live execution evidence.
