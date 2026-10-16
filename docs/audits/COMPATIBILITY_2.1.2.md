# Exelia Ultimate Codex Starter v2.1.2 — Compatibility audit

## Executive decision

**SOURCE VERIFICATION PASS; finished archive readiness is recorded in the external companion artifacts.** This is a local release candidate; no publication approval is implied. The final external companion report records exact release commit, archive checksum and post-extraction readiness.

## Baseline and scope

Baseline: `a205d5cbee70ae3b877c26c5d88deb7ebbf5f97b`, branch `main`, clean worktree/index, version2.1.1. The optional independent Polish report was not found in checked local paths; the four user-provided findings were authoritative. Historical2.1.1 remediation reports and product discovery approval are preserved.

## Finding matrix

| Finding | Status | Changed files | Executable regression evidence | Residual limit |
|---|---|---|---|---|
| I-01 | FIXED | installer/localtools.py, tests/test_compatibility_venv.py | Actual offline pip installs and repeat installs from system and external copies/symlinks venvs; unknown interpreter and writable directory links rejected. | Native Windows remains unsupported; tested interpreter/platform versions are listed separately. |
| I-02 | FIXED | tests/integration_smoke.py, tests/test_compatibility_installation.py | Host node sentinel cannot execute; actual CLI reports ready vs incompatible; clean and installed-state integration/resume. | Offline fixtures are simulated host prerequisite evidence; real installation still needs compliant host Node. |
| I-03 | FIXED | installer/engine.py, installer/processes.py, tests/integration_smoke.py, tests/test_compatibility_installation.py | Slow runner, real timeout/no delayed commit, retry success, nested outer timeout, SIGINT/SIGTERM, detached pipe drain, invalid budget refusals. | SIGKILL cannot be caught; a malicious process can detach into a separate session. This is supervised local execution, not OS security isolation. |
| I-04 | FIXED | scripts/check-publication.py, tests/test_compatibility_publication.py | Clean and post-test exports; tracked/inventoried/archived bytecode and nested secrets rejected; altered/missing inventory sources, symlinks/traversal and corrupt ZIP fail. | Inventory is not authenticated supplier provenance; heuristics cannot certify secret absence. |

## Root causes and corrections

### I-01

Interpreter exception compared only sys.executable; external copies venv uses a distinct trusted base executable. Accept runtime-provided sys._base_executable as an additional read-only interpreter target, retaining confined writable directories/caches and restricted interpreter aliases. pyvenv.cfg cannot confer trust.

### I-02

Fixture replaced npm/npx but inherited real host node binary. Explicit simulated Node22.20.0 default shadows host; compliant and22.16.0 noncompliant scenarios use real installer CLI. Real manifest minimum22.20 is unchanged.

### I-03

Fixed120-second initial checkpoint timeout was too short for full QA; killing only parent shell could leave committing children. Checkpoint900s and smoke1800s defaults, explicit1..7200s budgets; process-group timeout/interruption cleanup with bounded drain/reap, signal policy restored; actual timeout/resume checks retain all QA.

### I-04

No-Git export walked generated __pycache__ as release content after ordinary Python execution. Manifest-backed source exports validate source hashes and permit only unlisted current-interpreter bytecode with exact compile/marshal equivalence to unchanged hash-verified inventoried source; never unmarshal or execute caches. Actual ZIP --archive scan inspects every member and rejects runtime artifacts regardless of source-cache exception.

## Test strategy and evidence

Each finding has a red reproduction and permanent executable regression. Commands and nonzero intermediate outcomes remain in the machine-readable report; later successful runs do not erase failures. Counts identify unittest methods per run, not sums across repeated runs or nested fixtures. Offline fake-host integration is separate from actual interpreter/process execution and isolated Linux execution.

| Check | Actual command | Exit | Outcome |
|---|---|---:|---|
| clean-gate | `env -u PYTHONDONTWRITEBYTECODE bash scripts/quality-gate.sh --starter` | 0 | PASS |
| clean-gitleaks | `gitleaks dir --redact --no-banner --report-format json --report-path <temporary-report> .` | 0 | PASS |
| clean-integration | `env EXELIA_SMOKE_TIMEOUT_RECOVERY=1 python3 tests/integration_smoke.py` | 0 | PASS |
| clean-publication | `python3 scripts/check-publication.py` | 0 | PASS |
| clean-rerun-gate | `env -u PYTHONDONTWRITEBYTECODE bash scripts/quality-gate.sh --starter` | 0 | PASS |
| clean-rerun-integration | `env EXELIA_SMOKE_TIMEOUT_RECOVERY=1 python3 tests/integration_smoke.py` | 0 | PASS |
| current-publication | `python3 scripts/check-publication.py` | 0 | PASS |
| history-gitleaks | `gitleaks git --redact --no-banner --report-format json --report-path <temporary-report> .` | 0 | PASS |
| host-final-gate | `bash scripts/quality-gate.sh --starter` | 0 | PASS |
| host-installed-smoke | `env EXELIA_SMOKE_TIMEOUT_RECOVERY=1 python3 tests/integration_smoke.py` | 0 | PASS |
| host-remediation | `python3 -m unittest discover -s tests -p test_remediation_*.py -v` | 0 | PASS |
| host-unit | `python3 -m unittest discover -s tests -v` | 0 | PASS |
| linux-live | `docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,exec (bounded resources, no mounts) full unittest; timeout/recovery integration; publication` | 0 | PASS |
| linux-live | `docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,exec (bounded resources, no mounts) full unittest; timeout/recovery integration; publication` | 1 | FAIL |
| linux-live | `docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,exec (bounded resources, no mounts) full unittest; timeout/recovery integration; publication` | 2 | FAIL |
| linux-live | `docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,exec (bounded resources, no mounts) full unittest; timeout/recovery integration; publication` | 2 | FAIL |
| linux-live | `docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,exec (bounded resources, no mounts) full unittest; timeout/recovery integration; publication` | 0 | PASS |
| post-test-publication | `python3 scripts/check-publication.py` | 1 | FAIL |
| post-test-rerun | `python3 scripts/check-publication.py` | 0 | PASS |
| provenance-licenses | `python3 -c from pathlib import Path; import json,hashlib,subprocess; root=Path.cwd(); v=json.loads(Path('manifests/dependency-provenance.json').read_text()); [(lambda x: (None if hashlib.sha256(Path(x['lockfile']).read_bytes()).hexdigest()==x['sha256'] else (_ for _ in ()).throw(AssertionError(x['lockfile']))))(x) for x in v['npm'].values()]; [(_ for _ in ()).throw(AssertionError(name)) for name in ('LICENSE','rich-LICENSE.txt','markdown-it-py-LICENSE.txt','mdurl-LICENSE.txt','Pygments-LICENSE.txt') if not (Path(name) if name=='LICENSE' else Path('installer/_vendor/licenses')/name).is_file()]; [(_ for _ in ()).throw(AssertionError(p)) for p in ('manifests/tool-dependencies/core/package.json','manifests/tool-dependencies/core/package-lock.json','manifests/tool-dependencies/web/package.json','manifests/tool-dependencies/web/package-lock.json','manifests/tool-dependencies/requirements-uv.txt','manifests/tool-dependencies/requirements-ruff.txt') if Path(p).read_bytes()!=subprocess.check_output(['git','show','a205d5c:'+p])]; print('PASS: original locks and registry hashes unchanged; thirdparty license notices retained')` | 0 | PASS |
| syntax | `python3 -c from pathlib import Path; import subprocess; fs=[p for d in ('exelia','installer','scripts','tests') for p in Path(d).glob('*.py')]; [compile(p.read_text(),str(p),'exec') for p in fs]; sh=[Path('install.sh'),*Path('scripts').glob('*.sh')]; [subprocess.run(['bash','-n',str(p)],check=True) for p in sh]; print(len(fs),'Python files compiled in memory;',len(sh),'shell scripts parsed')` | 0 | PASS |

## Timeout policy and recovery

`EXELIA_CHECKPOINT_TIMEOUT=900` and `EXELIA_SMOKE_TIMEOUT=1800` default to seconds, accept integers1..7200 and reject invalid/unbounded values. Dependency action90/600s, venv100s, structural/probe/platform deadlines remain distinct. The initial checkpoint runs the complete starter QA gate. Timeout/handled interruption terminates its process group before returning failure; no passing result or approved commit is invented. `EXELIA_SMOKE_TIMEOUT_RECOVERY=1` runs a real fixture timeout followed by resume/full QA. Cleanup cannot catch SIGKILL or enforce security containment against malicious detached sessions.

## Native agents and independent review

Six actual native role task assignments are recorded in JSON; definitions alone are not execution evidence. Implementing workers do not approve their own changes. Code and security reviewer findings, fixes and final reviewed-source snapshots are attached after final review. Model recommendations do not prove model routing.

## Existing architecture and security

All twelve roles, local skills, first-frame bundled Rich, MCP definitions, capability/worktree/orchestration/state/evaluation/visual tools and human approval gates remain. No application implementation or discovery approval was invented. F01–F16 regression suites are retained; F12/F16 residual supplier/image/platform limitations remain explicit. Source inventories are integrity metadata, not authenticated supplier trust. Secret detection and log redaction remain heuristic.

## Platforms and CI

Actual macOS host: arm64 Python3.14.8. Actual isolated Linux run: Ubuntu24.04 arm64, Python3.12.3, Node24.20.0 and Git2.43.0. Full140/140 tests, timeout/resume integration and publication PASS (exit0). The task-specific image added missing python3.12-venv; no host package was installed. Test containers had no network/host mounts, a read-only root, writable executable tmpfs, capability drop and bounded resources; containers were removed automatically. CI now configures Ubuntu24.04 Python3.11/3.12/3.14 with bytecode disabled and bounded job duration; configuration is not a hosted CI run. Native Windows is not supported; WSL requires target verification.

## Packaging and publication

Use `git archive` only after the reviewed local release commit. Validate the actual ZIP with `python3 scripts/check-publication.py --archive PATH`; a source export passing after incidental bytecode is not permission to distribute bytecode. Extract into a new directory, verify inventory hashes/modes, full source gate, integration, Rich bootstrap and publication before declaring READY. The source audit precedes its own final commit; finished ZIP identity and readiness belong to the four external release artifacts. No older Desktop artifact is deleted automatically.

## Known limitations

- No hosted GitHub Actions/settings/template flag tested; no remote changed.
- Supplier code/advisory/legal audits and all optional dependency installations remain incomplete.
- No new live product/browser E2E; historical2.1.1 synthetic Chromium evidence is not repeated or claimed current.
- Linux Python3.11 and3.14 hosted matrix not executed unless separately recorded.
- No production or infrastructure services started.
- Raw local runtime logs remain outside distribution; public command summaries contain no host credentials or user data.

Historical evidence: [2.1.1 audit](REMEDIATION_2.1.1.md). Machine-readable current evidence: [COMPATIBILITY_2.1.2.json](COMPATIBILITY_2.1.2.json).

## Final source outcomes

- Actual macOS arm64 Python3.14.8: **140/140 unittest methods PASS**, complete starter gate exit0.
- Actual isolated Linux arm64 Python3.12.3: **140/140 PASS**, exit0. Existing venv/PIP_TARGET regression now executes successfully; system and external copies/symlinks venvs perform real offline pip operations.
- Compatibility subset: **29/29 PASS**. Historical F01–F16 remediation subset: **57/57 PASS**. These are subsets, not extra unique tests added to140.
- Actual installer checkpoint timeout/resume: PASS. Timeout created no HEAD; resume executed the unchanged full gate and committed; repeated installed-state resume performed no downloads. Node22.20/22.16 compliance is simulated explicitly; real minimum remains22.20.
- Syntax:42 Python source files compiled in memory and10 shell scripts parsed. Dependency locks/provenance hashes and bundled license texts remain unchanged from2.1.1; their original provenance release label is historical evidence, not a current-version mismatch.
- Gitleaks reachable baseline history: PASS with no detections; final release commit and finished ZIP are scanned separately during packaging. No scanner certifies secret absence.

## Independent review closure

Independent Code Reviewer: **PASS**. Independent Security Auditor: **PASS**. Both reviewed the complete implementation diff and identified the same SIGTERM late-commit blocker. The original real-process reproduction exited-15 and allowed a late commit; the corrected process exits143, kills the checkpoint group, leaves no HEAD and permits a successful retry. Their final implementation snapshot hashes are recorded in JSON. No outstanding identified source blocker remains.

## Preserved historical findings and approval

F01–F11 andF13–F15 retain their fixes; all57 historical remediation methods pass. F12/F16 remain **PARTIAL** with supplier/legal/advisory, optional install and image/runtime limitations from the untouched2.1.1 reports. Product discovery/approval remains unchanged. Maintenance tasks remain ready for separate final review; the product completion gate is not bypassed.

## Final packaging decision boundary

Verified source is eligible for a local release-candidate commit and clean full-source ZIP. **READY FOR FINAL INDEPENDENT AUDIT** applies only after the four external artifacts record successful checks of the actual finished ZIP, including extraction, all140 tests, offline installation, source hashes, modes, Rich bootstrap, post-test source cache handling and strict rejection of forbidden archived content. Public GitHub publication remains unapproved; no remote/settings/push/deploy operation occurred.

## Failure evidence and scope limits

Original red regressions and the review blocker remain recorded in JSON. Intermediate Linux harness failures (missing ensurepip, tar ownership/options and noexec tmpfs) were preserved before successful reruns; they are not represented as passed product tests. SIGKILL cannot be caught; malicious separately detached sessions are outside Python supervision. Native Windows is unsupported and WSL/unexecuted hosted Python3.11/3.14 Linux jobs remain NOT_TESTED. No live product/browser test or supplier audit was invented. Raw environment/audit runtime logs are excluded from distribution.
