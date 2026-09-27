from pathlib import Path
import tomllib

import kavi_capability_compiler as kcc


def test_release_version_is_coherent():
    data=tomllib.loads(Path("pyproject.toml").read_text())
    assert data["project"]["version"]=="0.1.0"
    assert kcc.__version__=="0.1.0"


def test_release_metadata_keeps_core_dependency_free():
    data=tomllib.loads(Path("pyproject.toml").read_text())
    assert data["project"]["dependencies"]==[]
    assert set(data["project"]["optional-dependencies"])=={"mcp","signing","all"}


def test_release_docs_exist():
    for path in (
        "CHANGELOG.md",
        "docs/EMBEDDED_SDK.md",
        "docs/UNIVERSAL_MANIFEST.md",
        "docs/INTEGRATION_RECIPES.md",
        "docs/BENCHMARK_REPORT_V0.1.md",
        "docs/RELEASE_CHECKLIST.md",
    ):
        assert Path(path).is_file(), path
