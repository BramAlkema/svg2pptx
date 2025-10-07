# Repository Guidelines

## Project Structure & Module Organization
`core/` hosts the Clean Slate conversion pipeline (parse, IR, mapping, policy, converters). `api/` exposes the FastAPI service for OAuth, batch, and visual analysis workflows. `cli/` contains the Click entry point for local conversions. `pipeline/` and `presentationml/` supply orchestration and PPTX templating helpers. Automation lives in `scripts/` and `tools/`. Tests are in `tests/` (unit, e2e, performance, visual) with golden assets under `testing/golden/`. Architecture notes, specs, and runnable samples live in `docs/`, `specs/`, and `examples/`.

## Build, Test, and Development Commands
- `python3 -m venv venv` — create the project virtualenv once (macOS/Linux).
- `source venv/bin/activate` — always activate the virtualenv in your shell before running tooling (Windows: `venv\\Scripts\\activate`).
- `pip install -r requirements-dev.txt` — install runtime + dev tooling (pytest, black, mypy, etc.).
- `pre-commit install` — enable formatting, lint, type, security, and coverage hooks.
- `python -m pytest` — run the default suite with coverage output in `reports/coverage/`.
- `python -m pytest tests/unit -m "unit and not slow"` — quick feedback cycle.
- `uvicorn api.main:app --reload` (or `svg2pptx-server`) — start the API after configuring `.env` and OAuth credentials.

## Coding Style & Naming Conventions
Black enforces 4-space indentation and PEP 8 defaults; isort runs with the black profile. Use snake_case for modules/functions, PascalCase for classes, and UPPER_SNAKE for constants. Type hints are expected across public services; mypy (ignore-missing-imports) runs in CI. Keep module boundaries aligned with domain folders (e.g., `core/map`, `core/policy`). Prefer docstrings or inline comments only when explaining non-obvious policy decisions.

## Testing Guidelines
Pytest discovers `test_*.py` under `tests/`; mirror source paths (e.g., `tests/unit/core/map/test_text_mapper.py`). Apply markers (`unit`, `integration`, `e2e`, `performance`, `slow`, `w3c`, `compliance`) and filter with `-m` during local runs. Coverage must remain ≥60% (`--cov=src`); update golden baselines in `testing/golden/` when behavior changes and document diffs in the PR.

## Commit & Pull Request Guidelines
Write concise, imperative commit subjects, mirroring the existing log (e.g., `Add IR tests for clipping fallback`). Keep logical changes grouped and run pre-commit before pushing. PRs should state the issue, solution, and validation (tests run, visual diff assets, generated PPTX/HTML reports). Link issues when relevant and flag configuration impacts (`.env`, Huey/Redis, Google credentials) so reviewers can reproduce.

## Security & Configuration Tips
Never commit secrets; adapt `.env.example` and keep tokens under `credentials/`. Follow `OAUTH_SETUP.md` for Google integrations and `HUEY_QUEUE_SETUP.md` for queueing. Sanitize large or proprietary SVG fixtures before sharing and avoid checking binary results into git.
