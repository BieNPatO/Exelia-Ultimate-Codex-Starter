# Security policy

## Reporting

Please report a potential security problem privately to the maintainers using GitHub's **Report a vulnerability** feature, if enabled. Do not publish exploit details or credentials in Issues.

## Trust boundaries

- This repository is a **coding harness template**, not a security sandbox.
- Git worktrees isolate Git working directories, not OS processes, filesystem privileges or secrets.
- Codex agents inherit their session permissions; declared read-only roles are advisory.
- By default Codex uses `workspace-write`, `on-request` and network off. Never install tools or skills globally via this template. Browser downloads use `.exelia/browsers`.
- Review all downloaded third-party skills and installer commands before first execution.
- No automatic push, production deployment, privileged Docker socket mount or host filesystem mutation outside the project.
- Documentation approval evidence is a workflow marker, not cryptographic proof of identity.
- `~/.codex` authentication, ChatGPT sessions and global hooks are managed by the user, not Exelia.

## Supply chain

Tool versions and immutable skill source commits are recorded in `manifests/components.json`. Node installations use `npm ci` with the core/web lock profiles in `manifests/tool-dependencies/`; Python installations use `requirements-uv.txt` and `requirements-ruff.txt` with `--require-hashes`. Registry integrity metadata and source records are documented in [dependency-provenance.json](manifests/dependency-provenance.json). `manifests/skills.lock.json` separately captures installed skill content for drift detection. A content digest does not prove supplier authenticity or code safety.

Already-present binaries accepted by a readiness probe are not automatically upgraded or version-attested; use a reviewed explicit project-local reinstall to obtain the pinned version. Node 22.20+ is required by the pinned skills CLI.

F12 remains PARTIAL: full supplier, advisory, licensing and all-platform verification are incomplete. Review source and lock changes before updates; do not silently replace pinned dependencies. Downloaded external skills remain Git-ignored and are not redistributed. Bundled Rich dependency licenses are in `installer/_vendor/licenses/`.

GitHub Actions use full source commit SHAs. Optional development services require operator-supplied reviewed image digests through `POSTGRES_DIGEST`, `REDIS_DIGEST`, `MAILPIT_DIGEST` and `MINIO_DIGEST`; no default digest is claimed verified. F16 remains PARTIAL until the selected images, permissions, volumes and healthchecks are tested. Ports bind to localhost and passwords must be development-only. No service startup is implied by configuration validation.

## Release controls and limits

Checkpoint, integration and publication checks share sensitive-filename protection at every directory depth. Non-secret `.env.example` templates may be allowed; real `.env` variants, private keys and recognized credential artifacts remain protected. Installer logs redact common authorization, token, API-key, password and environment formats and use restrictive local permissions. Redaction is best effort: do not collect real authentication output unnecessarily, and inspect logs before sharing.

`python3 scripts/check-publication.py` scans intended tracked source and reachable local Git history; a source export has no history to inspect. It excludes runtime directories, downloaded external skills and credential files from acceptable release content. Synthetic regression fixtures exercise known patterns. Heuristic scanning cannot prove absence of secrets; a dedicated external secret scanner and remote-only security settings are separate checks, recorded honestly in the [release audit](docs/audits/REMEDIATION_2.1.1.md).

Task review requires an independent identifier, PASS result, exact commit, timestamp, existing local evidence file and no outstanding findings. A later source commit invalidates the attestation. Sequential main-only tasks have a narrow completion exception for linear backlog/evidence-only commits; [workflow](docs/automation/WORKFLOW.md) documents the allowed paths and stale-review checks. These records cannot authenticate reviewer identities and do not replace actual independent review. Product documentation approval remains human-controlled.

## Support and publication status

Version 2.1.2 is a release candidate requiring separate final audit; consult the [compatibility audit](docs/audits/COMPATIBILITY_2.1.2.md) for current verification. No public GitHub publication, branch protection, vulnerability-reporting setting or hosted CI result is implied by local checks. Platform, network-download, dependency provenance and live-browser limitations are listed in the release audit. Report unknowns rather than treating a configured integration as verified.

## Compatibility safeguards

Project-local writable directories, caches, packages and executable destinations remain confined. A venv's Python interpreter link may resolve to the current interpreter or its trusted base interpreter; this read-only execution exception does not permit redirecting installation targets. It is not protection against a hostile same-user process racing filesystem checks.

Publication checks use tracked source in Git and validate an export's `MANIFEST.sha256` inventory. Only current-interpreter bytecode whose payload exactly matches compilation of an unchanged inventoried Python source may be treated as incidental post-test output. These compiler-verified caches are excluded from source secret scanning because they are generated output; inventoried source remains scanned. Unknown or modified cache payloads are rejected. This exception never applies to release ZIP members: run `python3 scripts/check-publication.py --archive /path/to/release.zip` to inspect actual contents. Runtime files, secrets, unsafe paths and symlinks remain prohibited in archives. Inventory hashes and pattern matching do not authenticate the supplier or prove absence of secrets.

Release verification should set `PYTHONDONTWRITEBYTECODE=1`. A timed-out initial checkpoint fails and its process group is terminated; it cannot be treated as approved QA evidence. Resume retries the gate rather than approving unfinished tests. See [timeout settings](docs/installer/TROUBLESHOOTING.md#checkpoint-and-integration-timeouts).
