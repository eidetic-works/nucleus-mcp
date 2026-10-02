# Changelog

All notable changes to `nucleus-mcp`. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Added
- `runtime.sibling_repos` — resolves companion scripts that live in a repo next to this one.
  Configure with `NUCLEUS_SIBLING_REPOS` (`os.pathsep`-separated) or one path per line in
  `$XDG_CONFIG_HOME/nucleus/siblings`. With no configuration only this repo is searched, so
  nothing is assumed about the host machine. A missing script raises one error naming every
  location tried and how to configure it.

### Changed
- `paths.nucleus_root()` no longer falls back to a hard-coded directory under `$HOME`. It now
  resolves `NUCLEUS_ROOT`, else the nearest ancestor of the working directory containing a
  `.brain/`, else the working directory. Strict mode names both fixes in its error.

### Fixed
- Six scheduled jobs (`driver`, `briefing`, `twin_routine`, `analytics`, `training_refresh`,
  `tb_compound`) launched companion scripts from a hard-coded in-repo path. When those scripts
  live elsewhere the jobs failed at run time pointing at a path that does not exist; they now
  resolve through `sibling_repos`.
- `tb_compound_job` read its brain from a literal `$HOME/<repo>/.brain`; it now uses
  `paths.brain_path()` like the rest of the runtime.

### From the public repo (Aug 2026): per-user dashboard + live funnel
#### Added
- **Per-user telemetry dashboard** — worker now stores full per-user event history
  (not just aggregate counters). Each install_id gets:
  - Profile hash (first_seen, last_seen, country, city, region, timezone, python, os, version)
  - Per-command invocation counts (command → count)
  - Recent 200 events list (command, category, duration_ms, session_id, error_type)
  - Daily activity heatmap (date → event count)
  - Auto-assigned pseudonym (deterministic: Adjective + Animal from install_id hash)
- **Geo enrichment** — every event now captures city, region, timezone from
  Cloudflare edge (MaxMind GeoIP). No IP stored.
- **HTML dashboard** at `eidetic.works/dashboard` — full funnel visualization:
  - Funnel bars (views → clones → downloads → real users → telemetry)
  - Key metrics cards (stars, forks, humans, CI noise, telemetry)
  - Real vs CI table with HUMAN/AMBIGUOUS/CI badges
  - Per-user cards with pseudonym, location, commands, recent events
  - Known BigQuery users table for correlation
  - Dark theme, auto-refresh 60s
- **`GET /telemetry/users`** — per-user dashboard API (`?limit=20&events=0`)
- **`GET /telemetry/users/:id`** — single-user detail with full event history
- **`POST /telemetry/users/:id/pseudonym`** — manually name a user
- **`GET /telemetry/known-users`** — pre-telemetry BigQuery user list (9 users)
- **`GET/POST /telemetry/funnel`** — store/retrieve BigQuery+GitHub funnel summary
- **Funnel script integration** — daily `pypi_full_funnel.py` pushes live
  BigQuery + GitHub data to the worker for the dashboard
#### Changed
- Worker now captures `request.cf.city`, `request.cf.region`, `request.cf.timezone`
  in addition to `request.cf.country`
- Dashboard reads live funnel data from Upstash (no more hardcoded numbers)

## [1.16.9]
See the release history on PyPI for versions published before this file existed.
