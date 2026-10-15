# Agent autonomy and security boundaries

The starter asks Codex to use `approval_policy = "on-request"` and `sandbox_mode = "workspace-write"`, allowing normal workspace work while requiring confirmation for actions outside the sandbox. This is not identical to an isolated container or mandatory no-network runtime. Codex workspace network access is disabled by default; the user separately reviews the local installer plan before downloading dependencies.

## Required boundaries

1. Start Codex only from a trusted project root. Project-specific config and hooks require trust; inspect `AGENTS.md`, `.codex/config.toml`, and `.codex/hooks.json` before trusting.
2. Do **not** enable `danger-full-access`, `--yolo` or broad write access to the macOS home directory to make an install succeed.
3. OrbStack/Docker services are development dependencies. A mounted Docker socket can grant host-level power regardless of Codex instructions. The default Docker Compose recipes **do not mount the Docker socket**, run no privileged containers and bind dev ports to loopback.
4. No production credentials, user data, payment keys or secrets in project files, logs, agent messages or Git. Maintain `.env.example`, `.gitignore`, secret stores and short-lived test tokens.
5. Do not blindly execute scripts from the internet. Third-party skill installers are explicit opt-in in `setup-integrations.sh`. Review publisher, source, license and startup hooks.
6. Keep remote Git pushes, production deploys, external communications, migrations against live databases and destructive host operations out of unattended scope.
7. Tools and MCP calls use their own permissions; `approval_policy = "on-request"` does not override host access policy. If blocked, report BLOCKED and suggest a bounded remedy, not a bypass.
8. SQL/database MCP must be read-only and pointed at disposable local databases unless separately authorized.
9. Hook-based command blocking is defense-in-depth and may not cover all execution paths. Rely on sandbox and OS/filesystem restrictions for enforced boundaries.

## Verification

Run `scripts/doctor.sh`, `docker context ls`, check `docker compose config`, verify which network ports are exposed, and inspect actual effective Codex permissions on the user's Mac. No such verification is possible from a prebuilt ZIP.
