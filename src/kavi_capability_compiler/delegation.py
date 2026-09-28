from __future__ import annotations

import copy
import re
import time
from collections.abc import Mapping
from typing import Any

from .core import (
    CAPSULE_VERSION,
    INVENTORY_VERSION,
    _inventory_integrity,
    _validate_parameter_constraints,
    digest,
    verify_capsule,
)

DELEGATION_REQUEST_VERSION="kcc.delegation-request.v1"
DELEGATED_CAPSULE_VERSION="kcc.delegated-capsule.v1"
_INHERITED_POLICY_SEMANTICS="inherited_authorization_provenance"
_CONSTRAINT_KEYS={"operations","parameters"}


def _is_sha256(value: Any) -> bool:
    return isinstance(value,str) and bool(re.fullmatch(r"[a-f0-9]{64}",value))


def _validate_constraint_shape(capability: Mapping[str,Any], constraints: Any) -> dict[str,Any]:
    if not isinstance(constraints,dict):
        raise ValueError(f"Invalid delegated constraints for {capability.get('id')}")
    unsupported=sorted(set(constraints)-_CONSTRAINT_KEYS)
    if unsupported:
        raise ValueError(f"Unsupported delegated constraint(s) for {capability.get('id')}: {unsupported}")

    if "operations" in constraints:
        ops=constraints["operations"]
        if not isinstance(ops,list) or not ops or not all(isinstance(x,str) and x for x in ops):
            raise ValueError(f"Invalid delegated operations constraint for {capability.get('id')}")
        if len(set(ops)) != len(ops):
            raise ValueError(f"Invalid delegated operations constraint for {capability.get('id')}")

    if "parameters" in constraints and not isinstance(constraints["parameters"],dict):
        raise ValueError(f"Invalid delegated parameter constraints for {capability.get('id')}")

    _validate_parameter_constraints(dict(capability),constraints)
    return copy.deepcopy(constraints)


def _rule_is_subset(child: Any, parent: Any) -> bool:
    if not isinstance(parent,dict):
        return not isinstance(child,dict) and child==parent

    if not isinstance(child,dict):
        # Runtime scalar rules use Python equality, whose equivalence classes
        # can cross structured type boundaries (for example 1 == True and
        # 1 == 1.0). Until scalar-domain subset semantics can be proven
        # independently of those aliases, structured -> scalar attenuation
        # fails closed.
        return False

    if parent.get("required") is True and child.get("required") is not True:
        return False

    parent_type=parent.get("type")
    child_type=child.get("type")
    if parent_type is not None:
        if child_type is None:
            return False
        if child_type!=parent_type and not (parent_type=="number" and child_type=="integer"):
            return False

    if "min" in parent:
        if "min" not in child or child["min"] < parent["min"]:
            return False
    if "max" in parent:
        if "max" not in child or child["max"] > parent["max"]:
            return False

    if "enum" in parent:
        if "enum" not in child:
            return False
        try:
            if not all(value in parent["enum"] for value in child["enum"]):
                return False
        except TypeError:
            return False

    if "max_length" in parent:
        if "max_length" not in child or child["max_length"] > parent["max_length"]:
            return False

    if "pattern" in parent:
        if child.get("pattern") != parent["pattern"]:
            return False

    return True


def _parameters_are_subset(child_constraints: Mapping[str,Any], parent_constraints: Mapping[str,Any]) -> bool:
    parent_has="parameters" in parent_constraints
    child_has="parameters" in child_constraints

    if not parent_has:
        return True
    if not child_has:
        return False

    parent_params=parent_constraints["parameters"]
    child_params=child_constraints["parameters"]
    if not isinstance(parent_params,dict) or not isinstance(child_params,dict):
        return False

    if not set(child_params).issubset(parent_params):
        return False

    for key,parent_rule in parent_params.items():
        if isinstance(parent_rule,dict) and parent_rule.get("required") is True:
            if key not in child_params:
                return False
            child_rule=child_params[key]
            if not isinstance(child_rule,dict) or child_rule.get("required") is not True:
                return False

    for key,child_rule in child_params.items():
        if not _rule_is_subset(child_rule,parent_params[key]):
            return False

    return True


def _operations_are_subset(child_constraints: Mapping[str,Any], parent_constraints: Mapping[str,Any]) -> bool:
    parent_has="operations" in parent_constraints
    child_has="operations" in child_constraints

    if not parent_has:
        return True
    if not child_has:
        return False

    try:
        return set(child_constraints["operations"]).issubset(parent_constraints["operations"])
    except TypeError:
        return False


def _constraints_are_subset(child_constraints: Mapping[str,Any], parent_constraints: Mapping[str,Any]) -> bool:
    return (
        _operations_are_subset(child_constraints,parent_constraints)
        and _parameters_are_subset(child_constraints,parent_constraints)
    )


def _validate_request(request: Any) -> dict[str,Any]:
    if not isinstance(request,Mapping):
        raise ValueError("Delegation request must be an object")
    req=copy.deepcopy(dict(request))
    allowed={"version","parent_capsule_id","task","ttl_seconds","capabilities"}
    unsupported=sorted(set(req)-allowed)
    if unsupported:
        raise ValueError(f"Unsupported delegation request field(s): {unsupported}")
    if req.get("version") != DELEGATION_REQUEST_VERSION:
        raise ValueError(f"Unsupported delegation request contract: {req.get('version')}")
    if not _is_sha256(req.get("parent_capsule_id")):
        raise ValueError("Invalid delegation parent_capsule_id")
    if "task" in req and req["task"] is not None and not isinstance(req["task"],str):
        raise ValueError("Delegation task must be a string or null")

    ttl=req.get("ttl_seconds",900)
    if not isinstance(ttl,int) or isinstance(ttl,bool) or ttl < 1 or ttl > 86400:
        raise ValueError("Delegation ttl_seconds must be an integer from 1 to 86400")

    capabilities=req.get("capabilities")
    if not isinstance(capabilities,list):
        raise ValueError("Delegation capabilities must be a list")

    seen=set()
    for item in capabilities:
        if not isinstance(item,dict):
            raise ValueError("Delegation capability entry must be an object")
        extra=sorted(set(item)-{"id","constraints"})
        if extra:
            raise ValueError(f"Unsupported delegation capability field(s): {extra}")
        cid=item.get("id")
        if not isinstance(cid,str) or not cid:
            raise ValueError("Delegation capability id must be a non-empty string")
        if cid in seen:
            raise ValueError(f"Duplicate delegated capability: {cid}")
        seen.add(cid)
        if "constraints" in item and not isinstance(item["constraints"],dict):
            raise ValueError(f"Invalid delegated constraints for {cid}")
    return req


def _verified_parent(parent: Any, inventory: Any, *, now: int) -> tuple[dict[str,Any],dict[str,Any]]:
    if not isinstance(parent,Mapping) or not isinstance(inventory,Mapping):
        raise ValueError("Invalid parent capsule or inventory")
    cap=copy.deepcopy(dict(parent))
    inv=copy.deepcopy(dict(inventory))
    if inv.get("version") != INVENTORY_VERSION or not _inventory_integrity(inv,semantic_ids=()):
        raise ValueError("Invalid inventory integrity")
    result=verify_capsule(cap,inv,now=now)
    if not result["valid"]:
        failed=[x["name"] for x in result["checks"] if not x["ok"]]
        raise ValueError(f"Invalid parent capsule: {failed}")
    return cap,inv


def attenuate_capsule(
    parent: Mapping[str,Any],
    request: Mapping[str,Any],
    inventory: Mapping[str,Any],
    *,
    now: int | None = None,
) -> dict[str,Any]:
    """Derive a child capsule whose effective authority is a subset of parent.

    Invalid or unprovable attenuation requests fail closed with ValueError.
    """
    current=int(now if now is not None else time.time())
    parent_cap,inv=_verified_parent(parent,inventory,now=current)
    req=_validate_request(request)

    if req["parent_capsule_id"] != parent_cap.get("capsule_id"):
        raise ValueError("Delegation request does not bind the supplied parent capsule")

    parent_grants={}
    for entry in parent_cap.get("grants",[]):
        cid=entry.get("id")
        if cid in parent_grants:
            raise ValueError(f"Invalid parent capsule: duplicate grant {cid}")
        parent_grants[cid]=entry

    inventory_by_id={x["id"]:x for x in inv.get("capabilities",[])}

    child_grants=[]
    for item in req["capabilities"]:
        cid=item["id"]
        if cid not in parent_grants:
            raise ValueError(f"Delegated capability is not a parent grant: {cid}")
        capability=inventory_by_id.get(cid)
        if capability is None:
            raise ValueError(f"Delegated capability absent from inventory: {cid}")

        parent_entry=parent_grants[cid]
        parent_constraints=_validate_constraint_shape(
            capability,
            parent_entry.get("constraints") or {},
        )
        if "constraints" in item:
            child_constraints=_validate_constraint_shape(capability,item["constraints"])
        else:
            child_constraints=copy.deepcopy(parent_constraints)

        if not _operations_are_subset(child_constraints,parent_constraints):
            raise ValueError(f"Delegated operation scope widens parent authority: {cid}")
        if not _parameters_are_subset(child_constraints,parent_constraints):
            raise ValueError(f"Delegated parameter scope widens parent authority: {cid}")

        child_entry={
            "id":cid,
            "fingerprint":parent_entry["fingerprint"],
            "effect":parent_entry["effect"],
            "risk_flags":copy.deepcopy(parent_entry.get("risk_flags",[])),
            "constraints":child_constraints,
        }
        child_grants.append(child_entry)

    request_digest=digest(req)
    ttl=req.get("ttl_seconds",900)
    expires_at=min(int(parent_cap["expires_at"]),current+ttl)
    if expires_at <= current:
        raise ValueError("Invalid parent capsule: no delegable lifetime remains")

    child={
        "version":CAPSULE_VERSION,
        "status":"ready",
        "issued_at":current,
        "expires_at":expires_at,
        "inventory_digest":parent_cap["inventory_digest"],
        "intent_digest":request_digest,
        "policy_digest":parent_cap["policy_digest"],
        "task":req["task"] if "task" in req else parent_cap.get("task"),
        "constraints":copy.deepcopy(parent_cap.get("constraints") or {}),
        "grants":child_grants,
        "approvals":[],
        "denials":[],
        "fail_closed":True,
    }
    child["capsule_id"]=digest(child)

    envelope={
        "version":DELEGATED_CAPSULE_VERSION,
        "parent_capsule_id":parent_cap["capsule_id"],
        "child_capsule":child,
        "attenuation_request_digest":request_digest,
        "provenance":{
            "kind":"attenuation",
            "parent_intent_digest":parent_cap["intent_digest"],
            "parent_policy_digest":parent_cap["policy_digest"],
            "child_policy_digest_semantics":_INHERITED_POLICY_SEMANTICS,
        },
        "fail_closed":True,
    }
    envelope["envelope_id"]=digest(envelope)

    verification=verify_delegated_capsule(envelope,parent_cap,inv,now=current)
    if not verification["valid"]:
        failed=[x["name"] for x in verification["checks"] if not x["ok"]]
        raise ValueError(f"Internal delegated capsule verification failed: {failed}")
    return envelope


def _attenuation_holds(child: Mapping[str,Any], parent: Mapping[str,Any], inventory: Mapping[str,Any]) -> bool:
    try:
        parent_entries=parent.get("grants",[])
        child_entries=child.get("grants",[])
        if not isinstance(parent_entries,list) or not isinstance(child_entries,list):
            return False

        parent_by_id={}
        for entry in parent_entries:
            if not isinstance(entry,dict) or not isinstance(entry.get("id"),str):
                return False
            if entry["id"] in parent_by_id:
                return False
            parent_by_id[entry["id"]]=entry

        child_seen=set()
        inventory_by_id={x["id"]:x for x in inventory.get("capabilities",[])}
        for entry in child_entries:
            if not isinstance(entry,dict) or not isinstance(entry.get("id"),str):
                return False
            cid=entry["id"]
            if cid in child_seen or cid not in parent_by_id:
                return False
            child_seen.add(cid)
            parent_entry=parent_by_id[cid]

            if entry.get("fingerprint") != parent_entry.get("fingerprint"):
                return False
            if entry.get("effect") != parent_entry.get("effect"):
                return False
            if entry.get("risk_flags") != parent_entry.get("risk_flags"):
                return False

            capability=inventory_by_id.get(cid)
            if capability is None:
                return False
            parent_constraints=_validate_constraint_shape(
                capability,
                parent_entry.get("constraints") or {},
            )
            child_constraints=_validate_constraint_shape(
                capability,
                entry.get("constraints") or {},
            )
            if not _constraints_are_subset(child_constraints,parent_constraints):
                return False
        return True
    except (KeyError,TypeError,ValueError):
        return False


def verify_delegated_capsule(
    envelope: Mapping[str,Any],
    parent: Mapping[str,Any],
    inventory: Mapping[str,Any],
    *,
    now: int | None = None,
) -> dict[str,Any]:
    """Verify envelope integrity, parent validity, and monotonic attenuation."""
    current=int(now if now is not None else time.time())
    checks=[]

    if not isinstance(envelope,Mapping):
        return {"valid":False,"checks":[{"name":"shape","ok":False}]}
    env=copy.deepcopy(dict(envelope))

    claimed=env.pop("envelope_id",None)
    try:
        integrity=isinstance(claimed,str) and claimed==digest(env)
    except (TypeError,ValueError):
        integrity=False
    checks.append({"name":"integrity","ok":integrity})
    checks.append({"name":"version","ok":envelope.get("version")==DELEGATED_CAPSULE_VERSION})
    checks.append({"name":"fail_closed","ok":envelope.get("fail_closed") is True})

    allowed_keys={
        "version","parent_capsule_id","child_capsule","attenuation_request_digest",
        "provenance","fail_closed","envelope_id",
    }
    shape=set(envelope).issubset(allowed_keys) and all(
        key in envelope
        for key in (
            "version","parent_capsule_id","child_capsule","attenuation_request_digest",
            "provenance","fail_closed","envelope_id",
        )
    )
    checks.append({"name":"shape","ok":shape})

    parent_valid=False
    inventory_valid=False
    parent_cap=copy.deepcopy(dict(parent)) if isinstance(parent,Mapping) else {}
    inv=copy.deepcopy(dict(inventory)) if isinstance(inventory,Mapping) else {}
    try:
        inventory_valid=(
            inv.get("version")==INVENTORY_VERSION
            and _inventory_integrity(inv,semantic_ids=())
        )
        parent_result=verify_capsule(parent_cap,inv,now=current) if inventory_valid else {"valid":False}
        parent_valid=bool(parent_result.get("valid"))
    except (TypeError,ValueError,KeyError):
        parent_valid=False
    checks.append({"name":"inventory","ok":inventory_valid})
    checks.append({"name":"parent","ok":parent_valid})

    parent_binding=(
        _is_sha256(envelope.get("parent_capsule_id"))
        and envelope.get("parent_capsule_id")==parent_cap.get("capsule_id")
    )
    checks.append({"name":"parent_binding","ok":parent_binding})

    child=envelope.get("child_capsule")
    child_valid=False
    if isinstance(child,Mapping) and inventory_valid:
        try:
            child_valid=verify_capsule(dict(child),inv,now=current)["valid"]
        except (TypeError,ValueError,KeyError):
            child_valid=False
    checks.append({"name":"child","ok":child_valid})

    source_state=(
        isinstance(child,Mapping)
        and child.get("status")=="ready"
        and child.get("approvals")==[]
        and child.get("denials")==[]
    )
    checks.append({"name":"child_source_state","ok":source_state})

    request_digest=envelope.get("attenuation_request_digest")
    provenance=envelope.get("provenance")
    provenance_ok=(
        _is_sha256(request_digest)
        and isinstance(child,Mapping)
        and child.get("intent_digest")==request_digest
        and child.get("policy_digest")==parent_cap.get("policy_digest")
        and child.get("inventory_digest")==parent_cap.get("inventory_digest")
        and child.get("constraints")==parent_cap.get("constraints")
        and isinstance(provenance,Mapping)
        and set(provenance)=={
            "kind","parent_intent_digest","parent_policy_digest","child_policy_digest_semantics"
        }
        and provenance.get("kind")=="attenuation"
        and provenance.get("parent_intent_digest")==parent_cap.get("intent_digest")
        and provenance.get("parent_policy_digest")==parent_cap.get("policy_digest")
        and provenance.get("child_policy_digest_semantics")==_INHERITED_POLICY_SEMANTICS
    )
    checks.append({"name":"provenance","ok":provenance_ok})

    time_ok=False
    if isinstance(child,Mapping):
        try:
            time_ok=(
                int(child.get("issued_at")) >= int(parent_cap.get("issued_at"))
                and int(child.get("expires_at")) <= int(parent_cap.get("expires_at"))
                and int(child.get("expires_at")) > int(child.get("issued_at"))
            )
        except (TypeError,ValueError):
            time_ok=False
    checks.append({"name":"time_attenuation","ok":time_ok})

    attenuation=False
    if isinstance(child,Mapping) and parent_valid and child_valid and inventory_valid:
        attenuation=_attenuation_holds(child,parent_cap,inv)
    checks.append({"name":"attenuation","ok":attenuation})

    valid=all(x["ok"] for x in checks)
    return {
        "valid":valid,
        "parent_capsule_id":parent_cap.get("capsule_id") if isinstance(parent_cap,dict) else None,
        "child_capsule_id":child.get("capsule_id") if isinstance(child,Mapping) else None,
        "checks":checks,
    }
