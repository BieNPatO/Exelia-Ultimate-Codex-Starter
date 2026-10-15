# Ponytail — local skill, global plugin and hook trust

[← Start here](../../START_HERE.md) · [Troubleshooting](TROUBLESHOOTING.md) · [Security policy](SECURITY.md)

> [!IMPORTANT]
> **Exelia uses Ponytail as a project-local skill, not as a global Codex plugin.** You do not need to install or trust global Ponytail hooks to use the starter.

## Two different integration modes

| Capability | Exelia project skill | Separate global plugin |
| :--- | :--- | :--- |
| Installed by Exelia | **Yes**, under `.agents/skills/ponytail/` | **No** |
| Read via `AGENTS.md` | **Yes**, for relevant coding tasks | May add its own behavior |
| Lifecycle hooks and plugin commands | **Not included** | May be available depending on installed plugin/version |
| Hook trust required for Exelia setup | **No** | Requires your independent decision |
| User-level Codex config modified by Exelia | **No** | **No** — not managed by Exelia |

## Verify the project skill

```bash
./install.sh --verify
```

The installer checks for a local `SKILL.md` with basic frontmatter. This does **not** exercise the full global plugin behavior.

During coding, follow the **local** skill's minimal-change guidance while retaining required testing, accessibility, security, robustness and acceptance criteria.

## When a hook asks for trust

**Do not approve based on the name alone.** Inspect:

1. The **source** (repository location or installed plugin source).
2. The **exact command** and what it can read, modify or execute.
3. Whether the hook belongs to **Ponytail** or to **Exelia's own hook**.

A global Ponytail hook trust prompt is unrelated to the local skill installation. You can decline it and still use project-local Ponytail.

## Exelia has a separate project hook

`.codex/hooks.json` references `.codex/hooks/session_start.py`. This **Exelia SessionStart hook** prints project phase, documentation approval and language reminders; it is **not** a Ponytail hook. Review the script before granting trust.

## Avoiding duplicated instructions

An existing global Ponytail plugin may coexist with the local skill. Their instructions can overlap. Exelia **does not automatically switch off** or change global plugins. If results appear duplicated or contradictory, inspect the active plugin/hooks and choose the intended mode for that session.

> [!WARNING]
> The local skill does **not** provide all features of the separately installed plugin. Do not advertise or assume its dynamic modes, slash commands or lifecycle hooks are working in project-local mode.
