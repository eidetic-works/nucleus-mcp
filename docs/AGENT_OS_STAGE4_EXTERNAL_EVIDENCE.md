# Agent OS Stage 4 — External Agent Boot Evidence

> **Date:** 2026-08-04
> **Test:** G1 — Real external agent boot (the market test)
> **Status:** PASS — TWO VENDORS

---

## What was tested

Two real external agents from different vendors booted into the Nucleus Agent OS via `boot_cell()`. These are the first real external boots, not simulations. Built via `nucleus_delegate` cross-vendor dispatch.

## Agent 1: Devin (GLM-5.2 High), Cognition

### Boot 1: Git commit verification
- turn_id: turn-e47129069ae7
- verdict: PARTIAL (confidence: 0.5) — git anchor passed, doctrine capped
- recalled: 0 rows (first boot)
- mediated: True (event_id: evt-1785787490-b65e83f5)

### Boot 2: File existence
- turn_id: turn-54b7f3890842
- verdict: PARTIAL (confidence: 0.5) — fs anchor passed, doctrine capped (pre-fix)
- recalled: 5 rows (memory from boot 1 — flywheel working)
- mediated: True

### Boot 3: Judgment task (regime-3)
- turn_id: turn-381b0ba3c2f2
- verdict: UNVERIFIABLE (confidence: 0.2) — no deterministic anchor, honest
- recalled: 5 rows
- mediated: True

## Agent 2: Gemini (3.1-pro-high), Google

Script: `scripts/external_agent_boot_gemini.py` (written and run by the agy lane)

### Turn 1: Git commit verification
- verdict: PARTIAL — git anchor passed, doctrine capped (adjacent, not direct match)

### Turn 2: File existence
- verdict: **CONFIRMED** — fs anchor passed, direct-match exemption (post-doctrine-fix)

### Turn 3: Judgment task (regime-3)
- verdict: UNVERIFIABLE — no deterministic anchor, honest

## Summary

| Metric | Devin (GLM-5.2) | Gemini (3.1-pro) |
|--------|-----------------|------------------|
| Vendor | Cognition | Google |
| Turns | 3 | 3 |
| Mediated | 3/3 | 3/3 |
| CONFIRMED | 0 | 1 |
| PARTIAL | 2 | 1 |
| UNVERIFIABLE | 1 | 1 |
| False CONFIRMED | 0 | 0 |
| Memory recalled | 5 rows (boots 2+3) | 5 rows (turns 2+3) |

## What this proves

1. **The platform thesis is empirically supported by two independent vendors** — Cognition (GLM-5.2) and Google (Gemini) both booted into Nucleus
2. **The flywheel works** — boots 2+3 recalled memory from boot 1 for both agents
3. **The referee is honest** — CONFIRMED for direct-match file existence, PARTIAL for adjacent git, UNVERIFIABLE for judgment, 0 false CONFIRMED
4. **The moat extends to external agents** — their turns carry referee labels that naked turns don't
5. **The doctrine fix works end-to-end** — Gemini's file-existence turn got CONFIRMED (the direct-match exemption)

## What this does NOT prove

1. The market wants this — technical validation ≠ market demand
2. The platform scales to many concurrent agents — 2 agents booting 3 times each is not a load test
3. The verified corpus improves model quality — real fine-tuning hasn't happened yet

## 200-task scale test (post-doctrine-fix)

After the doctrine fix, a 200-task scale test (dispatched to the devin lane) produced:

| Status | Count | Meaning |
|--------|-------|---------|
| CONFIRMED | 100 | real repo-root files — fs:file_exists anchor passed |
| REFUTED | 100 | synthetic test_001.py...test_100.py — anchor failed honestly |
| PARTIAL | 0 | — |
| UNVERIFIABLE | 0 | every claim got a deterministic anchor |

**Compounding curve:** 0 → 6 → 8 → 9 → **100** retained

The doctrine fix unlocked the CONFIRMED signal at scale. 100% of real files got CONFIRMED, 100% of fake files got REFUTED. The referee is honest at scale.
