from __future__ import annotations

from typing import Any, Mapping

from .core import capability_id, digest


def scan_kavi_dispatch_contract(
    contract: Mapping[str, Any],
    *,
    source_repository: str,
    source_path: str,
    source_sha: str,
) -> dict[str, Any]:
    """Adapt the declared KAVI Dispatch Bridge contract into KCC inventory IR.

    This adapter is intentionally outside the core compiler. The contract's
    read/write declaration is preserved as declared authority evidence; it is
    not treated as observed runtime proof.
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
    caps=[]
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
        effect="write" if declared_write else "read"
        risk_flags=["declared_mutation"] if declared_write else []
        if raw.get("fail_closed_until_operator_contract") is True:
            risk_flags.append("approval_contract_required")
        declared={
            "write":declared_write,
            "approval":raw.get("approval"),
            "actors":list(raw.get("actors") or []),
            "fail_closed_until_operator_contract":bool(raw.get("fail_closed_until_operator_contract",False)),
        }
        fp=digest({
            "name":name,
            "declared":declared,
            "source_sha":source_sha,
            "contract_version":provenance["contract_version"],
        })
        caps.append({
            "id":capability_id("kavi",server,name),
            "provider":"kavi",
            "server":server,
            "name":name,
            "description":f"KAVI Dispatch Bridge declared {'write' if declared_write else 'read'} capability.",
            "input_schema":{},
            "fingerprint":fp,
            "effect":effect,
            "confidence":1.0,
            "analysis":{
                "effect":effect,
                "confidence":1.0,
                "risk_flags":risk_flags,
                "declared":declared,
                "evidence":[{
                    "kind":"declared_contract",
                    "field":"write",
                    "value":declared_write,
                    "source_sha":source_sha,
                }],
            },
            "annotations":{},
            "provenance":provenance,
        })
    inv={
        "version":"kcc.inventory.v0",
        "adapter":"kavi-dispatch-contract.v0",
        "provenance":provenance,
        "capabilities":caps,
    }
    inv["digest"]=digest(inv)
    return inv
