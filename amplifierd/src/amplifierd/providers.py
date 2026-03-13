"""Provider configuration loading and injection.

Thin re-export layer. All logic lives in amplifier_lib.config.
"""

from amplifier_lib.config import (
    expand_env_vars,
    inject_providers,
    load_provider_config,
    merge_settings_providers,
)

__all__ = [
    "expand_env_vars",
    "inject_providers",
    "load_provider_config",
    "merge_settings_providers",
]
