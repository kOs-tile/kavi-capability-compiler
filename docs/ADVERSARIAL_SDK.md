# Adversarial SDK Benchmark

KCC's adversarial SDK benchmark tests the embedded enforcement boundary before broader framework integration examples are treated as reference patterns.

The benchmark is deterministic and local. It uses no paid API or hosted service.

## Enforced cases

CI requires KCC to block or detect:

- capsule tampering
- manifest tampering
- same-name namespace collision
- post-compile schema/authority drift
- expired capsules
- wrong signing keys
- approval bypass attempts that still pass through Guard
- stale inventory locks
- capabilities added after compilation
- extra runtime parameters outside a compiled parameter constraint

The canonical runtime pattern binds Guard to the current inventory:

```python
guard = kcc.Guard.from_capsule(capsule, inventory=current_inventory)
```

This binding turns post-compile capability-surface changes into a pre-dispatch denial.

## Explicit host boundaries

Two cases are intentionally not misrepresented as KCC protections.

### Replay

A valid capsule may authorize multiple calls until expiry. KCC v0.1 has no distributed replay database. Hosts that require one-shot execution must maintain execution/replay state outside KCC.

### Direct dispatcher bypass

KCC mediates calls that cross Guard. It cannot stop the host application from invoking its own dispatcher directly. The host is responsible for making Guard the mandatory path for protected tool execution.

## CI contract

`benchmark/adversarial_sdk.py` emits structured JSON and `tests/test_adversarial_benchmark.py` gates it in the normal test suite.

CI requires every enforceable adversarial case to pass while replay and direct-dispatch boundaries remain explicitly classified as host responsibilities rather than claimed KCC protections.
