"""Prepare browser QA for an explicitly selected web application, never global npm."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
from .common import ROOT, approved, load, save, utc

PLAYWRIGHT_CONFIG = '''import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  retries: 1,
  reporter: [['list'], ['html', { outputFolder: '../.exelia/visual-report', open: 'never' }]],
  use: {
    baseURL: process.env.EXELIA_TEST_URL ?? 'http://127.0.0.1:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
});
'''

SMOKE_TEST = '''import { test, expect } from '@playwright/test';

test('home route loads on desktop and mobile without uncaught page errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('body')).toBeVisible();
  await expect(page.locator('body')).not.toBeEmpty();
  expect(errors).toEqual([]);
  // TODO: after product discovery, add auth, checkout, accessibility and keyboard flows.
  // Do not treat this smoke test as a complete accessibility/security audit.
});
'''


def inspect(root: Path = ROOT):
    cfg = load(root / 'project.config.json', {})
    frontend = ((cfg.get('stack') or {}).get('frontend') or '').lower()
    directory = root / 'app'
    return {'eligible': bool(frontend) and (directory / 'package.json').exists(),
            'frontend': frontend or None, 'app_dir': 'app',
            'config_exists': (directory / 'playwright.config.ts').exists(),
            'smoke_exists': (directory / 'tests/e2e/smoke.spec.ts').exists(),
            'package_installed': (directory / 'node_modules/@playwright/test/package.json').is_file(),
            'browser_path': '.exelia/browsers',
            'note': 'Browser installation and E2E execution require explicit approval and a running app.'}


def setup(root: Path = ROOT, *, overwrite=False):
    approved(root)
    status = inspect(root)
    if not status['eligible']:
        raise RuntimeError('Select a frontend and create app/package.json first.')
    files = {root / 'app/playwright.config.ts': PLAYWRIGHT_CONFIG,
             root / 'app/tests/e2e/smoke.spec.ts': SMOKE_TEST}
    for path in files:
        if path.exists() and not overwrite:
            raise RuntimeError('Refusing to overwrite existing test file: ' + str(path))
    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding='utf-8')
    return {'written': [str(x.relative_to(root)) for x in files],
            'next': 'From app/: npm install --save-dev --save-exact @playwright/test; PLAYWRIGHT_BROWSERS_PATH=../.exelia/browsers npx --no-install playwright install chromium'}


def run(root: Path = ROOT):
    approved(root)
    status = inspect(root)
    if not status['eligible'] or not status['package_installed'] or not status['smoke_exists'] or not status['config_exists']:
        raise RuntimeError('E2E not ready: run visual plan/setup and install project-local @playwright/test explicitly.')
    binary = root / 'app/node_modules/.bin/playwright'
    if not binary.exists():
        raise RuntimeError('Local Playwright binary is absent; global tools will not be used.')
    env = dict(os.environ)
    env['PLAYWRIGHT_BROWSERS_PATH'] = str(root / '.exelia/browsers')
    result = subprocess.run([str(binary), 'test'], cwd=root / 'app', env=env, capture_output=True, text=True)
    record = {'timestamp': utc(), 'status': 'PASS' if result.returncode == 0 else 'FAIL', 'exit_code': result.returncode,
              'command': 'app/node_modules/.bin/playwright test', 'output_tail': (result.stdout + '\n' + result.stderr)[-1800:]}
    file = root / '.exelia/visual/last-run.json'
    save(file, record)
    return record
