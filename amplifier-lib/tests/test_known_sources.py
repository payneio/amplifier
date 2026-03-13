"""Tests for amplifier_lib.known_sources."""


class TestWellKnownBundles:
    def test_foundation_present(self) -> None:
        from amplifier_lib.known_sources import WELL_KNOWN_BUNDLES
        assert "foundation" in WELL_KNOWN_BUNDLES

    def test_each_entry_has_remote(self) -> None:
        from amplifier_lib.known_sources import WELL_KNOWN_BUNDLES
        for name, info in WELL_KNOWN_BUNDLES.items():
            assert "remote" in info, f"Bundle '{name}' missing 'remote' key"


class TestDefaultProviderSources:
    def test_anthropic_present(self) -> None:
        from amplifier_lib.known_sources import DEFAULT_PROVIDER_SOURCES
        assert "provider-anthropic" in DEFAULT_PROVIDER_SOURCES

    def test_all_values_are_git_uris(self) -> None:
        from amplifier_lib.known_sources import DEFAULT_PROVIDER_SOURCES
        for name, uri in DEFAULT_PROVIDER_SOURCES.items():
            assert uri.startswith("git+https://"), f"{name} URI doesn't start with git+https://"


class TestProviderDependencies:
    def test_azure_depends_on_openai(self) -> None:
        from amplifier_lib.known_sources import PROVIDER_DEPENDENCIES
        assert "provider-openai" in PROVIDER_DEPENDENCIES.get("provider-azure-openai", [])