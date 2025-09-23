"""CLI templates for common patterns."""


class CliTemplate:
    """Pre-built templates for common CLI patterns."""

    @staticmethod
    def basic_tool() -> str:
        """Basic CLI tool template with notification support.

        Returns:
            Python code template for a basic CLI tool
        """
        return '''#!/usr/bin/env python3
"""
{name} - {description}

A Claude Code SDK powered CLI tool with optional desktop notification support.
"""
import asyncio
import click
from pathlib import Path
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.logger import ToolkitLogger


@click.command()
@click.argument("input", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--notify", is_flag=True, help="Enable desktop notifications")
def main(input: str, output: str, debug: bool, notify: bool):
    """{description}"""
    logger = ToolkitLogger(debug=debug, enable_notifications=notify)
    logger.info("Starting {name}", input=input)

    # Run async function
    result = asyncio.run(process(input, logger))

    if output:
        Path(output).write_text(result)
        logger.info("Output written", file=output)
    else:
        print(result)


async def process(input_path: str, logger: ToolkitLogger) -> str:
    """Process input file with Claude."""
    content = Path(input_path).read_text()

    # Use Claude Code SDK directly with utilities
    client = ClaudeSDKClient()

    try:
        response = await client.query(
            content,
            system_prompt="You are a helpful assistant"
        )

        logger.info("Successfully processed file", input=input_path)
        return response.content
    except Exception as e:
        logger.error("Failed to process", error=str(e))
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
'''

    @staticmethod
    def analyzer_tool() -> str:
        """Code analyzer template with notification support.

        Returns:
            Template for a code analysis tool
        """
        return '''#!/usr/bin/env python3
"""
{name} - Code Analysis Tool

Analyzes code using Claude Code SDK with optional desktop notification support.
"""
import asyncio
import click
import json
from pathlib import Path
from typing import List, Dict, Any
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.logger import ToolkitLogger


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("--output-format", "-f", type=click.Choice(["json", "text"]), default="text")
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--notify", is_flag=True, help="Enable desktop notifications")
def main(paths: tuple, output_format: str, config: str, debug: bool, notify: bool):
    """Analyze code files with Claude."""
    logger = ToolkitLogger(output_format="json" if debug else "text", debug=debug, enable_notifications=notify)

    # Load configuration
    analysis_config = load_config(config) if config else {}

    # Process files
    results = asyncio.run(analyze_files(list(paths), analysis_config, logger))

    # Output results
    if output_format == "json":
        print(json.dumps(results, indent=2))
    else:
        print_text_results(results)


async def analyze_files(
    paths: List[str],
    config: Dict[str, Any],
    logger: ToolkitLogger
) -> List[Dict[str, Any]]:
    """Analyze multiple files."""
    results = []

    system_prompt = config.get("system_prompt", """
    You are a code analyzer. Review the code for:
    - Quality issues
    - Security concerns
    - Performance problems
    - Best practices
    Return a structured analysis.
    """)

    client = ClaudeSDKClient()

    for path in paths:
        logger.info(f"Analyzing {path}")

        content = Path(path).read_text()
        try:
            response = await client.query(f"Analyze this code:\\n\\n{content}", system_prompt=system_prompt)
            results.append({
                "file": path,
                "analysis": response.content,
                "error": None
            })
        except Exception as e:
            results.append({
                "file": path,
                "analysis": None,
                "error": str(e)
            })

    return results


def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from file."""
    return json.loads(Path(path).read_text())


def print_text_results(results: List[Dict[str, Any]]):
    """Print results in text format."""
    for result in results:
        print(f"\\n=== {result['file']} ===")
        if result['error']:
            print(f"ERROR: {result['error']}")
        else:
            print(result['analysis'])


if __name__ == "__main__":
    main()
'''

    @staticmethod
    def makefile_target(name: str) -> str:
        """Generate Makefile target for a CLI tool.

        Args:
            name: Tool name

        Returns:
            Makefile target snippet
        """
        return f""".PHONY: {name}
{name}: ## Run {name} tool
\t@uv run python -m tools.{name} $(ARGS)

.PHONY: {name}-help
{name}-help: ## Show {name} help
\t@uv run python -m tools.{name} --help
"""

    @staticmethod
    def get_template(template_type: str) -> str:
        """Get a template by type.

        Args:
            template_type: Type of template (basic, analyzer, etc.)

        Returns:
            Template code
        """
        templates = {
            "basic": CliTemplate.basic_tool(),
            "analyzer": CliTemplate.analyzer_tool(),
        }
        return templates.get(template_type, CliTemplate.basic_tool())
