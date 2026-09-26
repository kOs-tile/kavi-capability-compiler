# Universal Capability Manifest

`kcc.capabilities.v1` is KCC's framework-neutral capability interchange format.

An agent framework does **not** need to adopt KCC internally. It may either:

1. provide one of the built-in source formats; or
2. emit this manifest directly.

The compiler path is then:

```
external runtime/tool registry
        |
        v
source adapter
        |
        v
kcc.capabilities.v1
        |
        v
KCC inventory -> task intent + policy -> execution capsule
        |
        v
generic runtime guard -> caller-supplied dispatcher
```

## Capability identity

Each capability has:

- `namespace`
- `name`
- `description`
- `input_schema`
- `annotations`
- semantic `fingerprint`
- non-authoritative `source` provenance

KCC identity is:

`kcc:<namespace>:<name>`

Same-named tools in different namespaces do not collide.

## Semantic fingerprint

A capability fingerprint covers authority-relevant semantic metadata:

- namespace
- name
- description
- input schema
- annotations

It deliberately excludes provenance such as source file, framework name, revision, or transport metadata.

Therefore:

- moving the same capability between source formats does not create authority drift;
- changing its schema or authority-relevant metadata does create drift.

## Manifest digest

The manifest digest binds the sorted set of:

`namespace + name + capability fingerprint`

Source provenance is retained in the artifact but does not change the semantic authority digest.

## Built-in adapters

Current built-in source formats:

- `generic`
- `mcp`
- `openai`
- `anthropic`
- `openapi`

Example:

```bash
kcc manifest tools.json \
  --format openai \
  --namespace my-agent \
  -o capabilities.json

kcc scan-manifest capabilities.json -o inventory.json
```

After `scan-manifest`, the compiler and runtime guard are source-format agnostic.

## External adapter contract

A framework integration does not need to subclass a KCC base class.

The stable boundary is the manifest itself.

An external adapter should:

1. observe the framework's real capability/tool registry;
2. emit deterministic `kcc.capabilities.v1`;
3. preserve schemas and declared annotations without inventing missing metadata;
4. keep credentials and secret values out of the manifest;
5. place non-authoritative provenance under `source`;
6. avoid pre-classifying security effects unless the source natively declares them.

KCC performs authority analysis after normalization.

## Current equivalence gate

CI expresses the same capability set in five formats:

- generic JSON
- MCP
- OpenAI function tools
- Anthropic tools
- OpenAPI

The gate requires:

- one semantic manifest digest across all five;
- one KCC inventory digest across all five;
- identical compiled grants;
- allowed calls reach the generic dispatcher;
- denied calls never reach the dispatcher.

Specific systems such as Hermes, Codex, KAVI, LangGraph, or custom agents are therefore validation targets, not compiler dependencies.
