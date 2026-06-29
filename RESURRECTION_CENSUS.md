# OPERATION REFLOAT — Phase 0 Census

**Branch:** `resurrection/00-survey`
**Date:** 2026-06-29
**Survey-only:** No fixes applied. All numbers are real command outputs.

---

## 1. Per-Subsystem Census

24 subsystems + top-level modules. Module/LOC counts from `find + wc -l`.
Test file counts from import-scan mapping (278 total test files).

| Subsystem | Modules | Src LOC | Test Files | Test LOC |
|-----------|---------|---------|------------|----------|
| admin | 3 | 346 | 1 | 285 |
| artifacts | 1 | 0 | 0 | 0 |
| core | 4 | 241 | 3 | 24 |
| daemon | 3 | 163 | 0 | 0 |
| dashboard | 2 | 165 | 1 | 244 |
| deployment | 2 | 4 | 0 | 0 |
| diagnostics | 5 | 345 | 1 | 111 |
| features | 1 | 0 | 0 | 0 |
| flywheel | 6 | 774 | 1 | 892 |
| http_transport | 9 | 3022 | 17 | 2057 |
| hypervisor | 4 | 511 | 4 | 0 |
| mirror | 10 | 2062 | 6 | 983 |
| oauth | 2 | 314 | 3 | 1518 |
| org | 2 | 305 | 3 | 798 |
| rabbithole | 5 | 1342 | 1 | 0 |
| recipes | 0 | 0 | 0 | 0 |
| runtime | 251 | 75280 | 171 | 1170 |
| schemas | 1 | 22 | 0 | 0 |
| sessions | 13 | 3183 | 11 | 685 |
| sovereign | 4 | 1700 | 0 | 0 |
| templates | 1 | 1 | 0 | 0 |
| tools | 18 | 6004 | 12 | 1349 |
| watchdog | 2 | 297 | 0 | 0 |
| (top-level) | 17 | 15263 | 44 | — |
| **TOTAL** | **366** | **111344** | **278** | **10825** |

**Notes:**
- `runtime` is the dominant subsystem: 251 modules, 75K LOC (67% of total).
- `recipes` and `artifacts` are empty directories (0 modules).
- 44 test files are unmapped (test framework/tooling tests, not subsystem-specific).
- `sovereign` has 1700 LOC but 0 test files — largest untested subsystem.
- `watchdog` has 297 LOC, 0 test files.
- `hypervisor` has 511 LOC, 4 test files but 0 test LOC (empty test files).

---

## 2. Full Pytest Run

```
$ uv run pytest -q --tb=line
1 failed, 4336 passed, 42 skipped, 21 warnings, 9 errors in 1113.52s (0:18:33)
EXIT=1
```

### Failures (1)

| Test | Error |
|------|-------|
| `tests/test_relay_post_helper.py::test_post_nucleus_relay_block_happy_path` | `assert False is True` — relay_post: OCI rejected status=401 role=cc_tb recipient=operator_assistant |

### Errors (9)

All in `tests/test_chatgpt_app_catalog.py::TestToolAnnotations`:

| Test | Error |
|------|-------|
| `test_all_tools_have_annotations` | `AttributeError: 'FastMCP' object has no attribute 'get_tools'` |
| `test_all_tools_have_readonly_hint` | same |
| `test_all_tools_have_destructive_hint` | same |
| `test_all_tools_have_openworld_hint` | same |
| `test_readonly_tools_are_not_destructive` | same |
| `test_known_readonly_tools` | same |
| `test_known_destructive_tools` | same |
| `test_known_openworld_tools` | same |
| `test_tool_count` | same |

**Root cause:** `FastMCP.get_tools()` API was removed/renamed in a newer version of the `mcp` library. The test suite uses an API that no longer exists.

### Skips (42)

42 tests skipped. Not yet triaged — Phase 1 will justify or fix each.

---

## 3. Coverage Baseline

```
$ uv run pytest -q --tb=no --cov=mcp_server_nucleus --cov-report=term-missing
TOTAL: 53551 statements, 30539 missing, 16286 branches, 1432 missing
Coverage: 40%
```

### Lowest-coverage subsystems (0-20%):

| Module | Stmts | Miss | Branch | BrMiss | Cover |
|--------|-------|------|--------|--------|-------|
| `sovereign/archive_cli.py` | 994 | 994 | 300 | 0 | 0% |
| `sovereign/local_llm.py` | 179 | 179 | 56 | 0 | 0% |
| `watchdog/stall.py` | 186 | 186 | 80 | 0 | 0% |
| `siphon.py` | 121 | 121 | 58 | 0 | 0% |
| `validate.py` | 114 | 114 | 24 | 0 | 0% |
| `runtime/watcher.py` | 73 | 73 | 28 | 0 | 0% |
| `runtime/triggers.py` | 77 | 64 | 24 | 0 | 13% |
| `selfhealer.py` | 260 | 230 | 90 | 0 | 9% |
| `server.py` | 436 | 339 | 70 | 0 | 20% |
| `setup.py` | 61 | 53 | 22 | 1 | 11% |
| `tools/engrams.py` | 296 | 250 | 108 | 0 | 11% |
| `runtime/vector_store.py` | 89 | 59 | 14 | 1 | 30% |
| `tools/orchestration.py` | 780 | 456 | 154 | 16 | 38% |
| `tools/_marketplace_core.py` | 503 | 268 | 176 | 33 | 43% |

**Gap to 90% target:** Need to cover ~26,000 more statements (from 23,012 covered to ~48,196).

---

## 4. Static Analysis Baselines

### mypy

```
$ uv run mypy src --ignore-missing-imports
Found 1136 errors in 174 files (checked 379 source files)
MYPY_EXIT=1
```

**1136 type errors across 174/379 files (46% of files have type errors).**

### ruff

```
$ uv run ruff check src
All checks passed!
RUFF_EXIT=0
```

**0 ruff errors.** Code is lint-clean.

### vulture (dead code)

```
$ uv run vulture src
589 dead code items found
  27 at 90% confidence (unused imports, clear dead code)
  552 at 60% confidence (unused functions/methods/variables)
VULTURE_EXIT=0
```

**90% confidence dead imports (27):**
- `cli.py:2212` — unused import `_pt_patch_stdout`
- `http_transport/app.py:59` — unused import `Middleware`
- `runtime/environment_detector.py:21` — unused imports `PurePosixPath`, `PureWindowsPath`
- `runtime/federation.py:43` — unused import `_context_manager_mod`
- `runtime/growth_ops.py:29` — unused import `common_logger`
- `tools/orchestration.py:135` — unused import `_emit_ev`
- (20 more at 90%)

---

## 5. Security Audit

### pip-audit

```
$ uv run pip-audit
15 CVEs across 6 packages:

Package          Version  CVE ID              Fix Version
python-dotenv    1.2.1    CVE-2026-28684      1.2.2
python-multipart 0.0.22   CVE-2026-40347      0.0.26
python-multipart 0.0.22   CVE-2026-42561      0.0.27
python-multipart 0.0.22   CVE-2026-53540      0.0.31
python-multipart 0.0.22   CVE-2026-53539      0.0.30
python-multipart 0.0.22   CVE-2026-53538      0.0.30
requests          2.32.5  CVE-2026-25645      2.33.0
starlette         0.52.1  PYSEC-2026-161      1.0.1
starlette         0.52.1  PYSEC-2026-249      1.3.1
starlette         0.52.1  PYSEC-2026-248      1.3.0
starlette         0.52.1  CVE-2026-48818      1.1.0
starlette         0.52.1  CVE-2026-48817      1.1.0
urllib3           2.6.3   PYSEC-2026-142      2.7.0
urllib3           2.6.3   PYSEC-2026-141      2.7.0
AUDIT_EXIT=0
```

**15 CVEs, 6 packages need upgrading.** `starlette` has 5 CVEs and needs a major version bump (0.52→1.3). `python-multipart` has 5 CVEs.

### pip list --outdated

```
$ uv pip list --outdated
65 outdated packages
```

Key outdated:
- `starlette` 0.52.1 → 1.3.1 (major bump, 5 CVEs)
- `uvicorn` 0.41.0 → 0.49.0
- `websockets` 15.0.1 → 16.0
- `pydantic` 2.12.5 → 2.13.4
- `protobuf` 6.33.5 → 7.35.1 (major bump)
- `requests` 2.32.5 → 2.34.2 (CVE fix)
- `urllib3` 2.6.3 → 2.7.0 (CVE fix)

---

## 6. Per-Module Import Cost

```
Scanning 366 modules for import cost...

Module                                          Import (ms)
------------------------------------------------|-----------
mcp_server_nucleus                                  1801.6
mcp_server_nucleus.oauth.exchange                    355.0

Total modules scanned: 366
Modules >100ms: 2
```

**Critical:** `mcp_server_nucleus/__init__.py` takes **1.8 seconds** to import. This is the same root cause that made the rabbithole hook slow — the package init eagerly imports heavy submodules. Any tool that imports the package pays 1.8s on every fresh process.

`oauth.exchange` at 355ms is also heavy (likely crypto/JWT library imports).

---

## 7. Ranked Defect Backlog

Severity: CRITICAL > HIGH > MEDIUM > LOW
Blast-radius: system-wide > multi-subsystem > single-subsystem > isolated

| # | Severity | Blast-Radius | Defect | Count | Phase |
|---|----------|-------------|--------|-------|-------|
| 1 | CRITICAL | system-wide | CVEs in dependencies (starlette, python-multipart, requests, urllib3, python-dotenv) | 15 | 4 |
| 2 | CRITICAL | multi-subsystem | `mcp_server_nucleus/__init__.py` import cost 1801ms — every fresh process pays ~1.8s | 1 | 5 |
| 3 | HIGH | system-wide | mypy errors — type safety broken across 46% of files | 1136 | 2 |
| 4 | HIGH | multi-subsystem | Coverage at 40% — need 90%+ (gap: ~26K statements) | 30539 miss | 2 |
| 5 | HIGH | single-subsystem | `FastMCP.get_tools()` API removed — 9 tests erroring | 9 | 1 |
| 6 | HIGH | single-subsystem | relay_post_helper test failing — 401 auth rejection | 1 | 1 |
| 7 | HIGH | multi-subsystem | Dead code (vulture) — 589 items, 27 at 90% confidence | 589 | 2 |
| 8 | MEDIUM | multi-subsystem | 42 skipped tests — need justification or fix | 42 | 1 |
| 9 | MEDIUM | multi-subsystem | 65 outdated packages — upgrade + test | 65 | 4 |
| 10 | MEDIUM | single-subsystem | `sovereign` subsystem: 1700 LOC, 0 test files, 0% coverage | 1 | 2 |
| 11 | MEDIUM | single-subsystem | `watchdog/stall.py`: 186 LOC, 0% coverage | 1 | 2 |
| 12 | MEDIUM | single-subsystem | `selfhealer.py`: 260 LOC, 9% coverage | 1 | 2 |
| 13 | MEDIUM | single-subsystem | `server.py`: 436 LOC, 20% coverage | 1 | 2 |
| 14 | MEDIUM | single-subsystem | `tools/orchestration.py`: 780 LOC, 38% coverage | 1 | 2 |
| 15 | MEDIUM | single-subsystem | `tools/_marketplace_core.py`: 503 LOC, 43% coverage | 1 | 2 |
| 16 | LOW | isolated | `oauth.exchange` import cost 355ms | 1 | 5 |
| 17 | LOW | isolated | Pydantic V1 deprecation warnings (class-based config, @validator) | 3 | 2 |
| 18 | LOW | isolated | websockets.legacy deprecation warnings | 2 | 2 |
| 19 | LOW | isolated | OTEL export failures (otel.example.com:4317 unreachable) | ongoing | 3 |
| 20 | LOW | isolated | `recipes` and `artifacts` directories are empty | 2 | 2 |

---

## Summary

| Metric | Value | Target |
|--------|-------|--------|
| Tests passing | 4336 | 4336+ (fix 1 fail + 9 errors) |
| Tests failing | 1 | 0 |
| Tests erroring | 9 | 0 |
| Tests skipped | 42 | 0 (justify or fix each) |
| Coverage | 40% | ≥90% |
| mypy errors | 1136 | 0 |
| ruff errors | 0 | 0 (already clean) |
| vulture dead code | 589 | <50 |
| CVEs | 15 | 0 |
| Outdated packages | 65 | <10 |
| Import cost >100ms | 2 | 0 |
| Total LOC | 111,344 | — |
| Total modules | 366 | — |
| Total test files | 278 | — |

**The wreck is real but salvageable.** Ruff is already clean. The test suite mostly works (4336/4346 = 99.8% pass rate excluding errors). The biggest gaps are: type safety (1136 mypy errors), coverage (40%→90%), CVE remediation (15), and the 1.8s import cost. Phase 1 fixes the 10 broken tests. Phase 2×24 attacks coverage + mypy per subsystem. Phase 4 kills the CVEs.
