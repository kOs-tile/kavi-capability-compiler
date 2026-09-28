# KAVI Capability Compiler v0.2.0

> Development release notes. v0.2.0 is not published yet. The latest stable public release remains v0.1.1 until the final v0.2.0 publication gates are completed.

## Scope currently on main

- deterministic delegation-request and delegated-capsule contracts
- provable authority attenuation from a verified parent capsule to a narrower child capsule
- additive public schemas `kcc.delegation-request.v1` and `kcc.delegated-capsule.v1`
- fail-closed capability, operation, parameter, lifetime, inventory, and trust attenuation checks
- no new required dependency in the default core
- existing `kcc.capsule.v1` and `kcc.sdk.v1` remain intact

## Security boundary

Delegation may narrow verified parent authority. It may not manufacture trust, widen capabilities, turn approvals/denials into grants, escape inventory drift, extend lifetime, or rely on probabilistic reasoning to prove authority.

Structured-parent to scalar-child parameter attenuation is rejected in v1 because Python equality aliases can widen an apparently exact scalar domain across types.

## Publication status

No v0.2.0 tag or release should exist until the final scope is evidence-backed, main is fully green, the manual exact-SHA release dry-run is reviewed, and publication is explicitly confirmed.

When published, the canonical direct wheel URL will be:

https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.2.0/kavi_capability_compiler-0.2.0-py3-none-any.whl

Until then, use the published v0.1.1 install instructions in README.
