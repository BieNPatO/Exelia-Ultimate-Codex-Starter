# Contributing to Exelia Ultimate Codex Starter

Thanks for improving this template. Contributions should be isolated, reviewable and reproducible.

## Local checks

```bash
./install.sh --plan
python3 scripts/validate-starter.py
python3 -m unittest discover -s tests -v
python3 tests/integration_smoke.py
python3 scripts/check-publication.py
```

Do not commit secrets, generated credentials, local tool binaries or runtime history. Never add a skill or an MCP without documenting its upstream source, permissions, security impact and license.

## Pull requests

- Explain the behavior change and security boundary.
- Include an offline test for new automation capabilities.
- Keep English for all code, prompts, docs and test fixtures.
- No automatic push or deployment in project workflows.
- Keep third-party libraries and their licenses separate from the MIT-licensed starter code.

For user projects, create a repository from the GitHub **Use this template** action, not a PR to this upstream starter.

## Stability release evidence

Keep regression coverage for core-only, React, Python, combined and optional-security configurations. Disposable installation fixtures must not inherit `.exelia-tools`, downloaded skills or runtime caches from the checkout. Preserve failed command output and distinguish simulated integration from upstream downloads and live browsers.

Before a local checkpoint, review an explicit file scope or the staged index; exclude unrelated work. An independent reviewer must inspect the exact committed task revision and provide an existing evidence file through `scripts/task-ledger.py attest-review`. Re-review later code changes; the documented sequential completion exception permits only backlog and the same review-evidence metadata. See [delivery workflow](docs/automation/WORKFLOW.md) and the [2.1.1 audit](docs/audits/REMEDIATION_2.1.1.md).

Dependency updates must be intentional: review the source revision, exact version, integrity metadata and license, update manifests/locks and run clean-export checks. A locally generated skill content digest is not verified upstream provenance. Never silently refresh verified sources to a newer upstream revision.
