# v1.0.7: The First Impression Update

**Codename:** First Impression
**Date:** Feb 17, 2026
**Focus:** Immediate user value, onboarding friction reduction, and engineering hardening.

## 🌟 New Features (The "Wow" Factor)

### 1. The Sovereign Brain Card (`cold_start`)
- **What:** When an AI connects, it now receives a rich "Brain Card" instead of a generic success message.
- **Why:** Immediate context on the state of the Sovereign Brain.
- **Details:**
    - **Memory:** Summary of total engrams and recent memories.
    - **Tasks:** Breakdown of Active/InProgress/Completed tasks.
    - **Mounts:** List of connected ecosystem tools (Stripe, Postgres, etc.).

### 2. Pre-Seeded Welcome Engrams
- **What:** `nucleus-init` now seeds the brain with 2 starter memories.
- **Why:** Prevents "empty brain syndrome" and teaches the user how to retrieve memories immediately.
- **Engrams:**
    - `welcome_to_nucleus`: Explains the local-first philosophy.
    - `tip_cold_start`: Explains how the AI gets context on connection.

### 3. OS-Aware Onboarding
- **What:** `nucleus-init` now detects the User's OS (macOS/Linux/Windows).
- **Impact:** Provides copy-paste configuration paths for Claude Desktop, Cursor, and Windsurf specific to the user's machine.

### 4. Single Source of Truth (SSoT) Versioning
- **What:** Centralized version control in `.registry/version.json`.
- **Tooling:** Hardened `sync_registry.py` to update PyPI, NPM (root & wrapper), Landing Page, and Internal Manifests in a single strike.

## 🐛 Bug Fixes & Hardening

### Tiered Tool Registration
- **Fix:** Resolved `AttributeError` and recursion bugs in `test_tier_based_registration`.
- **Impact:** Robust filtering of tools based on Beta Token tiers.

### Sync Operations
- **Fix:** Resolved cache pollution in `test_sync_ops.py` where identity persisted between tests.
- **Impact:** 100% Pass rate on all 23 sync tests.

### Config & Linting
- **Fix:** Standardized on `py311` target version for `ruff`.
- **Fix:** Deleted redundant/dead code in `tool_registration.py`.
