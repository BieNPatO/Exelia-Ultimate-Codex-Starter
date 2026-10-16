# Supported platforms — strict project-local edition

- **macOS (Apple Silicon/Intel)**: Primary target. OrbStack, Homebrew and Codex are detected, but Exelia does not install/update them.
- **Linux / WSL2**: Best-effort. Python 3.11+, Node 22.20+, Codex CLI, Git and container runtime are host prerequisites. Docker Engine is not installed by this package.
- **Native Windows PowerShell**: Launcher points to WSL2; full native behavior is not declared supported.

`--check` and `--plan` do not write. `--apply` installs only repository-private tools and copies project skills. `--allow-system-changes` is intentionally rejected. Host tools must be prepared outside Exelia if missing.

All third-party node packages are installed under `.exelia-tools/node`; isolated Python binaries under `.exelia-tools/python`. User npm/pip caches might still be used by their respective installers, but no executable is added to a global package directory.
