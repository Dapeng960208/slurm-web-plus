# Agent Rules

1.  **Documentation First**: Before making any changes, read `docs/standards/documentation-standard.md`.
2.  **Synchronous Updates**: Any change affecting functionality, interfaces, configuration, permissions, databases, deployment, or testing must be accompanied by corresponding updates in the `docs/` directory. A summary of the change must also be recorded in `docs/overview/latest-features.md`; update `project-overview.md` and `architecture-overview.md` when necessary.
3.  **Status Tracking**: Development progress and coordination details must be written into `docs/tracking/`. Never leave them only in chat logs or commit messages.
4.  **New Features**: At minimum, check and update the following as needed:
    - `docs/README.md`
    - `docs/overview/project-overview.md`
    - `docs/overview/architecture-overview.md`
    - `docs/overview/latest-features.md`
    - Feature-specific docs under `docs/features/<feature>/`
    - `docs/tracking/current-release.md`
5.  **Fact-Based**: Never describe unimplemented features as completed.

---

## Hard Constraints

- **Testing**: Every change must include corresponding tests. If testing is infeasible, explicitly document the blocking reasons, unverified scope, and associated risks.
- **Multi-Task Handling**: When multiple requests, issues, or bugs are raised at once, the AI must first categorize them independently, then address them separately by topic. Before committing, identify which changes belong to the current topic, and split commits according to repository conventions. Uncommitted changes must be confirmed with the developer before inclusion; confirmed topic changes must at least be committed locally to ensure traceability.
- **Commit Standards**: Git commits must follow the above splitting and confirmation principles, and adhere to `docs/standards/ai-development-standard.md`.
- **Documentation Organization**:
    - Do not create new top-level topic files in the `docs/` root directory; only `docs/README.md` serves as the index entry point.
    - File naming and placement must follow `docs/standards/document-naming-convention.md`.
    - `docs/overview/latest-features.md` is the global change log entry point; any perceptible change must be appended with a summary there.
- **Error Logging**: When encountering a reproducible error, a retrospective must be written into `docs/tracking/error-log.md` (following `docs/standards/development-error-summary.md`).
- **GitHub CI Workflow**: When checking remote GitHub Actions results, downloading failed logs/artifacts, or continuing from CI failures, the AI must use the repository `github-ci-autofix` flow and the repo-local scripts under `scripts/` first (`fetch-github-ci-result.ps1`, `watch-github-ci.ps1`, `continue-from-github-ci.ps1`, `push-and-watch-github-ci.ps1`) instead of inventing an ad hoc process.
- **Chinese Encoding (Windows)**: When reading Chinese `.md` files, never use bare `Get-Content`. Always use `Get-Content -Encoding UTF8`. If terminal garbling persists, first set `[Console]::InputEncoding`, `[Console]::OutputEncoding`, and `$OutputEncoding` to UTF-8 before reading; alternatively, use `[System.IO.File]::ReadAllText(<path>, [System.Text.UTF8Encoding]::new($false))`.
- **Minor Changes**: Even for trivial fixes, you must evaluate whether documentation updates are required—never skip this step by default.
- **Frontend Changes**: Any frontend-related changes must use the frontend-skill and must read the global stylesheet at `frontend\src\style.css`.
