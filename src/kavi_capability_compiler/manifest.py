from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from .core import INVENTORY_VERSION, analyze_capability, capability_id, digest

SCHEMA_VERSION = "kcc.capabilities.v1"


def _schema(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, Mapping) else {}


def _source(kind: str, metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    out={"kind":kind}
    for key,value in (metadata or {}).items():
        if value is not None:
            out[str(key)]=deepcopy(value)
    return out


def _entry(
    *,
    namespace: str,
    name: str,
    description: str = "",
    input_schema: Mapping[str, Any] | None = None,
    annotations: Mapping[str, Any] | None = None,
    source_kind: str,
    source_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    namespace=str(namespace).strip()
    name=str(name).strip()
    if not namespace or not name:
        raise ValueError("Capability namespace and name are required")
    semantic={
        "namespace":namespace,
        "name":name,
        "description":str(description or ""),
        "input_schema":_schema(input_schema),
        "annotations":deepcopy(dict(annotations or {})),
    }
    return {
        **semantic,
        "fingerprint":digest(semantic),
        "source":_source(source_kind,source_metadata),
    }


def build_manifest(capabilities: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows=[]
    seen=set(); seen_ids=set()
    for raw in capabilities:
        row=deepcopy(dict(raw))
        key=(str(row.get("namespace","")),str(row.get("name","")))
        if not all(key):
            raise ValueError("Manifest capability missing namespace or name")
        if key in seen:
            raise ValueError(f"Duplicate capability identity: {key[0]}:{key[1]}")
        seen.add(key)
        canonical_id=capability_id("kcc",key[0],key[1])
        if canonical_id in seen_ids:
            raise ValueError(f"Duplicate canonical capability identity: {canonical_id}")
        seen_ids.add(canonical_id)
        expected=_entry(
            namespace=key[0],
            name=key[1],
            description=row.get("description",""),
            input_schema=row.get("input_schema") or {},
            annotations=row.get("annotations") or {},
            source_kind=(row.get("source") or {}).get("kind","unknown"),
            source_metadata={k:v for k,v in (row.get("source") or {}).items() if k!="kind"},
        )["fingerprint"]
        if row.get("fingerprint") and row["fingerprint"] != expected:
            raise ValueError(f"Capability fingerprint mismatch: {key[0]}:{key[1]}")
        row["fingerprint"]=expected
        rows.append(row)
    rows.sort(key=lambda x:(x["namespace"],x["name"]))
    manifest={
        "schema_version":SCHEMA_VERSION,
        "capabilities":rows,
    }
    manifest["digest"]=digest({
        "schema_version":SCHEMA_VERSION,
        "capabilities":[
            {"namespace":x["namespace"],"name":x["name"],"fingerprint":x["fingerprint"]}
            for x in rows
        ],
    })
    return manifest


def from_generic(
    capabilities: Iterable[Mapping[str, Any]],
    *,
    namespace: str = "generic",
    source_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows=[]
    for raw in capabilities:
        rows.append(_entry(
            namespace=str(raw.get("namespace") or namespace),
            name=str(raw.get("name") or raw.get("id") or ""),
            description=str(raw.get("description") or ""),
            input_schema=raw.get("input_schema") or raw.get("inputSchema") or raw.get("parameters") or {},
            annotations=raw.get("annotations") or {},
            source_kind="generic-json",
            source_metadata=source_metadata,
        ))
    return build_manifest(rows)


def from_mcp_tools(
    tools: Iterable[Mapping[str, Any]],
    *,
    namespace: str,
    server: str | None = None,
) -> dict[str, Any]:
    return build_manifest([
        _entry(
            namespace=namespace,
            name=str(t.get("name") or ""),
            description=str(t.get("description") or ""),
            input_schema=t.get("inputSchema") or {},
            annotations=t.get("annotations") or {},
            source_kind="mcp",
            source_metadata={"server":server},
        )
        for t in tools
    ])


def from_openai_tools(
    tools: Iterable[Mapping[str, Any]],
    *,
    namespace: str,
) -> dict[str, Any]:
    rows=[]
    for raw in tools:
        if raw.get("type") != "function" or not isinstance(raw.get("function"), Mapping):
            raise ValueError("Only OpenAI function tools are supported by this adapter")
        fn=raw["function"]
        rows.append(_entry(
            namespace=namespace,
            name=str(fn.get("name") or ""),
            description=str(fn.get("description") or ""),
            input_schema=fn.get("parameters") or {},
            annotations={},
            source_kind="openai-function",
        ))
    return build_manifest(rows)


def from_anthropic_tools(
    tools: Iterable[Mapping[str, Any]],
    *,
    namespace: str,
) -> dict[str, Any]:
    return build_manifest([
        _entry(
            namespace=namespace,
            name=str(t.get("name") or ""),
            description=str(t.get("description") or ""),
            input_schema=t.get("input_schema") or {},
            annotations={},
            source_kind="anthropic-tool",
        )
        for t in tools
    ])


def _openapi_schema(operation: Mapping[str, Any]) -> dict[str, Any]:
    request=((operation.get("requestBody") or {}).get("content") or {}).get("application/json") or {}
    body=request.get("schema")
    parameters=operation.get("parameters") or []
    props={}
    required=[]
    for p in parameters:
        if not isinstance(p, Mapping) or not p.get("name"):
            continue
        props[str(p["name"])]=deepcopy(p.get("schema") or {})
        if p.get("required"):
            required.append(str(p["name"]))
    if isinstance(body, Mapping) and body:
        if body.get("type")=="object":
            props.update(deepcopy(body.get("properties") or {}))
            required.extend(str(x) for x in (body.get("required") or []))
        else:
            props["body"]=deepcopy(body)
            required.append("body")
    out={"type":"object","properties":props}
    if required:
        out["required"]=sorted(set(required))
    return out


def from_openapi(
    spec: Mapping[str, Any],
    *,
    namespace: str,
    source_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows=[]
    for path,item in (spec.get("paths") or {}).items():
        if not isinstance(item, Mapping):
            continue
        for method in ("get","post","put","patch","delete"):
            op=item.get(method)
            if not isinstance(op, Mapping):
                continue
            name=op.get("operationId")
            if not name:
                continue
            rows.append(_entry(
                namespace=namespace,
                name=str(name),
                description=str(op.get("description") or op.get("summary") or ""),
                input_schema=_openapi_schema(op),
                annotations={},
                source_kind="openapi",
                source_metadata={"method":method.upper(),"path":str(path),**dict(source_metadata or {})},
            ))
    return build_manifest(rows)


def scan_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported capability manifest: {manifest.get('schema_version')}")
    checked=build_manifest(manifest.get("capabilities") or [])
    if manifest.get("digest") != checked["digest"]:
        raise ValueError("Capability manifest digest mismatch")
    caps=[]
    for row in checked["capabilities"]:
        tool={
            "name":row["name"],
            "description":row.get("description",""),
            "inputSchema":row.get("input_schema") or {},
            "annotations":row.get("annotations") or {},
        }
        analysis=analyze_capability(tool)
        caps.append({
            "id":capability_id("kcc",row["namespace"],row["name"]),
            "provider":"kcc-manifest",
            "server":row["namespace"],
            "name":row["name"],
            "description":row.get("description",""),
            "input_schema":row.get("input_schema") or {},
            "fingerprint":row["fingerprint"],
            "effect":"unknown" if analysis["effect"]=="mixed" else analysis["effect"],
            "confidence":analysis["confidence"],
            "analysis":analysis,
            "annotations":row.get("annotations") or {},
            "source":row.get("source") or {"kind":"unknown"},
        })
    inv={"version":INVENTORY_VERSION,"adapter":"universal-manifest.v1","capabilities":caps}
    inv["digest"]=digest({
        "version":inv["version"],
        "adapter":inv["adapter"],
        "capabilities":sorted(
            [{"id":x["id"],"fingerprint":x["fingerprint"]} for x in caps],
            key=lambda x:x["id"],
        ),
    })
    return inv
