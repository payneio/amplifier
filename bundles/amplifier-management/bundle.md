---
bundle:
  name: amplifier-management
  version: 1.0.0
  description: Tooling for developing and managing the Amplifier ecosystem

includes:
  - bundle: foundation
  - bundle: amplifier-expert:behaviors/amplifier-expert
  - bundle: amplifier-management:behaviors/amplifier-dev
---

# Amplifier Ecosystem Management

The **amplifier-management** bundle provides operational tooling for people working ON the Amplifier ecosystem. It includes:

- **Ecosystem Recipes** - Audit, activity reports, doc generation
- **Development Hygiene** - CLI architecture and dev patterns context
- **Amplifier Expert** - The authoritative ecosystem consultant agent

## Recipes

| Recipe | Description |
|--------|-------------|
| `amplifier-ecosystem-audit.yaml` | Multi-repo compliance audit with approval gate |
| `ecosystem-activity-report.yaml` | Cross-repo activity report from MODULES.md |
| `document-generation.yaml` | BFS-traversal doc generation from outline |
| `outline-generation-from-doc.yaml` | Generate outline from existing doc |
| `repo-activity-analysis.yaml` | Single-repo commit/PR analysis |
| `repo-audit.yaml` | Single-repo compliance check |

## When to Use This Bundle

Use this bundle when you are working ON the Amplifier ecosystem:
- Running ecosystem audits and activity reports
- Generating or updating documentation
- Multi-repo coordination and analysis

For general Amplifier development (building apps, bundles, modules), use the `foundation` bundle instead.

---

@foundation:context/shared/common-system-base.md
