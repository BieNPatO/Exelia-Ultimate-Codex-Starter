# Strict local installation security policy

1. Project-local installs are the only allowed executable installation actions: `.agents/skills/`, `.exelia-tools/node/`, `.exelia-tools/python/`.
2. The installer never runs `brew install`, `sudo`, `npm -g`, user-level Codex plugin marketplace/add, or writes `~/.codex/config.toml`.
3. Host tools (Codex, Node, Python, Git, Docker/OrbStack) are detected but not automatically installed.
4. The Git baseline is local and requires a passing QA gate. `.gitattributes` exempts upstream Vercel skill Markdown only; application whitespace checks remain enforced.
5. Code downloaded from third-party skill repositories is untrusted until reviewed. The installer does not pretend to audit upstream JavaScript execution or Python packages.
6. Ponytail is a project skill, with AGENTS.md routing, but has NO global plugin hooks or persistent slash-command mode. This restriction is deliberate.
7. `.codex/config.toml` owns the project MCP servers. Authentication and live connectivity are independent of configuration presence. Never commit plaintext API keys.
8. The interactive Impeccable upstream installer may offer multiple scopes; choose only Project. Do not auto-select an unverified CLI argument.
9. Installer-managed npm/pip caches and package prefixes are project-local; no global installed binaries/plugins/skills are touched.
10. `approval_policy=on-request` with workspace-write and network disabled is not full host security. An unconstrained Docker socket grants broad host privileges. Avoid host root mounts and real production credentials.
11. Installer command output logs are stored under ignored `.exelia-install/` with restrictive permissions and best-effort redaction of common bearer headers, token/API-key/password fields and environment assignments. Do not collect real credentials for tests; review logs before sharing externally.
12. Rollback is limited to configuration files backed up before changes; it never uninstalls host software, rewrites Git history or deletes user edits.

For source/history scanning, review attestations, dependency provenance and 2.1.1 residual limits, see the [root security policy](../../SECURITY.md) and [remediation audit](../audits/REMEDIATION_2.1.1.md).

Tool installs use checked-in core/web npm lock profiles (`npm ci`) and hashed Python requirements (`--require-hashes`) under `manifests/tool-dependencies/`. Immutable source revisions and registry provenance are recorded in `manifests/dependency-provenance.json`. Updating these files requires source, integrity and license review plus fresh isolated installation checks; recorded hashes are not a supplier security certification.

## Managed runtime paths

The installer rejects redirected managed directories, caches, state, logs and skill destinations before writing. Local tool launchers require resolved executable paths inside the managed project prefix, except trusted venv Python interpreter links to the running or base interpreter. Python installs isolate pip configuration and use explicit local prefix/cache paths; npm explicitly disables global installation. The interpreter exception is read-only execution; writable directories, package destinations and caches cannot be redirected. These checks do not provide process isolation or prevent a hostile same-user process from concurrently changing the filesystem.

Current compatibility and release-verification evidence is in the [2.1.2 audit](../audits/COMPATIBILITY_2.1.2.md). Historical 2.1.1 evidence remains unchanged.
