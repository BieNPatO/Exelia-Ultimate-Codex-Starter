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
