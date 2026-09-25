"""Release gates for nucleus-mcp, run against the BUILT ARTIFACT.

Usage:  python3 scripts/release_gates.py [path/to/sdist.tar.gz]

Every gate here exists because the property it checks ALREADY shipped broken.
None is hypothetical. Run against a known-bad sdist before trusting a green
run: the 1.16.6 sdist fails GATE3 and GATE4, which is what makes a pass on
1.16.7 mean something.

These run against the ARTIFACT, not the source tree, because that is where the
defects were observable -- 1.16.6's source read fine in isolation at every point
a source-level check would have looked.
"""
import re, subprocess, sys, tarfile, hashlib, os
from pathlib import Path

def _newest_sdist() -> Path:
    """The no-argument path, with the staleness check it was missing.

    Globbing dist/ picks up whatever was built last, which may be days old. That
    is not hypothetical: on 2026-09-18 a floor was raised in pyproject.toml and
    three separate gate runs kept reporting the OLD floor as vulnerable, because
    every one of them read a two-day-old sdist. The verdict was about an artifact
    nobody was changing.

    This is the same failure the comment below describes for the tar prefix, one
    level up: the gate must be pointed at the artifact the change produced, not at
    one that merely exists.
    """
    pkg = Path(__file__).resolve().parents[1]
    found = sorted((pkg / "dist").glob("*.tar.gz"))
    if not found:
        print("INSUFFICIENT: no sdist in dist/ and none given. Nothing was checked.",
              file=sys.stderr)
        raise SystemExit(3)
    newest = max(found, key=lambda p: p.stat().st_mtime)
    src_mtime = subprocess.run(
        ["git", "-C", str(pkg), "log", "-1", "--format=%ct", "--",
         "pyproject.toml", "uv.lock", "src"],
        capture_output=True, text=True).stdout.strip()
    if src_mtime and newest.stat().st_mtime < int(src_mtime):
        import datetime as _dt
        built = _dt.datetime.fromtimestamp(newest.stat().st_mtime).isoformat(" ", "seconds")
        changed = _dt.datetime.fromtimestamp(int(src_mtime)).isoformat(" ", "seconds")
        print(f"INSUFFICIENT: {newest.name} was built {built}, but pyproject/uv.lock/src "
              f"changed {changed}. This sdist predates the sources, so any verdict "
              f"would describe an artifact nobody is changing.\n"
              f"  Rebuild:  python3 -m build --outdir dist .\n"
              f"  Or name the artifact:  {Path(__file__).name} path/to/sdist.tar.gz",
              file=sys.stderr)
        raise SystemExit(3)
    return newest


SDIST = Path(sys.argv[1]) if len(sys.argv) > 1 else _newest_sdist()

# Derive the top-level dir from the ARCHIVE, never the filename: a renamed or
# downloaded sdist would otherwise make every read() miss, and the gates would
# report PASS while reading nothing. Observed while building this script --
# it "passed" a known-bad sdist because it was still pointed at the good one.
with tarfile.open(SDIST) as _t:
    PREFIX = _t.getnames()[0].split("/", 1)[0]
print(f"GATES over: {SDIST}  (prefix {PREFIX})")
fails = []

# The member list is the input set for every gate below. A scan over an empty
# archive exits 0 having examined nothing, which is how a "success" gets reported
# for work that never happened.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from mcp_server_nucleus.runtime.preflight import assert_non_empty
except Exception:  # preflight is a nicety here, never a reason a gate cannot run
    def assert_non_empty(label, items, minimum=1):
        if len(items) < minimum:
            raise SystemExit(f"{label}: {len(items)} item(s) — nothing was scanned")
        print(f"preflight: {label}={len(items)}")
        return items


def read(member):
    with tarfile.open(SDIST) as t:
        f = t.extractfile(f"{PREFIX}/{member}")
        if f is None:
            raise SystemExit(f"GATE ABORT: {member!r} not in {SDIST.name} -- "
                             "the gates did not run; this is not a pass")
        return f.read().decode("utf-8", "replace")

# ── GATE 1: the 36x pricing fix is present and prices a family model ────────
tb = read("src/mcp_server_nucleus/runtime/token_budget.py")
ok = "MODEL_FAMILY_PRICING" in tb
print(f"GATE1 pricing-family-table present : {ok}")
if not ok: fails.append("GATE1")

# ── GATE 2: no real identity, by HASH not by count ──────────────────────────
home = os.path.expanduser("~")
real = hashlib.sha256(home.encode()).hexdigest()
names, hits = set(), []
with tarfile.open(SDIST) as t:
    for m in t.getmembers():
        if not m.isfile(): continue
        try: txt = t.extractfile(m).read().decode("utf-8", "replace")
        except Exception: continue
        for n in re.findall(r"/Users/[A-Za-z0-9_.-]+", txt):
            names.add(n)
            if hashlib.sha256(n.encode()).hexdigest() == real: hits.append((m.name, n))
print(f"GATE2 /Users/* names={len(names)}  REAL-home matches={len(hits)}")
if hits:
    fails.append("GATE2"); print("      ", hits[:3])

# ── GATE 3: the 1.16.6 defect -- the scan's consumer must actually run ──────
br = read("src/mcp_server_nucleus/runtime/build_runner.py")
import ast
tree = ast.parse(br)
mod_names = set()
for n in tree.body:
    if isinstance(n, ast.Assign):
        mod_names |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        mod_names.add(n.name)
undefined = []
for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
    local = {a.arg for a in fn.args.args}
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Assign):
            local |= {t.id for t in sub.targets if isinstance(t, ast.Name)}
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
            if sub.id.startswith("_PSEUDONYMITY") and sub.id not in mod_names and sub.id not in local:
                undefined.append((fn.name, sub.lineno, sub.id))
print(f"GATE3 pseudonymity consumer resolvable : {not undefined}")
if undefined:
    fails.append("GATE3"); print("      NameError-on-call:", undefined)

# ── GATE 4: no dependency declared twice in the shipped metadata ────────────
pkg = read("PKG-INFO")
# Harmful shape = two UNCONDITIONAL declarations of one distribution. A base
# dep restated under `extra == "x"` is legal (extras tighten). The cryptography
# defect was two in the SAME marker context, silently intersected by pip.
lines = re.findall(r"^Requires-Dist:\s*(.+)$", pkg, re.M)
buckets = {}
for line in lines:
    nm = re.split(r"[<>=!~\[;( ]", line.strip(), maxsplit=1)[0].lower().replace("_", "-")
    mk = line.split(";", 1)[1].strip() if ";" in line else ""
    buckets.setdefault((nm, mk), []).append(line.strip())
dupes = {k: v for k, v in buckets.items() if len(v) > 1}
deps = lines
print(f"GATE4 Requires-Dist={len(deps)}  same-context-duplicates={dupes or 'none'}")
if dupes: fails.append("GATE4")

# ── GATE 5: no URL PyPI will 400 on ────────────────────────────────────────
urls = re.findall(r"^Project-URL:\s*.+?,\s*(\S+)", pkg, re.M)
bad = [u for u in urls if not u.lower().startswith(("http://", "https://"))]
print(f"GATE5 Project-URL={urls}  rejected-by-pypi={bad or 'none'}")
if bad: fails.append("GATE5")

# ── GATE 6: metadata version PyPI accepts ──────────────────────────────────
mv = re.search(r"^Metadata-Version:\s*(\S+)", pkg, re.M).group(1)
print(f"GATE6 Metadata-Version={mv} (2.5 is rejected)")
if mv != "2.4": fails.append("GATE6")

# ── GATE 7: no declared floor may land on a known-vulnerable version ────────
#
# Checks the ADVISORY COUNT AT THE DECLARED FLOOR, not at whatever version
# happens to be installed. Those differ exactly when a floor is too low, and a
# check that only inspects a resolved environment cannot see it -- a resolver
# picking the newest release reads clean while the published constraint still
# permits a vulnerable one for everyone else.
#
# This exists because 1.16.7 shipped `cryptography>=48.0.1`, believed to be a
# CVE remediation floor on the strength of commit 497d5139's message. That
# commit names no CVE, carries no audit artifact, and says it bumped to 49.0.0
# while writing >=48.0.1 -- whatever was tested is not what was pinned, and
# nothing anywhere said so. Measured against OSV, >=48.0.1 left two HIGH and
# one MODERATE advisory reachable.
#
# Network-dependent, so it must fail INSUFFICIENT, never clean: an unreachable
# advisory database is not evidence of zero advisories.

import json as _json, urllib.request as _url, urllib.error as _err

def _advisories(name, version):
    req = _url.Request(
        "https://api.osv.dev/v1/query",
        data=_json.dumps({"package": {"name": name, "ecosystem": "PyPI"},
                          "version": version}).encode(),
        headers={"Content-Type": "application/json"})
    with _url.urlopen(req, timeout=25) as r:
        return {a["id"] for a in (_json.load(r).get("vulns") or [])
                if a["id"].startswith("GHSA")}

floors = {}
for line in re.findall(r"^Requires-Dist:\s*(.+)$", pkg, re.M):
    nm = re.split(r"[<>=!~\[;( ]", line.strip(), maxsplit=1)[0].lower().replace("_", "-")
    fl = re.search(r">=\s*([0-9][0-9A-Za-z.\-]*)", line)
    if fl:
        floors.setdefault(nm, fl.group(1))

vuln, unreachable = [], []
for nm, fl in sorted(floors.items()):
    try:
        ids = _advisories(nm, fl)
        if ids:
            vuln.append((nm, fl, sorted(ids)))
    except Exception as e:
        unreachable.append((nm, fl, str(e)[:60]))

print(f"GATE7 floors checked={len(floors)}  vulnerable={len(vuln)}  unreachable={len(unreachable)}")
for nm, fl, ids in vuln:
    print(f"      !! {nm}>={fl} -> {len(ids)}: {', '.join(ids[:3])}")
if vuln:
    fails.append("GATE7")
if unreachable:
    print(f"      INSUFFICIENT (advisory DB unreachable for {len(unreachable)}): "
          f"{unreachable[0][0]} -- {unreachable[0][2]}")
    fails.append("GATE7-INSUFFICIENT")


# ── GATE 8: no LOCKED package may be on a known-vulnerable version ──────────
#
# GATE7 checks DECLARED floors. This checks what is actually pinned. The two
# differ enormously: 29 declared floors vs 137 locked packages, so 108 packages
# were never examined by any check here.
#
# It found two, both transitive, both HIGH, neither declared anywhere:
#   mcp==1.26.0        GHSA-jpw9-pfvf-9f58  HTTP transports serve session
#                      requests without verifying the authenticated session
#                      GHSA-vj7q-gjh5-988w  no Host/Origin validation on the
#                      WebSocket transport
#                      GHSA-hvrp-rf83-w775  experimental task handlers
#   soupsieve==2.8.3   GHSA-2wc2-fm75-p42x  memory exhaustion
#                      GHSA-836r-79rf-4m37  ReDoS in the selector parser
#
# The lockfile is also a SECOND place a floor lives: at the time GATE7 first
# passed, uv.lock still pinned aiohttp 3.14.1, pyasn1 0.6.3 and cryptography
# 49.0.0 -- all BELOW the floors pyproject had just raised. A `uv sync` would
# have installed vulnerable versions while every declared-floor check read green.
#
# Runs against the repo's uv.lock, not the sdist -- the lock does not ship.
# INSUFFICIENT on an unreachable DB, never clean.

_LOCK = Path(__file__).resolve().parents[1] / "uv.lock"
if not _LOCK.exists():
    print(f"GATE8 SKIPPED: no uv.lock at {_LOCK}")
else:
    locked = {}
    for blk in _LOCK.read_text(encoding="utf-8", errors="replace").split("[[package]]"):
        nm = re.search(r'name\s*=\s*"([^"]+)"', blk)
        vr = re.search(r'version\s*=\s*"([^"]+)"', blk)
        if nm and vr:
            locked[nm.group(1).lower()] = vr.group(1)
    lv, lu = [], []
    for nm, vr in sorted(locked.items()):
        try:
            ids = _advisories(nm, vr)
            if ids:
                lv.append((nm, vr, sorted(ids)))
        except Exception as e:
            lu.append((nm, vr, str(e)[:50]))
    print(f"GATE8 locked={len(locked)}  vulnerable={len(lv)}  unreachable={len(lu)}")
    for nm, vr, ids in lv:
        print(f"      !! {nm}=={vr} -> {len(ids)}: {', '.join(ids[:3])}")
    if lv:
        fails.append("GATE8")
    if lu:
        print(f"      INSUFFICIENT (DB unreachable for {len(lu)}): {lu[0][0]} -- {lu[0][2]}")
        fails.append("GATE8-INSUFFICIENT")


print()
print("RESULT:", "ALL GATES PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)
