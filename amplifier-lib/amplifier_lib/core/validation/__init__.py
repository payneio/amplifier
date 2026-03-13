"""Validation framework for Amplifier plugin modules."""

import importlib
from dataclasses import dataclass, field


@dataclass
class ValidationCheck:
    """Result of a single validation step."""

    name: str
    passed: bool
    message: str
    severity: str = "error"


@dataclass
class ValidationResult:
    """Aggregated validation results for a module."""

    module_type: str
    module_path: str
    checks: list[ValidationCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no error-severity checks failed."""
        return all(c.passed for c in self.checks if c.severity == "error")

    @property
    def errors(self) -> list[ValidationCheck]:
        """All failed error-severity checks."""
        return [c for c in self.checks if not c.passed and c.severity == "error"]

    @property
    def warnings(self) -> list[ValidationCheck]:
        """All failed warning-severity checks."""
        return [c for c in self.checks if not c.passed and c.severity == "warning"]

    def add(self, check: ValidationCheck) -> None:
        """Append a check to the results."""
        self.checks.append(check)

    def summary(self) -> str:
        """Return a human-readable summary line."""
        total = len(self.checks)
        failed = len(self.errors)
        warned = len(self.warnings)
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.module_type} {self.module_path} — "
            f"{total} checks, {failed} errors, {warned} warnings"
        )


class _BaseValidator:
    """Base validator with common import and mount checks."""

    module_type: str = ""

    async def validate(
        self,
        module_path: str,
        entry_point: str | None = None,
        config: dict | None = None,
    ) -> ValidationResult:
        """Validate a module by import path.

        Checks:
        1. Module is importable.
        2. Entry-point attribute exists on the module (defaults to 'mount').
        3. Entry-point attribute is callable.
        """
        result = ValidationResult(
            module_type=self.module_type,
            module_path=module_path,
        )

        # Check 1: importable
        try:
            if ":" in module_path:
                import_path, attr_name = module_path.rsplit(":", 1)
            else:
                import_path = module_path
                attr_name = entry_point or "mount"

            mod = importlib.import_module(import_path)
            result.add(
                ValidationCheck(
                    name="importable",
                    passed=True,
                    message=f"Module '{import_path}' imported successfully.",
                )
            )
        except ImportError as exc:
            result.add(
                ValidationCheck(
                    name="importable",
                    passed=False,
                    message=f"Cannot import '{module_path}': {exc}",
                )
            )
            # Remaining checks cannot proceed without the module
            result.add(
                ValidationCheck(
                    name="mount_exists",
                    passed=False,
                    message="Skipped — module not importable.",
                )
            )
            result.add(
                ValidationCheck(
                    name="mount_callable",
                    passed=False,
                    message="Skipped — module not importable.",
                )
            )
            return result

        # Check 2: entry-point attribute exists
        attr = getattr(mod, attr_name, None)
        if attr is None:
            result.add(
                ValidationCheck(
                    name="mount_exists",
                    passed=False,
                    message=f"Attribute '{attr_name}' not found on '{import_path}'.",
                )
            )
            result.add(
                ValidationCheck(
                    name="mount_callable",
                    passed=False,
                    message="Skipped — mount attribute missing.",
                )
            )
            return result

        result.add(
            ValidationCheck(
                name="mount_exists",
                passed=True,
                message=f"Attribute '{attr_name}' found.",
            )
        )

        # Check 3: attribute is callable
        if callable(attr):
            result.add(
                ValidationCheck(
                    name="mount_callable",
                    passed=True,
                    message=f"'{attr_name}' is callable.",
                )
            )
        else:
            result.add(
                ValidationCheck(
                    name="mount_callable",
                    passed=False,
                    message=f"'{attr_name}' exists but is not callable.",
                )
            )

        return result


class ToolValidator(_BaseValidator):
    """Validator for tool modules."""

    module_type = "tool"


class HookValidator(_BaseValidator):
    """Validator for hook modules."""

    module_type = "hook"


class ContextValidator(_BaseValidator):
    """Validator for context provider modules."""

    module_type = "context"


class OrchestratorValidator(_BaseValidator):
    """Validator for orchestrator modules."""

    module_type = "orchestrator"


class ProviderValidator(_BaseValidator):
    """Validator for LLM provider modules."""

    module_type = "provider"


__all__ = [
    "ValidationCheck",
    "ValidationResult",
    "ToolValidator",
    "HookValidator",
    "ContextValidator",
    "OrchestratorValidator",
    "ProviderValidator",
]
