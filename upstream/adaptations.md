# Upstream Adaptations Log

Changes incorporated from upstream repos into the monorepo.

| Date | Repo | Change | Action | Notes |
|------|------|--------|--------|-------|
| 2026-03-14 | amplifierd | Remove `amplifier-core` dependency, rewrite all imports to `amplifier_lib` (`d32a895`) | Completed locally | Migration finished before upstream-sync tooling existed; 4 files (`persistence.py`, `errors.py`, `routes/health.py`, `state/session_handle.py`) rewritten |
| 2026-03-14 | amplifier-core (local) | Add `AccessDeniedError`, `InvalidRequestError`, `AbortError`; enhance `InvalidToolCallError` (`0461e7b`) | Added locally | New error classes in `amplifier_lib/core/llm_errors.py` (76→100 lines); not from upstream |
| 2025-07-16 | amplifier-core | PR #47 | SKIP | CI-only change for Rust wheel builds (macOS x86_64, Windows arm64); all Rust/maturin infrastructure eliminated in monorepo |
| 2025-07-17 | amplifier-foundation | PR #126 | ADAPT | v3.3.0 recipe validation integration into validate-bundle-repo.yaml; pure bundle content (recipe + tests) → bundles/amplifier-bundle-foundation/; no import translations needed; note: references validate-recipes.yaml sub-recipe not yet in monorepo |
| 2025-07-16 | amplifier-core | 5902f3e chore: bump version to 1.2.2 | SKIP | Pure version bump on eliminated Rust/PyO3/pyproject.toml infrastructure |
| 2026-03-14 | amplifier-foundation | 4c6bf7b feat(foundation): add creating-amplifier-modules skill | ADAPT | New skill file → bundles/amplifier-bundle-foundation/skills/creating-amplifier-modules/SKILL.md; `from amplifier_core import ToolResult` translated to `from amplifier_lib.core import ToolResult` in all code examples; peer dependency comment updated accordingly |
