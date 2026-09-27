from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

_SCHEMAS={
    "kcc.capabilities.v1":"kcc.capabilities.v1.schema.json",
    "kcc.inventory.v1":"kcc.inventory.v1.schema.json",
    "kcc.inventory-lock.v1":"kcc.inventory-lock.v1.schema.json",
    "kcc.capsule.v1":"kcc.capsule.v1.schema.json",
    "kcc.signed-capsule.v1":"kcc.signed-capsule.v1.schema.json",
}


def schema_names() -> tuple[str,...]:
    return tuple(sorted(_SCHEMAS))


def get_schema(name: str) -> dict[str, Any]:
    filename=_SCHEMAS.get(str(name))
    if not filename:
        raise KeyError(f"Unknown KCC schema: {name}")
    data=(files("kavi_capability_compiler")/"schemas"/filename).read_text(encoding="utf-8")
    return json.loads(data)
