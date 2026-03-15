This is a monorepo for a project named "Amplifier".

This monorepo contains:

- amplifier-lib: A python lib containing most of the amplifier code.
- amplifier-cli: A CLI to interact with amplifier. Uses amplifier-lib.
- amplifierd: An HTTP/SSE web service to expose amplifier-lib functionality.
- bundles: Packages of context and functionality that can be used by amplifier.
  - bundles/foundation: A "batteries-included" bundle (agents, behaviors, tools, providers).
  - bundles/core: Kernel internals expert and documentation.
  - bundles/amplifier-expert: Ecosystem consultant agent.
  - bundles/amplifier-management: Operational tooling (recipes, audit, activity reports).
  - bundles/experiments: Experimental bundle variants.

@upstream/README.md
