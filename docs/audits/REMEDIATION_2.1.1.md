# Exelia Ultimate Codex Starter 2.1.1 — Remediation audit

## Executive summary

**SOURCE VERIFICATION PASS; final archive identity is recorded in the companion external release artifacts.** All HIGH findings and independent-review blockers are fixed and regression-tested. F12/F16 retain explicit PARTIAL limitations. Public GitHub publication is not authorized.

## Original baseline

The original post-install audit targeted commit `2d78cd0130123187e9dc6766a602049f9235e549`: 16 findings (2 HIGH, 11 MEDIUM, 3 LOW). It reproduced scope aliases, false Visual QA success, broad staging, capabilities drift, installed/discovered test failures, empty dispatch errors and credential-guard gaps. Installation-local logs and machine data are excluded from the distribution.

## Finding resolutions

| Finding | Status | Changed files | Regression evidence | Residual risk |
|---|---|---|---|---|
| F01 | FIXED | exelia/worktrees.py | test_remediation_backend.py, test_remediation_qa.py | Case aliases are conservatively serialized; worktrees are not process sandboxes. |
| F02 | FIXED | exelia/__main__.py, exelia/visual.py | test_remediation_visual.py | Runner output remains diagnostic; smoke coverage is limited. |
| F03 | FIXED | scripts/git-checkpoint.sh, scripts/checkpoint.py, installer/engine.py | test_remediation_devops.py, integration_smoke.py | Prepared index selection is a human/coordinator assertion; failed gate mutations remain for inspection. |
| F04 | FIXED | exelia/capabilities.py | test_remediation_backend.py | Registry metadata and hashes do not authenticate suppliers. |
| F05 | FIXED | tests/integration_smoke.py | integration_smoke.py | Offline lifecycle simulation mocks external downloads; real bounded dependency checks are separate. |
| F06 | FIXED | tests/test_starter.py, tests/test_exelia_automation.py, tests/test_post_discovery.py | test_post_discovery.py, test_starter.py | Representative stacks; no claim every framework/version is tested. |
| F07 | FIXED | exelia/dispatch.py | test_remediation_backend.py, test_remediation_qa.py | Prepare still requires product documentation approval. |
| F08 | FIXED | exelia/visual.py, docs/automation/QUALITY.md | test_remediation_visual.py; isolated real desktop/mobile smoke | Synthetic application smoke does not validate a future product. |
| F09 | FIXED | exelia/security.py, installer/engine.py | test_remediation_security.py | Unknown/obfuscated credentials cannot be ruled out; authentication diagnostics are intentionally suppressed. |
| F10 | FIXED | exelia/security.py, exelia/worktrees.py, scripts/checkpoint.py, scripts/check-publication.py | test_remediation_security.py, test_remediation_backend.py, test_remediation_devops.py | Example suffix exemption is filename-only; content remains scanned. |
| F11 | FIXED | scripts/task-ledger.py, exelia/worktrees.py | test_remediation_backend.py, test_remediation_qa.py | Reviewer identity and evidence are procedural attestations, not authenticated proof. |
| F12 | PARTIAL | manifests/components.json, manifests/tool-dependencies/, manifests/dependency-provenance.json, installer/localtools.py, installer/engine.py | test_remediation_devops.py; bounded real dependency install checks | Full supplier code/advisory/legal audit and all-platform/optional installs are not complete; installed tool binaries are not version-attested automatically; generator repository HEAD is not package-build attestation. |
| F13 | FIXED | scripts/check-publication.py, exelia/security.py | test_remediation_security.py; publication and Gitleaks checks | Heuristic scans cover reachable local history only and cannot certify absence of secrets. |
| F14 | FIXED | scripts/task-ledger.py | test_remediation_backend.py | Dependencies remain required before start. |
| F15 | FIXED | scripts/project-state.py | test_remediation_backend.py | Extensions, private-use and full registry canonicalization are deliberately unsupported. |
| F16 | PARTIAL | infrastructure/compose/dev-services.yml, .github/workflows/starter-ci.yml | test_remediation_devops.py; Compose config only | Image digests/compatibility must be selected and verified by project; no service was started; hosted Actions/OS matrix untested. |

## Root causes and implementation changes

### F01

Scope aliases were compared as raw strings; integration trusted branch-controlled paths and rename destinations. Canonical ownership frozen at prepare; traversal/escape and rebinding rejected; every rename endpoint checked; lexical paths and resolved symlink targets both checked; exact reviewed checkout bound through QA.

### F02

CLI always returned zero after runner result. Propagate runner exit/signal; missing configuration and runner fail; keyboard interruption returns 130.

### F03

Unconditional broad staging captured unrelated work. Exact files, explicitly reviewed index or initial source inventory; bind index and HEAD across QA; credential checks shared.

### F04

Audit iterated only old selected entries and lost optional selectors. Retain selectors; compare complete selected name sets, missing content, hashes, stack and recorded sources/revisions.

### F05

Copied downloaded skills without their runtimes made installed fixtures falsely appear ready. Exclude runtime and external skills; create isolated deterministic installer fixtures and source inventory.

### F06

Pre-discovery expectations read mutable destination configuration. Move state-dependent checks into fixtures; exercise core, React, Python, combined and security configurations.

### F07

Empty prepare accessed absent packets key. Return zero packets/prepared tasks without creating runtime files.

### F08

iPhone descriptor required WebKit but instructions installed Chromium. Use Pixel 7 Chromium with Desktop Chrome and local browser cache.

### F09

Single-value regex leaked quoted, bearer and multiline output. Discard authentication-bearing subprocess output; recognize flags/credential URIs; atomic 0600 logs and 0700 directory.

### F10

Root-specific filename comparisons missed nested credentials. Shared basename/component policy at any depth, with explicit non-secret example suffixes.

### F11

Ready status stood in for review and QA could cover another commit/tree. Record reviewer/result/exact commit/time/evidence/findings; reject stale/nonindependent review; bind checkout and require integrated reviewed commit before completion QA.

### F12

Bare package names and mutable repository sources allowed silent upstream drift. Exact npm versions and integrity locks via npm ci; Python release hashes; immutable skill source references; writable runtime paths and executables confined to project; isolated package-manager routing; provenance/update policy.

### F13

Narrow patterns skipped token families/history and deduplicated historical pathnames. Scan tracked/export content and every historical tree pathname plus reachable blobs; reject runtime/downloaded skills; dedicated Gitleaks run separately.

### F14

Blocked tasks had no supported outgoing recovery transition. Explicit evidence-bearing blocked-to-todo resume preserves history and clears stale review.

### F15

Locale regex only accepted basic language and uppercase region. Document and validate common BCP47 language/script/region/variant subset; conversation language separate.

### F16

Actions tags/images latest and known development password defaults were mutable/unsafe. Verified action SHAs; require explicitly reviewed image digest variables and development passwords; localhost ports remain explicit.

## Regression tests and command execution

The ledger retains intermediate failures, including red regression runs and sandbox-denied browser execution. A later PASS does not erase the earlier observation. Test methods, parameterized cases and repeated executions are distinct counts.

| Check | Actual command | Exit | Outcome |
|---|---|---:|---|
| browser-live-escalated | `python3 -m exelia visual run` | 0 | PASS |
| browser-live | `python3 -m exelia visual run` | 1 | FAIL |
| clean-source-gate | `bash scripts/quality-gate.sh --starter` | 0 | PASS |
| clean-source-gitleaks | `gitleaks dir --redact --no-banner --report-format json --report-path <temporary-report> .` | 0 | PASS |
| clean-source-integration | `python3 tests/integration_smoke.py` | 0 | PASS |
| clean-source-publication | `python3 scripts/check-publication.py` | 0 | PASS |
| F05-installed-baseline-reproduction | `python3 tests/integration_smoke.py` | 1 | FAIL |
| final-installed-integration | `python3 tests/integration_smoke.py` | 0 | PASS |
| final-publication-working | `python3 scripts/check-publication.py` | 0 | PASS |
| final-starter-gate | `bash scripts/quality-gate.sh --starter` | 0 | PASS |
| installed-smoke-before | `python3 tests/integration_smoke.py` | 1 | FAIL |
| installer-recovery | `python3 -m unittest discover -s tests -p test_installer_recovery.py -v` | 0 | PASS |
|  | `python3 -m unittest discover -s tests -p test_exelia_automation.py -v` | 1 | FAIL |
| publication-current | `python3 scripts/check-publication.py` | 0 | PASS |
| qa-final | `python3 -m unittest discover -s tests -p test_remediation_qa.py -v` | 0 | PASS |
| rc-clean-gate | `bash scripts/quality-gate.sh --starter` | 0 | PASS |
| rc-clean-gitleaks | `gitleaks dir --redact --no-banner --report-format json --report-path <temporary-report> .` | 0 | PASS |
| rc-clean-integration | `python3 tests/integration_smoke.py` | 0 | PASS |
| rc-clean-publication | `python3 scripts/check-publication.py` | 0 | PASS |
| rc-installed-integration | `python3 tests/integration_smoke.py` | 0 | PASS |
| rc-product-gate | `bash scripts/quality-gate.sh --app` | 1 | BLOCKED (expected rejection) |
| rc-rich-bootstrap | `python3 -S -m installer --plan --json` | 0 | PASS |
| rc-source-gate | `bash scripts/quality-gate.sh --starter` | 0 | PASS |
| rc-syntax | `python3 -c from pathlib import Path; import subprocess; files=list(Path('exelia').glob('*.py'))+list(Path('installer').glob('*.py'))+list(Path('scripts').glob('*.py'))+list(Path('tests').glob('*.py')); [compile(p.read_text(),str(p),'exec') for p in files]; scripts=[Path('install.sh'),*Path('scripts').glob('*.sh')]; [subprocess.run(['bash','-n',str(p)],check=True) for p in scripts]; print('PASS:',len(files),'Python sources;',len(scripts),'shell scripts')` | 0 | PASS |
| release-final-gate | `bash scripts/quality-gate.sh --starter` | 1 | FAIL |
| starter-gate-regression | `python3 -m unittest discover -s tests -p test_starter.py -v` | 0 | PASS |
| syntax-final | `python3 -c from pathlib import Path; import subprocess; files=list(Path('exelia').glob('*.py'))+list(Path('installer').glob('*.py'))+list(Path('scripts').glob('*.py'))+list(Path('tests').glob('*.py')); [compile(p.read_text(),str(p),'exec') for p in files]; scripts=[Path('install.sh'),*Path('scripts').glob('*.sh')]; [subprocess.run(['bash','-n',str(p)],check=True) for p in scripts]; print('PASS:',len(files),'Python sources compiled in memory;',len(scripts),'shell scripts parsed')` | 0 | PASS |
| unit-final-candidate | `python3 -m unittest discover -s tests -v` | 0 | PASS |
| unit-initial | `python3 -m unittest discover -s tests -v` | 1 | FAIL |
| unit-progress | `python3 -m unittest discover -s tests -v` | 0 | PASS |
| visual-final | `python3 -m unittest discover -s tests -p test_remediation_visual.py -v` | 0 | PASS |

## Native agent execution

These are actual native Codex role invocations, confirmed by live agent listing; generated dispatch packets are not counted. Only the listed roles executed, although all twelve role definitions remain. Agents share inherited host permissions.

| Task | Role | Observed execution |
|---|---|---|
| backend_fixes | backend_engineer | completed implementation and review remediation |
| devops_fixes | devops_engineer | interrupted by usage limit before edits; recovered by separate agent |
| devops_recovery | devops_engineer | implementation and verified metadata retrieval |
| security_fixes | security_auditor | explicitly assigned implementation; not independent final reviewer |
| release_docs | documentation_agent | completed |
| qa_verification | qa_engineer | independent regressions found two HIGH defects |
| independent_security | security_auditor | completed independent review PASS_WITH_DOCUMENTED_LIMITATIONS; all reproduced findings fixed |
| independent_code_review | code_reviewer | completed independent review PASS_CODE_REVIEW; all reproduced findings fixed |

## Independent reviews

QA found scope rebinding and checkout/QA commit mismatch; code review found rename-source ownership, out-of-scope symlink and premature completion gaps; security review found multiline redaction, historical filename deduplication and checkpoint index mutation gaps. Permanent regressions and fixes were requested. Final independent code review: **PASS_CODE_REVIEW**. Final independent security review: **PASS_WITH_DOCUMENTED_LIMITATIONS**. Both found no unresolved source blocker; their source snapshots and check evidence appear below. Review identifiers are procedural attestations.

## Dependency provenance

See [dependency-provenance.json](../../manifests/dependency-provenance.json) and checked-in tool manifests/locks. Exact package versions, registry integrity hashes and Git source revisions reduce drift. They do not establish supplier authenticity, code safety, licensing rights or complete cross-platform reproducibility. Controlled updates must regenerate locks, inspect diff/provenance and rerun installation/security/release checks.

## Git safety

Initial branch: `main`; initial worktree and index were clean. No unrelated user work was discarded. Explicit file selection or reviewed index is required for checkpoints. Application discovery approval remains false. Maintenance tasks are tracked separately from product approval and retained for review; the application completion gate is not weakened to mark starter work done. No push, remote, history rewrite, service startup or production operation was performed.

## Known limitations

- No remote exists: GitHub Template settings, branch protection, hosted CI and publication approval remain BLOCKED.
- No product application is selected; product documentation remains intentionally unapproved.
- Live browser smoke uses a synthetic isolated local fixture, not production/product acceptance.
- Third-party source IDs and registry hashes are not supplier security/legal certification.
- No infrastructure was started; image digests and runtime permissions need project-specific validation.
- Linux/Windows/WSL and full supplier vulnerability review NOT_TESTED.

## Release readiness and packaging

The verified source is eligible for final ZIP creation and a separate independent audit. The source report necessarily precedes its own release commit. The companion external `Exelia-Ultimate-Codex-Starter-v2.1.1-AUDIT_REPORT.md` and `Exelia-Ultimate-Codex-Starter-v2.1.1-MANIFEST.json` bind the final commit, ZIP checksum and post-extraction checks. **The release is READY FOR FINAL INDEPENDENT AUDIT only when those fresh archive checks pass. Public GitHub publication approval remains pending.**

## Follow-up recommendations

Complete separate final independent audit, choose and validate infrastructure digests per project, review supplier advisories/licenses, run the platform CI matrix, and configure GitHub Template/security settings only after separate explicit publication authorization.

Machine-readable evidence: [REMEDIATION_2.1.1.json](REMEDIATION_2.1.1.json).

## Final source evidence

- Full source gate: **111/111 unittest methods PASS**, exit 0. The same 111 methods pass in the clean export. Counts are per full run, not added across repeated executions.
- Installed-state and clean-export installation simulations: **PASS**, exit 0; actual initial Git checkpoint/resume, downloads mocked.
- Recovery fixtures: actual synthetic failed subprocess, resumed journal/stale lock and timeout state are exercised.
- Actual Chromium smoke: **2/2 PASS** (Desktop Chrome and Pixel 7), isolated synthetic localhost app with project-local Playwright1.64.1/browsers. Initial sandbox browser refusal and nonzero result were retained before approved retry.
- Real bounded dependency checks: core npm `ci`, one immutable core skill copy and hash-locked Ruff install PASS. A real offline synthetic wheel verifies pip cannot honor hostile `PIP_TARGET`/`PIP_USER` routing outside the disposable venv.
- Existing host Gitleaks8.30.1 scanned baseline reachable history and the final clean source export: exit0, no detections. It was not installed or modified by this mission. This is limited detection evidence, not a no-secrets guarantee.
- Syntax: 38 first-party Python files compile in memory and 10 shell scripts parse. Starter has no separately configured mandatory lint/type/build command; no product exists.
- Product gate: **BLOCKED as expected**, exit1, because documentation templates/languages are intentionally undecided. Product approval fields were preserved.

### Independent source snapshots

| Reviewer | Result | Snapshot SHA-256 |
|---|---|---|
| native code reviewer | PASS_CODE_REVIEW | `e8de17025c164c327d8f49c01f1d33c689007854d9bc0482ffd31f221a16b099` |
| independent security auditor | PASS_WITH_DOCUMENTED_LIMITATIONS | `2b547200de46b29347cc9b9184949c82b5b0ad43833c3f38668b6e915e9fdcce` |

Snapshots exclude final audit/inventory and coordinator task metadata; the security snapshot also excludes the historical audit index. The exact final Git commit is supplied in the external manifest.

### Additional release limits

Managed runtime directories, caches, skill ancestors and local executable paths reject symlink escapes. These preflight checks do not protect against hostile concurrent filesystem replacement by the same user. Optional web dependencies, every upstream supplier, image runtime compatibility and the full OS matrix were not all live-tested. Compose config used synthetic values only; no service was started.

### Evidence handling

The JSON companion retains actual command exit codes, initial red regressions, intermediate failures and final source outcomes. Paths in public command summaries are normalized (`gitleaks`, `<temporary-report>`); machine-local raw logs, runtime audits, real environment reports, user data and downloaded skills are excluded from this source distribution. Detailed local execution records remain outside the release archive.
