# Infrastructure template catalog

The `infrastructure/compose/dev-services.yml` file has optional Compose profiles: `db`, `cache`, `mail`, `object`. They are dormant until the project requirements select them.

Example for database only, run from project root when Docker daemon available:

```bash
docker compose -p "$(basename "$PWD")" -f infrastructure/compose/dev-services.yml --profile db up -d
```

Select ports and credentials from environment variables. These local development recipes are **not production manifests**. Before using them, incorporate only required services into an app-specific compose file and configure proper health checks, backups, resource limits, test databases and secrets.
