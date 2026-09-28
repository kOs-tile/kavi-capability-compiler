# KAVI Capability Compiler v0.1.1

KCC v0.1.1 is a narrow security/correctness patch for the public alpha.

## What changed

- structured parameter-rule objects are now validated at capsule compile time
- unsupported or malformed parameter predicates are rejected instead of being silently ineffective
- runtime values that cannot be evaluated against numeric or length bounds fail closed with a deterministic `parameter_type_mismatch:<name>` decision

The patch does not expand authority and does not add a framework-specific runtime.

## Compatibility

The public compatibility contracts remain unchanged: `kcc.sdk.v1`, `kcc.capabilities.v1`, `kcc.inventory.v1`, `kcc.inventory-lock.v1`, `kcc.capsule.v1`, and `kcc.signed-capsule.v1`.

The default core still has zero required third-party runtime dependencies.

## Install

After publication:

```bash
python -m pip install https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.1/kavi_capability_compiler-0.1.1-py3-none-any.whl
```

The GitHub Pages Simple Repository will be redeployed from the verified v0.1.1 release assets after publication.

## Security boundary

This release strengthens fail-closed parameter-constraint handling. It is not a security certification and does not change KCC's documented host-responsibility boundaries.
