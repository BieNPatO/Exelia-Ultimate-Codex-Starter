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

The installer currently downloads some third-party skills by repository reference without immutable upstream commit pins. `manifests/skills.lock.json` captures local content digests, but **does not prove upstream origin**. Until a verified pinned manifest is established, review upstream code before installation or updating. Third-party downloaded skills are deliberately git-ignored and not redistributed by the public starter; they are fetched separately per project and can be checked against a local content lock (`capabilities audit`). Bundled Rich dependency licenses are in `installer/_vendor/licenses/`.
