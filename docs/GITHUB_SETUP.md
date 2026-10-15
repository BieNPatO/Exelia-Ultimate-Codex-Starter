# Publishing Exelia on GitHub and creating new projects

> [!IMPORTANT]
> **Do not push this starter to an existing private application repository.** Inspect all tracked files, third-party licenses and security settings before making the starter public.

## Publish the starter repository once

1. Make the starter its own empty Git repository. If its installer already initialized local Git, **keep it** — do not delete the `.git` directory.
2. Review `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `installer/_vendor/licenses`, and `docs/installer/SECURITY.md`.
3. Run the offline checks and verify no actual credentials or business data were added:

   ```bash
   python3 -m unittest discover -s tests -v
   python3 tests/integration_smoke.py
   python3 scripts/check-publication.py
   git status --short
   git remote -v
   ```

4. Create a new **empty GitHub repository** (no generated README/LICENSE from GitHub). The repository creator should choose visibility and review supply-chain licensing before publication.
5. Add the remote and push **manually** from the verified repo:

   ```bash
   git remote add origin YOUR_OWN_GITHUB_REPOSITORY_URL
   git branch -M main
   git push -u origin main
   ```

6. In GitHub repository Settings, enable **Template repository**, GitHub Actions, branch protection and vulnerability reporting where appropriate.

## Use for every new application

Select GitHub **Use this template → Create a new repository**, choose its own repository name and clone that new repository. This avoids accidental reuse of the starter's `origin` and produces a clean project history. Then run `./install.sh --plan` and `./install.sh --apply` locally. For an offline ZIP, unpack into a new folder and let the installer initialize local Git.

A plain `git clone` of the upstream starter is appropriate if you want to develop the **starter itself**. If you clone it for a different app, `git remote -v` will still point at the template's upstream origin; create a new remote intentionally before any push.

## Publication limitations

- A GitHub template repo is not an automatically versioned executable marketplace package. Versioned releases/tags and changelogs must be maintained.
- README examples have placeholders and unverified local MCP/auth flows; no secrets in Git.
- The default installer downloads some third-party skills without immutable source pins. This is explicitly disclosed in `SECURITY.md` and must be resolved before claiming fully reproducible or supply-chain-hardened installation.
- Worktrees are not an OS sandbox; use trusted Codex sandbox settings and isolated containers for high-risk operations.
- Downloaded third-party skills are intentionally Git-ignored and must be reviewed/reinstalled per clone. Third-party bundled Rich/Markdown dependencies retain their own licenses. The MIT root license does not change their upstream licensing.
