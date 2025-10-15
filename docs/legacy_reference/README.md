# Legacy Reference (Archive Retired)

The historical `archive/` and `archive_old/` directories were removed during Phase 6 of the Archive Shim Retirement
effort. Those trees hosted the original prototype converters, Drive upload scripts, and assorted debugging assets that
pre-dated the Clean Slate architecture. They are no longer part of the build or test surface area.

## Where did the files go?

- The final snapshot lives in Git history (see tag/commit referenced in `specs/archive_shim_retirement.md`).
- No active tests relied on the archived assets; existing golden fixtures cover current scenarios.

## Why remove them?

- To eliminate the temptation to reintroduce deprecated imports.
- To shrink the repository footprint (binary PPTX assets accounted for hundreds of megabytes).
- To simplify onboarding material—new contributors focus on the Clean Slate implementation.

If you truly need to inspect the legacy code, grab it from Git history (e.g. `git show <commit>:archive/legacy-src/...`).
This directory exists purely as a breadcrumb for future readers.

## Release Notes

- **Phase 6 (Archive Retirement)** – Removed `archive/` and `archive_old/` trees, along with Google Drive upload
  workflows, in favour of the streamlined Clean Slate pipeline and OAuth-based Slides export. Historical documents are
  retained in Git history and summarized here for posterity.
