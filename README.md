# Amplifier

> ⚠️ This project is a research demonstrator. It is in early development and may change significantly. Using permissive AI tools on your computer requires careful attention to security considerations and careful human supervision, and even then things can still go wrong. Use it with caution, and at your own risk, we have NOT built in the safety systems yet. We are performing our _active exploration_ in the open for others to join in the conversation and exploration, not as a product or "official release".

## What is Amplifier?

Amplifier is an agent library that allows developers to compose agents from modular bundles, controlling their behavior entirely, and embed them in programs and services.

### Composable Agents: The Bundle

Amplifier lets you compose agents from the ground up with with your own orchestration loop and context-management, and providers, then layering on your desired context, tools, hooks, skills, recipes, and subagents. These behaviors are composable, allowing developers to rapidly experiment with different agent behaviors for unlimited scenarios.

This repo includes a basic bundle (Amplifier basic) you can extend, a popular "batteries-included" bundle (the [foundation bundle](./bundles/foundation)), and [a list of community bundles we like](./docs/MODULES.md).

Once your agent is composed, Amplifier manages interactive sessions for you, using the LLM model providers of your choice.

Read more about bundles in our [Bundle Guide](amplifier-lib/docs/BUNDLE_GUIDE.md).

### Three ways to integrate into your projects: The Library, Daemon, and CLI

In addition to the [Amplifier library](./amplifier-lib/README.md), this repo contains:

- [Amplifierd](./amplifierd/README.md): An HTTP/SSE service, created as a think wrapper around the Amplifier library--useful for creating rich web-app experiences with Amplifier and for integrating Amplifier with your non-Python projects.
- [Amplifier CLI](./amplifier-cli/README.md): A command-line tool to manage your amplifier installation. Amplifier CLI also provides a simple interactive chat interface.

## Quick Start

> 🚩 Amplifier is currently developed and tested on macOS, Linux, and Windows Subsystem for Linux (WSL). Native Windows shells have known issues with some of the common bundle modules—use WSL unless you're actively contributing Windows fixes.

### Install

#### Prerequisites

- [`uv`](https://docs.astral.sh/uv/) (auto-installed if missing). Used by Amplifier to create isolated python environments and fetch modules.
- `git`: Used for fetching Amplifier bundles.
- [`gh`](https://cli.github.com) (authenticated): Not absolutely required, but very useful for coding agents that interact with Github.

Note: These are developer dependencies that we make sure you have installed to have the smoothest experience exploring Amplifier. When integrated into your programs, `uv` is the only system-requirement for Amplifier to work.

### Just run the install.sh script!

For developers, we suggest you clone the repo to get all the goodies.

```bash
git clone https://github.com/payneio/amplifier.git
cd amplifier
./install.sh
```

If you just want to run a particular Amplifier experience:

- The Amplifier CLI:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/microsoft/amplifier-distro/main/install.sh | bash
  ```
- A distro of various Amplifier experiences:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/microsoft/amplifier-distro/main/install.sh | bash
  ```

## Customizing Amplifier

### Creating Custom Bundles

Bundles configure your Amplifier environment with providers, tools, agents, and behaviors.

**→ [Bundle Authoring Guide](https://github.com/microsoft/amplifier-foundation/blob/main/docs/BUNDLE_GUIDE.md)** - Complete guide to creating bundles

### Creating Custom Agents

Agents are specialized AI personas for focused tasks.

**→ [Agent Authoring Guide](https://github.com/microsoft/amplifier-foundation/blob/main/docs/AGENT_AUTHORING.md)** - Complete guide to creating agents

**Having issues?** See [Troubleshooting](docs/USER_ONBOARDING.md#troubleshooting) including [Clean Reinstall](docs/USER_ONBOARDING.md#clean-reinstall-recovery) for recovery steps.

## The Vision

**Today**: A powerful CLI for AI-assisted development.

**Tomorrow**: A platform where:

- **Multiple interfaces** coexist - CLI, web, mobile, voice, IDE plugins
- **Community modules** extend capabilities infinitely
- **Dynamic mixing** - Amplifier composes custom solutions from available modules
- **AI builds AI** - Use Amplifier to create new modules with minimal manual coding
- **Collaborative AI** - Amplifier instances work together on complex tasks

The modular foundation we're building today enables all of this. You're getting in early on something that's going to fundamentally change how we work with AI.

## Contributing

**Join us on this journey!** Fork, experiment, build modules, share feedback. This is the ground floor.

> 📃 This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
