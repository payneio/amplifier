This codebase was originally pulled from multiple repos and has been refactored. The original repos are listed in @upstream/sources.md and include the last HEAD ref and time we incorporated commits from those repos.

We follow those upstream repos and periodically incorporate any new commits into our monorepo. This is not a simple git operation; instead, we understand the intent of new commits and figure out how to incorporate them into our refactored monorepo appropriately.

To help with this, we keep docs about the major refactorings we have done in the upstream/refactor/ directory.

## Quick Lookup for Important File Relocations

While all files may have been modified from upstream sources, the following is a list of files that have been relocated. If there is an upstream change that needs to be incorporated, this is how to find where the new location is. This is not all file movements, though, just think of this as a quick lookup for some important files.

- amplifier:docs/ > docs/
