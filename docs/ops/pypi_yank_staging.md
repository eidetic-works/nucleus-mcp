# PyPI Yank Staging — `nucleus-mcp` (ADR-0043 W2, kill-list item 1)

> STAGING ONLY. **No yank has been executed.** This document is the operator-gated
> plan. Do not run any yank/upload action from CI or an agent — a human with PyPI
> maintainer rights performs the yanks in the web console after reviewing this file.

<!-- generated 2026-07-08 from https://pypi.org/pypi/nucleus-mcp/json ; 36 releases -->

## Why

`pip install nucleus-mcp` does not resolve to one package — it resolves to
whatever the *interpreter's* `Requires-Python` allows. A stranger on macOS system
Python **3.9** resolves the newest release whose floor permits 3.9, which is
**1.8.8** — a wheel that crashes on every CLI invocation (`NameError:
archive_parser`) and whose MCP tools all throw `-32603 No module named
...god_combos.pulse_and_polish`. See `.brain/audits/2026-07-08_xray_trial_gauntlet/`.

The current line (1.12.0+) declares `Requires-Python >=3.10` and works. The fix is
to yank every release whose floor still advertises **`>=3.9`** support the code no
longer has. Once yanked, an unpinned `pip install nucleus-mcp` on a `<3.10`
interpreter finds **no** installable candidate (all remaining releases require
`>=3.10`) and errors out cleanly instead of installing a dead wheel — the intended
behavior. Yanked files remain installable only when a user pins the exact version.

The **11** releases below with a `>=3.9` floor are the broken family *and* the only
releases a `<3.10` interpreter can resolve — one and the same set here.

## Classification (version | floor | verdict)

| version | requires-python floor | resolvable by <3.10 | verdict |
|---------|----------------------|---------------------|---------|
| 0.5.0 | `>=3.10` | no | keep |
| 1.0.0 | `>=3.10` | no | keep |
| 1.0.1 | `>=3.10` | no | keep |
| 1.0.2 | `>=3.10` | no | keep |
| 1.0.4 | `>=3.10` | no | keep |
| 1.0.5 | `>=3.10` | no | keep |
| 1.0.6 | `>=3.10` | no | keep |
| 1.0.7 | `>=3.10` | no | keep |
| 1.0.8 | `>=3.10` | no | keep |
| 1.0.9 | `>=3.10` | no | keep |
| 1.2.0 | `>=3.10` | no | keep |
| 1.2.1 | `>=3.10` | no | keep |
| 1.3.0 | `>=3.10` | no | keep |
| 1.3.1 | `>=3.10` | no | keep |
| 1.6.0 | `>=3.9` | YES | **YANK** |
| 1.6.1 | `>=3.9` | YES | **YANK** |
| 1.7.0 | `>=3.9` | YES | **YANK** |
| 1.8.0 | `>=3.9` | YES | **YANK** |
| 1.8.1 | `>=3.9` | YES | **YANK** |
| 1.8.2 | `>=3.9` | YES | **YANK** |
| 1.8.3 | `>=3.9` | YES | **YANK** |
| 1.8.4 | `>=3.9` | YES | **YANK** |
| 1.8.6 | `>=3.9` | YES | **YANK** |
| 1.8.7 | `>=3.9` | YES | **YANK** |
| 1.8.8 | `>=3.9` | YES | **YANK** |
| 1.12.0 | `>=3.10` | no | keep |
| 1.12.1 | `>=3.10` | no | keep |
| 1.13.0 | `>=3.10` | no | keep |
| 1.13.1 | `>=3.10` | no | keep |
| 1.13.2 | `>=3.10` | no | keep |
| 1.13.3 | `>=3.10` | no | keep |
| 1.13.4 | `>=3.10` | no | keep |
| 1.13.5 | `>=3.10` | no | keep |
| 1.13.6 | `>=3.10` | no | keep |
| 1.14.0 | `>=3.10` | no | keep |
| 1.14.1 | `>=3.10` | no | keep |

**Yank set (11):** `1.6.0 1.6.1 1.7.0 1.8.0 1.8.1 1.8.2 1.8.3 1.8.4 1.8.6 1.8.7 1.8.8`

**Rationale (one line):** every `>=3.9`-floor release advertises a Python version
the code base does not support and is the exact wheel a `<3.10` stranger resolves;
yanking them removes the only path by which an unpinned install lands a dead wheel.

> The older `>=3.10` releases (0.5.0 … 1.3.1, 1.12.x, 1.13.x) are **kept**: a
> supported interpreter always resolves the newest (`1.14.x`, working), so these are
> reachable only by an explicit pin and pose no stranger-funnel risk. Yanking them is
> out of scope and would break pinned consumers.

## Exact yank commands (per release)

> **`twine` cannot yank.** There is no `twine yank` subcommand and no PyPI API token
> action for yanking — yank/unyank is a **web-console, session-authenticated** action
> (PEP 592). The canonical, exact "command" is therefore the Manage-release page
> below: open it → **Options ▾** → **Yank** → enter the reason → confirm the version.

Reason string to paste for every release in the set:

```
Requires-Python floor (>=3.9) is below the supported floor (>=3.10); this release
crashes on <3.10 interpreters (cli NameError + missing runtime module). Superseded
by 1.12.0+. See docs/ops/pypi_yank_staging.md.
```

Per-release console URLs (navigate, Yank, paste the reason, confirm):

- 1.6.0 → https://pypi.org/manage/project/nucleus-mcp/release/1.6.0/
- 1.6.1 → https://pypi.org/manage/project/nucleus-mcp/release/1.6.1/
- 1.7.0 → https://pypi.org/manage/project/nucleus-mcp/release/1.7.0/
- 1.8.0 → https://pypi.org/manage/project/nucleus-mcp/release/1.8.0/
- 1.8.1 → https://pypi.org/manage/project/nucleus-mcp/release/1.8.1/
- 1.8.2 → https://pypi.org/manage/project/nucleus-mcp/release/1.8.2/
- 1.8.3 → https://pypi.org/manage/project/nucleus-mcp/release/1.8.3/
- 1.8.4 → https://pypi.org/manage/project/nucleus-mcp/release/1.8.4/
- 1.8.6 → https://pypi.org/manage/project/nucleus-mcp/release/1.8.6/
- 1.8.7 → https://pypi.org/manage/project/nucleus-mcp/release/1.8.7/
- 1.8.8 → https://pypi.org/manage/project/nucleus-mcp/release/1.8.8/

### Optional scripted path (still operator-run, still web-session auth)

PyPI has no token-scoped yank endpoint, so any script must drive the authenticated
web session (login cookie + CSRF token), not a `PYPI_API_TOKEN`. If a maintainer
chooses to script it rather than click 11 times, the shape is one authenticated
POST per version to its `manage/.../release/<v>/` form with `confirm_yank=<v>` and
`yanked_reason=<reason>`. This is intentionally **not** wired here — no credentials
are referenced and nothing is executed. The web console is the supported path.

## Verify after yanking (operator)

On a `<3.10` interpreter, an unpinned install must now fail to resolve:

```
python3.9 -m pip install --no-cache-dir nucleus-mcp
# expected: ERROR: Could not find a version that satisfies the requirement
#           nucleus-mcp (no matching distribution for Python 3.9)
```

On a supported interpreter it still resolves the current release:

```
python3.10 -m pip install --no-cache-dir nucleus-mcp   # -> 1.14.x, works
```

## Rollback (yank is reversible)

Yanking **deletes nothing**. Per PEP 592 a yanked release's files stay on PyPI and
remain installable via an exact pin (`nucleus-mcp==1.8.8`); they are only removed
from *automatic* resolution. To undo, open the same Manage-release URL → **Options ▾**
→ **Unyank**, which restores normal resolution immediately. No re-upload, no version
bump, and no file re-hosting is required. Because it is fully reversible and
non-destructive, this is safe to stage now and execute after operator review.

## Regeneration

Re-run to refresh the table against live PyPI state:

```
python3 - <<'PY'
import json, urllib.request, re
d = json.load(urllib.request.urlopen("https://pypi.org/pypi/nucleus-mcp/json", timeout=30))
def floor(fs):
    return next((f["requires_python"] for f in fs if f.get("requires_python")), None)
def below(rp):
    m = re.search(r'>=\s*3\.(\d+)', rp or "")
    return (int(m.group(1)) < 10) if m else True
for v in sorted(d["releases"], key=lambda s:[int(x) if x.isdigit() else x for x in re.split(r'[.\-]', s)]):
    fs = d["releases"][v]; rp = floor(fs) if fs else None
    yanked = bool(fs) and all(f.get("yanked") for f in fs)
    print(v, rp, "YANK" if (below(rp) and not yanked) else "keep")
PY
```
