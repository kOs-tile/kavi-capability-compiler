# KAVI Capability Compiler v0.2.0

> Development release notes. v0.2.0 is not published yet. The latest stable public release remains v0.1.1 until the final v0.2.0 publication gates are completed.

## Scope currently on main

- deterministic delegation-request and delegated-capsule contracts
- provable authority attenuation from a verified parent capsule to a narrower child capsule
- additive public schemas `kcc.delegation-request.v1` and `kcc.delegated-capsule.v1`
- fail-closed capability, operation, parameter, lifetime, inventory, and trust attenuation checks
- safe coding-agent integration guidance for adding KCC to an existing project without inventing broad policy
- clean installed-wheel execution of the public delegation API and delegated-child Guard boundary
- deterministic classifier hardening for explicit exchange/trading order mutations
- credential-free real-consumer exchange execution boundary dogfood
- public deterministic capability-ID construction for external planning layers
- no new required dependency in the default core
- existing `kcc.capsule.v1` and `kcc.sdk.v1` remain intact

## Evidence currently on main

### Delegation safety

The v0.2 development line now proves the bounded delegation path both structurally and at runtime:

- parent authority can derive only a deterministic subset child
- operation, parameter, capability, lifetime, inventory, and trust widening fail closed
- structured-parent to scalar-child attenuation is rejected in v1 because Python equality aliases can widen an apparently exact scalar domain across types
- the clean installed wheel derives and verifies a narrower child capsule
- that child can be loaded into the public Guard
- an allowed child call reaches the host dispatcher exactly once
- operation and parameter widening are denied before host dispatch

### Real-consumer stabilization

The first reproduced real-consumer authority-semantic defect was an exchange execution capability whose live order submission shape fell through to generic `write` instead of `financial`.

The bounded fix:
- promotes explicit exchange/trading limit/market order mutations to `financial`
- keeps generic work-order creation as ordinary `write`
- keeps order-status fetch behavior as `read`
- preserves deterministic classification with no model or probabilistic authority decision

A minimized real-consumer exchange execution case study now also proves:
- only the approved limit-order capability is granted for one execution
- symbol, side, quantity, and limit price can be narrowed to the approved leg
- wrong symbol, opposite side, larger quantity, and an ungranted market-order call never reach the host dispatcher
- consumer-owned idempotency metadata can remain host-injected after authorization rather than becoming agent-controlled authority
- no exchange, network, credentials, model, or paid API is required for the regression evidence

### External identity contract

A second real integration audit found that an external capability planner could correctly prepare a KCC task intent for simple snake_case tool names yet mis-predict the inventory ID when a valid server/tool name contained case differences, spaces, `:`, or `%`.

v0.2 exposes KCC's existing deterministic `capability_id(...)` constructor publicly and documents its normalization/escaping rules. This does not change any existing capability ID or authority behavior; it removes the need for external planners to copy a private identity algorithm.

### Adoption

The repository includes a safe coding-agent integration path so a user can hand the KCC repository to a coding agent without asking the agent to invent security semantics.

The integration contract requires:
- discovery of the real dispatcher boundary
- audit before enforcement
- fail-closed treatment of unknown authority
- no protected bypass path
- regression evidence that denied calls reach the dispatcher zero times
- published v0.1.1 as the default stable install target unless unreleased v0.2/main is explicitly requested

## Security boundary

Delegation may narrow verified parent authority. It may not manufacture trust, widen capabilities, turn approvals/denials into grants, escape inventory drift, extend lifetime, or rely on probabilistic reasoning to prove authority.

KCC also does not replace consumer domain-risk accounting. In the exchange execution dogfood, business portfolio/risk checks remain consumer responsibility; KCC bounds what the execution path is authorized to dispatch.

## Publication status

v0.2.0 remains unreleased. External feedback collection and final release-scope selection are still open.

No v0.2.0 tag or release should exist until the final scope is evidence-backed, main is fully green, the manual exact-SHA release dry-run is reviewed, and publication is explicitly confirmed.

When published, the canonical direct wheel URL will be:

https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.2.0/kavi_capability_compiler-0.2.0-py3-none-any.whl

Until then, use the published v0.1.1 install instructions in README.
