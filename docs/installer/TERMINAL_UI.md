# Installer terminal UI — behavior

The terminal is rendered by `installer/ui.py` and used by `installer/cli.py`. All dependencies, including Rich, are local to the **repository**.

## Rendering modes

| Mode | Behavior |
|---|---|
| First screen in a new repository | Bundled Rich starts instantly, without pip or network |
| Progress during installation | Rich `Panel`, `Table`, `Rule` and live `Progress` spinner/bar |
| `--check` / `--plan` | Read-only; bundled Rich is available immediately, including offline |
| `--json` | Pure machine-readable stdout; no Rich tables, spinners or banners |
| `--quiet` | Suppress decorative progress |
| `NO_COLOR=1` or non-TTY | No ANSI color codes; structured layout without dynamic animation |
| `--verbose` | Include plan shell commands and step log tails on failure |

The renderer is `Rich · bundled / project-local` from the very first frame, or `Plain · fallback` if the bundled files are missing. Never use a globally installed Rich to masquerade as project-local. `--ui-demo` demonstrates the actual renderer without downloads.

## Status semantics

- **READY:** locally installed tool/skill detected, or a host prerequisite verified. Does not mean a live integration request succeeded.
- **CONFIGURED:** a project MCP or local hook definition exists; connection/trust is **not** verified.
- **ACTION:** interactive manual step needed (for example, Impeccable installation with Codex / Project selected).
- **WARNING / BLOCKED / FAILED:** attention required, see reason and local step log.
- **NOT TESTED:** live Codex multiagent execution and remote MCP calls cannot be verified offline.

The final panel shows completion/partial state, verified skills count, Git checkpoint, local-only guarantee, precise next steps and report path. `PARTIAL` is expected when Impeccable's interactive project installation is deferred; it is not silently treated as success.

## Screens and controls

- `./install.sh --check` — inventory.
- `./install.sh --plan` — planned project actions (use `--verbose` to print commands).
- `./install.sh --apply` — one approval before provisioning, progress for each step.
- `./install.sh --verify` — technical checks without changing the project.
- `./install.sh --resume` — incremental repair without repeating healthy steps.
- `./install.sh --report` — persisted JSON report.

The terminal UI is presentation-only. It does not alter installation scope, authorization policy or existing global configuration.

## UI preview (read-only)

```bash
./install.sh --ui-demo
```

Displays the **real UI renderer** with clearly labeled example data, not a design mockup.
For detailed inventories and exact commands, use `./install.sh --plan --verbose`.
On a non-interactive terminal, animations are naturally disabled. If the bundled
renderer cannot be loaded, a plain-text fallback preserves all installer commands.
