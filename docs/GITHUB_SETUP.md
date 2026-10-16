# Publishing Exelia on GitHub and creating new projects

> [!IMPORTANT]
> **Do not push this starter to an existing private application repository.** Inspect all tracked files, third-party licenses and security settings before making the starter public.

## Publish the starter repository once — separate manual approval

1. Make the starter its own empty Git repository. If its installer already initialized local Git, **keep it** — do not delete the `.git` directory.
2. Review `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `installer/_vendor/licenses`, and `docs/installer/SECURITY.md`.
3. Review the [2.1.1 candidate audit](audits/REMEDIATION_2.1.1.md), verify the extracted ZIP and checksum, and resolve release blockers. Run the offline checks and verify no actual credentials or business data were added:

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
- Exact package versions, registry integrity locks, Python requirement hashes and immutable skill source commits are recorded under `manifests/`. These do not replace supplier/advisory/legal review or cross-platform installation testing; F12 remains PARTIAL. See [security policy](../SECURITY.md).
- Worktrees are not an OS sandbox; use trusted Codex sandbox settings and isolated containers for high-risk operations.
- Downloaded third-party skills are intentionally Git-ignored and must be reviewed/reinstalled per clone. Third-party bundled Rich/Markdown dependencies retain their own licenses. The MIT root license does not change their upstream licensing.

## Release packaging boundary

Publish only the reviewed source export or verified release commit. Include installer code, tests, configuration templates, original project skills, bundled Rich components and third-party license notices. Exclude `.exelia-tools/`, `.exelia-install/`, `.exelia/`, downloaded external skills, `node_modules/`, virtual environments, logs, secrets and machine-specific evidence. Review the exact tracked/staged paths; do not package the installed working directory wholesale.

The candidate ZIP, checksum, standalone audit and manifest must identify the source revision and actual verification outcomes. Re-extract the ZIP into a new directory, verify executable permissions, bundled first-frame Rich, installer syntax, tests and publication hygiene without reusing the original installation. A successful compression command alone is insufficient evidence.

GitHub Template settings, hosted Actions, branch protection and vulnerability reporting require a real remote and owner action. Mark them `NOT_TESTED` or `BLOCKED` before that exists. This guide grants no permission to create a remote, push, tag publicly or publish a release.

Actions are pinned to full commit SHAs; hosted execution remains a remote-only check. Optional infrastructure requires reviewed image digest variables before Compose configuration can resolve, and selected-image runtime compatibility remains unverified (F16 PARTIAL). Do not use fabricated digests or mutable tags to bypass that requirement.
