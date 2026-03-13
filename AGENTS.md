This is a monorepo for a project named "Amplifier".

This monorepo contains:

- amplifier-lib: A python lib containing most of the amplifier code.
- amplifier-cli: A CLI to interact with amplifier. Uses amplifier-lib.
- amplifierd: An HTTP/SSE web service to expose amplifier-lib functionality.
- bundles: Packages of context and functionality that can be used by amplifier.
- bundles/amplifier-bundle-foundation: A "batteries-included" bundle.

This code was originally pulled from multiple repos and has been refactored. The original repos are listed in upstream/sources.md and include the last HEAD ref and time we incorporated commits from those repos.

We follow those upstream repos and periodically incorporate any new commits into our monorepo. This is not a simple git operation; instead, we understand the intent of new commits and figure out how to incorporate them into our refactored monorepo appropriately.

To help with this, we keep docs about the major refactorings we have done in the upstream/refactor/ directory.
