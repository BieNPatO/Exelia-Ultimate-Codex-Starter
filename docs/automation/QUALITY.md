# Quality, visual testing and measurement

## Product quality gates

Once the approved technology stack is implemented (`app/`, `api/`), run `python3 -m exelia quality plan`. It reads actual `package.json` scripts and Python project files. A gate is `ready` only if the relevant checks exist and it detects no missing expected steps. Run `python3 -m exelia quality configure` to write `quality/commands.txt` **after project approval**, then `bash scripts/quality-gate.sh --app`. Never silently skip a missing test/build/lint command.

## Browser QA

Browser testing is optional until a web app exists. `python3 -m exelia visual plan` shows prerequisites; `... visual setup` writes `app/playwright.config.ts` and a smoke test without overwriting existing files. Install `@playwright/test` only within `app/` after selecting a web app. Install Chromium with `PLAYWRIGHT_BROWSERS_PATH=../.exelia/browsers` from the app directory (never in the user's home cache). Run the app separately, then execute `python3 -m exelia visual run`. Both generated projects use Chromium: Desktop Chrome and Pixel 7. Do not substitute a WebKit-based device while installing only Chromium. The generated test checks desktop and mobile body readiness plus uncaught browser page exceptions; **it is not a full accessibility, security or UX audit**. Expand flows based on documented acceptance criteria. Actual test results are saved to `.exelia/visual/last-run.json`.

## Agent evaluation

Record actual results after a test run:

```bash
python3 -m exelia eval record --task LOGIN-1 --agent qa-engineer --model configured-model --outcome pass --seconds 42 --tokens 5000 --evidence 'E2E run output, commit abc123'
python3 -m exelia eval summary
python3 -m exelia model review --risk high
```

Costs/tokens omitted in input remain unknown and are not inferred. Comparisons are descriptive and require repeatable tasks, known model identities and enough independent samples before claims about superiority.

## Failure and evidence semantics

`python3 -m exelia visual run` returns a nonzero process status when its runner fails. Missing local runner/package, invalid configuration, interrupted execution or missing browser binaries must remain failures rather than successful quality evidence. Do not replace missing project tools with global tools. The local Playwright process reports browser/configuration errors; inspect its exit code and recorded output.

A generated smoke file is implemented setup, not executed browser QA. Report unexecuted browser runs as `NOT_TESTED` (or `NOT_RUN` in the task ledger), including the missing local package, browser or running application. Synthetic CLI runners verify exit propagation, not real browser rendering. See the [2.1.1 audit](../audits/REMEDIATION_2.1.1.md) for actual release checks.

For 2.1.1, the generated Desktop Chrome and Pixel 7 smoke tests were also executed in a real local Chromium against an isolated synthetic localhost fixture on macOS: 2/2 passed. This covers browser startup and the generated smoke flow only; no product application acceptance, production service or platform matrix is implied. Exact commands and evidence are in the [remediation audit](../audits/REMEDIATION_2.1.1.md).
