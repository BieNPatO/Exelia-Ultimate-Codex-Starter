# Git workflow and versioning

Git is mandatory. Run `./scripts/bootstrap.sh` in a new project and keep app source/version history separate from the distribution's `VERSION`.

## Working conventions

- Commit baseline after starter self-tests: `./scripts/git-checkpoint.sh --starter "chore: initialize Exelia starter"`.
- During discovery, `docs` commits may be created after `./scripts/quality-gate.sh --docs`. This **does not substitute** for the one-time human approval.
- After approval, use `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `chore` Conventional Commits; reference task IDs in body or changelog.
- Work on scoped branches: `feature/AUTH-001-login`, `fix/BUG-004-timeout`; branch names should be stable and clear.
- Use short-lived worktrees for isolated parallel edits; never allow two agents to edit overlapping files without coordinator ownership.
- Run real app quality commands before local commits: `./scripts/git-checkpoint.sh --app "feat(auth): add login flow"`.
- Tag validated app releases locally with `./scripts/release-local.sh v0.1.0`. Tags are separate from starter version.
- Update `CHANGELOG.md` with user-impacting changes and relevant migrations.
- Never automatically `git push`, force push, rebase public history, delete branches or publish a release. Remote setup/push require explicit human instruction.

## Safeguards and limitations

`git-checkpoint.sh` stages the entire worktree and checks for common secret paths (excluding safe `.env.example` templates), selected signatures, large files, whitespace and quality gates. It is a practical safety net, not full secret scanning. Enable Gitleaks in CI for projects that handle credentials. Git hooks and assistant instruction text are not access control. After checkpoint it updates `tasks/STATE.json` with the commit hash, which will appear in the following checkpoint; Git itself remains authoritative.
