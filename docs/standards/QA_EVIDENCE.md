# Quality gate evidence contract

Every implementation task includes: task ID, touched files, acceptance criteria, checks expected, checks executed (exact command), exit status, output/log path and independent review result. Use `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`.

The default `quality/commands.txt` contains comments only and intentionally causes `--app` to fail. After project interview, configure real commands for the chosen stack. They run from project root and are trusted repository commands, so review any external edits.

Typical relevant checks (only if selected by stack): Ruff, pytest, Python typing, TypeScript typecheck, frontend unit tests, build, Playwright E2E, Semgrep, Trivy, Gitleaks, OSV. Keep large binary logs in ignored artifacts and Git only the summary + command + status. A quality PASS without an executed tool is not evidence.
