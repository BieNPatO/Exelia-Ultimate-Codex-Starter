# Quality, visual testing and measurement

## Product quality gates

Once the approved technology stack is implemented (`app/`, `api/`), run `python3 -m exelia quality plan`. It reads actual `package.json` scripts and Python project files. A gate is `ready` only if the relevant checks exist and it detects no missing expected steps. Run `python3 -m exelia quality configure` to write `quality/commands.txt` **after project approval**, then `bash scripts/quality-gate.sh --app`. Never silently skip a missing test/build/lint command.

## Browser QA

Browser testing is optional until a web app exists. `python3 -m exelia visual plan` shows prerequisites; `... visual setup` writes `app/playwright.config.ts` and a smoke test without overwriting existing files. Install `@playwright/test` only within `app/` after selecting a web app. Install Chromium with `PLAYWRIGHT_BROWSERS_PATH=../.exelia/browsers` from the app directory (never in the user's home cache). Run the app separately, then execute `python3 -m exelia visual run`. The generated test checks desktop and mobile body readiness plus uncaught browser page exceptions; **it is not a full accessibility, security or UX audit**. Expand flows based on documented acceptance criteria. Actual test results are saved to `.exelia/visual/last-run.json`.

## Agent evaluation

Record actual results after a test run:

```bash
python3 -m exelia eval record --task LOGIN-1 --agent qa-engineer --model configured-model --outcome pass --seconds 42 --tokens 5000 --evidence 'E2E run output, commit abc123'
python3 -m exelia eval summary
python3 -m exelia model review --risk high
```

Costs/tokens omitted in input remain unknown and are not inferred. Comparisons are descriptive and require repeatable tasks, known model identities and enough independent samples before claims about superiority.
