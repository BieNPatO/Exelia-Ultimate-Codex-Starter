---
name: python-backend-engineering
description: Use for designing, implementing and maintaining typed, testable, secure Python services or FastAPI APIs, data workflows, migrations and integrations.
---

# Python Backend Engineering

1. First read the approved architecture, API contract, database and security requirements. Select a framework based on requirements; FastAPI is default but not mandatory.
2. Keep business rules separate from transport endpoints and database persistence. Avoid unnecessary class hierarchy/abstraction; adhere to Ponytail where no behavior is lost.
3. Use type hints and explicit Pydantic validation where applicable. Use `uv`, `ruff`, a single typechecker, pytest and HTTPX when those tools fit the actual stack.
4. Async only where appropriate; avoid blocking I/O within asynchronous handlers. Define timeouts, retries with jitter and idempotency for external calls.
5. Design authorization checks, user input validation, error codes, audit trails and secret handling before writing endpoint handlers.
6. Use database transactions and migrations with rollback plans. Never run destructive changes against production from development agent context.
7. Unit and integration tests must cover normal, invalid, unauthorized, concurrency and failure paths; tests use synthetic/seeded data.
8. Run targeted tests before broader gates and record commands, exit statuses and evidence.
9. Avoid storing raw tokens, user secrets, credentials or sensitive response bodies in logs.
10. Version public API changes and update `docs/project/API_SPEC.md` and relevant ADRs.
