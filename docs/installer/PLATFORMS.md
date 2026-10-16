# Supported platforms — strict project-local edition

- **macOS (Apple Silicon/Intel)**: Primary target. OrbStack, Homebrew and Codex are detected, but Exelia does not install/update them.
- **Linux / WSL2**: Best-effort. Python 3.11+, Node 22.20+, Codex CLI, Git and container runtime are host prerequisites. Docker Engine is not installed by this package.
- **Native Windows PowerShell**: Launcher points to WSL2; full native behavior is not declared supported.

`--check` and `--plan` do not write. `--apply` installs only repository-private tools and copies project skills. `--allow-system-changes` is intentionally rejected. Host tools must be prepared outside Exelia if missing.

All third-party node packages are installed under `.exelia-tools/node`; isolated Python binaries under `.exelia-tools/python`. Installer-managed npm/pip caches and writable package prefixes stay project-local; no executable is added to a global package directory.


Python 3.11+ and Node 22.20+ are real installation prerequisites on macOS and Linux. Offline integration fixtures simulate Node/tool responses and do not attest to a real dependency download or the host's suitability. They can run source-level checks on an older or absent host Node without weakening actual installer enforcement.

Standard venv interpreter symlinks to the running Python or its base interpreter are accepted; writable runtime paths remain guarded. Linux CI is configured for Python 3.11, 3.12 and 3.14. Configured CI coverage is not evidence of a hosted run; see the [compatibility audit](../audits/COMPATIBILITY_2.1.2.md) for platforms actually executed. Native Windows remains outside the supported execution matrix.
