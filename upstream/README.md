This codebase was originally pulled from multiple repos and has been refactored. The original repos are listed in @upstream/sources.md and include the last HEAD ref and time we incorporated commits from those repos.

We follow those upstream repos and periodically incorporate any new commits into our monorepo. This is not a simple git operation; instead, we understand the intent of new commits and figure out how to incorporate them into our refactored monorepo appropriately.

To help with this, we keep docs about the major refactorings we have done in the upstream/refactor/ directory.

## Key Reference Files

- **refactor-mappings.md** -- Complete upstream-to-monorepo mapping table: which repos map to which directories, what was eliminated vs kept, import translations, and migration status. This is the primary reference for incorporating upstream changes.
- **sources.md** -- Last-synced HEAD SHA per upstream repo. Updated automatically by the upstream-sync recipe.
- **adaptations.md** -- Running log of changes incorporated from upstream.
- **refactor/** -- Detailed decision records for each major refactoring (00-04).
