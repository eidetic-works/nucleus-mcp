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

## [1.16.9]
See the release history on PyPI for versions published before this file existed.
