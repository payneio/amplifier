---
mode:
  name: integrate-upstream
  description: Sync upstream changes into the monorepo
  shortcut: integrate-upstream

  tools:
    safe:
      - recipes
      - mode
      - bash
      - read_file
      - write_file
      - edit_file
      - glob
      - grep
      - delegate

  default_action: allow
---

INTEGRATE-UPSTREAM MODE activated. Sync upstream changes immediately -- do not wait for further input.

1. Call `recipes(operation="execute", recipe_path="@amplifier-monorepo:recipes/upstream-sync.yaml")`
2. Call `mode(operation="clear")` to exit this mode
3. Report the sync results clearly as your final text response

CRITICAL: Call mode(clear) BEFORE presenting results text.

Do not ask for confirmation. Run the recipe now.
