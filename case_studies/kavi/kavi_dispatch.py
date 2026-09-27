from __future__ import annotations

from typing import Any, Mapping

from kavi_capability_compiler import adapt_capabilities, scan_manifest


def scan_kavi_dispatch_contract(
    contract: Mapping[str, Any],
    *,
    source_repository: str,
    source_path: str,
    source_sha: str,
) -> dict[str, Any]:
    """Adapt the KAVI bridge contract through KCC's public generic manifest path.

    KAVI remains a repository-only case study. It does not define a private
    inventory contract or bypass KCC's framework-neutral manifest/inventory
    integrity rules.
    """
    tools=contract.get("tools")
    if not isinstance(tools,list) or not tools:
        raise ValueError("KAVI dispatch contract must contain tools")

    server=str(contract.get("name") or "KAVI Dispatch Bridge")
    provenance={
        "kind":"declared_contract",
        "repository":source_repository,
        "path":source_path,
        "sha":source_sha,
        "contract_version":str(contract.get("version") or ""),
        "schema_version":contract.get("schema_version"),
    }

    normalized=[]
    seen=set()
    for raw in tools:
        if not isinstance(raw,Mapping):
            raise ValueError("Invalid KAVI dispatch tool entry")
        name=str(raw.get("name") or "").strip()
        if not name or name in seen:
            raise ValueError(f"Invalid or duplicate KAVI dispatch tool: {name!r}")
        seen.add(name)

        declared_write=raw.get("write")
        if not isinstance(declared_write,bool):
            raise ValueError(f"KAVI dispatch tool missing boolean write declaration: {name}")

        fail_closed=bool(raw.get("fail_closed_until_operator_contract",False))
        annotations={
            "kaviDeclaredWrite":declared_write,
            "kaviApproval":raw.get("approval"),
            "kaviActors":list(raw.get("actors") or []),
            "kaviFailClosedUntilOperatorContract":fail_closed,
        }
        description=(
            "Update KAVI Dispatch Bridge execution state through a declared write capability."
            if declared_write else
            "Read KAVI Dispatch Bridge execution state through a declared read capability."
        )
        normalized.append({
            "name":name,
            "description":description,
            "input_schema":raw.get("input_schema") or raw.get("inputSchema") or {},
            "annotations":annotations,
        })

    manifest=adapt_capabilities(
        "generic",
        {"tools":normalized},
        namespace=server,
        source_metadata=provenance,
    )
    inventory=scan_manifest(manifest)
    inventory["provenance"]=provenance
    return inventory
