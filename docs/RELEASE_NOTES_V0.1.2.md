# KAVI Capability Compiler v0.1.2

v0.1.2 is a narrow security/correctness patch candidate for the stable v0.1.x series.

## Security correction

- Constrained literal parameter values now require the field to be present as well as equal to the authorized value.
- When a literal-constrained field is omitted, authorization fails closed **before** host dispatch instead of silently treating it as optional.
- Structured predicates that explicitly declare `required: false` retain optional semantics; `required: true` remains mandatory.
- A dedicated Guard/dispatcher regression suite verifies denial of omitted, altered, and extra arguments and successful dispatch of an exactly permitted read.

## Compatibility

Existing public contracts remain unchanged: `kcc.sdk.v1`, `kcc.capabilities.v1`, `kcc.inventory.v1`, `kcc.inventory-lock.v1`, and `kcc.capsule.v1`.

The default core still requires no third-party runtime dependencies. Previously accepted calls missing a constrained literal are now intentionally denied; consumers must supply the authorized argument.

## Install

After the v0.1.2 release has been published and verified:

```bash
python -m pip install https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.2/kavi_capability_compiler-0.1.2-py3-none-any.whl
```

## Disclosure and limits

This is a patch candidate until release artifacts and independent tests are verified. Existing v0.1.1 artifacts are immutable and remain unpatched. No production deployments, end-to-end agent routes or third-party security certification are asserted by this change.
