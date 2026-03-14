# Upstream Adaptations Log

Changes incorporated from upstream repos into the monorepo.

| Date | Repo | Change | Action | Notes |
|------|------|--------|--------|-------|
| 2026-03-14 | amplifierd | Remove `amplifier-core` dependency, rewrite all imports to `amplifier_lib` (`d32a895`) | Completed locally | Migration finished before upstream-sync tooling existed; 4 files (`persistence.py`, `errors.py`, `routes/health.py`, `state/session_handle.py`) rewritten |
| 2026-03-14 | amplifier-core (local) | Add `AccessDeniedError`, `InvalidRequestError`, `AbortError`; enhance `InvalidToolCallError` (`0461e7b`) | Added locally | New error classes in `amplifier_lib/core/llm_errors.py` (76→100 lines); not from upstream |
