from pathlib import Path
import tomllib

import kavi_capability_compiler as kcc


def test_release_version_is_coherent():
    from scripts.release_version import project_version

    data=tomllib.loads(Path("pyproject.toml").read_text())
    version=data["project"]["version"]
    assert version==project_version()
    assert kcc.__version__==version


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
        "docs/SDK_COMPATIBILITY.md",
        "docs/ADVERSARIAL_SDK.md",
        "docs/BENCHMARK_REPORT_V0.1.md",
        "docs/RELEASE_CHECKLIST.md",
    ):
        assert Path(path).is_file(), path


def test_public_contract_schema_sources_exist():
    for path in (
        "schemas/kcc.capabilities.v1.schema.json",
        "schemas/kcc.inventory.v1.schema.json",
        "schemas/kcc.inventory-lock.v1.schema.json",
        "schemas/kcc.capsule.v1.schema.json",
        "schemas/kcc.delegation-request.v1.schema.json",
        "schemas/kcc.delegated-capsule.v1.schema.json",
        "schemas/kcc.signed-capsule.v1.schema.json",
    ):
        assert Path(path).is_file(), path


def test_framework_neutral_integration_kits_exist():
    for path in (
        "examples/integrations/_shared.py",
        "examples/integrations/generic_python.py",
        "examples/integrations/openai_tools.py",
        "examples/integrations/anthropic_tools.py",
        "examples/integrations/mcp_tools.py",
        "examples/integrations/openapi_agent.py",
    ):
        assert Path(path).is_file(), path


def test_project_specific_case_study_code_is_not_in_core_package():
    assert not Path("src/kavi_capability_compiler/kavi_dispatch.py").exists()
    assert not Path("src/kavi_capability_compiler/live_probe.py").exists()
    assert Path("case_studies/kavi/kavi_dispatch.py").is_file()
    assert Path("case_studies/kavi/live_probe.py").is_file()

def test_github_first_distribution_files_exist():
    for path in (
        ".github/workflows/pages.yml",
        "scripts/build_simple_index.py",
        "scripts/verify_simple_index.py",
        "scripts/verify_release_workflow.py",
        "scripts/verify_pages_workflow.py",
        "docs/DISTRIBUTION_V0.1.md",
    ):
        assert Path(path).is_file(), path


def test_release_and_pages_workflow_security_contracts():
    from scripts.verify_release_workflow import main as verify_release
    from scripts.verify_pages_workflow import main as verify_pages
    verify_release(".github/workflows/release.yml")
    verify_pages(".github/workflows/pages.yml")
