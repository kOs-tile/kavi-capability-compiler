import asyncio

import pytest

from ingest import _github_parts, _is_top_level_skill_manifest, _validate_public_mcp_url


def test_github_root_url_is_normalized():
    assert _github_parts("https://github.com/acme/plugin") == ("acme", "plugin")


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/acme/plugin",
        "https://github.com/acme/plugin/tree/main",
        "https://github.com/acme/plugin?token=secret",
        "https://example.com/acme/plugin",
    ],
)
def test_github_non_root_or_non_github_urls_are_rejected(url):
    with pytest.raises(ValueError):
        _github_parts(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/mcp",
        "https://localhost/mcp",
        "https://127.0.0.1/mcp",
        "https://10.0.0.1/mcp",
        "https://169.254.169.254/latest/meta-data",
        "https://user:pass@example.com/mcp",
        "https://example.com/mcp?token=secret",
        "https://example.com/mcp#fragment",
    ],
)
def test_hosted_mcp_rejects_unsafe_targets(url):
    with pytest.raises(ValueError):
        asyncio.run(_validate_public_mcp_url(url))


def test_only_immediate_skill_manifests_are_discovered():
    assert _is_top_level_skill_manifest("skills/hello/SKILL.md") is True
    assert _is_top_level_skill_manifest("skills/hello/examples/SKILL.md") is False
    assert _is_top_level_skill_manifest("plugins/demo/skills/hello/SKILL.md") is False
    assert _is_top_level_skill_manifest("SKILL.md") is False
