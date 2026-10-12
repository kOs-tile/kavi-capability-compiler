# KCC — 5-minute engineering demonstration

**Audience:** AI engineering hiring managers and builders evaluating agent authorization controls.

**Goal:** show an actual dispatch boundary, not screenshots, badges, or an AI-generated explanation. This demonstration exercises the public KCC SDK using **synthetic, local-only customer records**. No credentials, API calls, models, network operations, or external writes are used while running the demo.

## Motion explainer — authority before dispatch

![Animated KCC task-scoped authority and host dispatch](media/KCC_Authority_Explainer_Animated.svg)

**Watch it alongside the executable demo.** An agent may discover or request a tool, but execution requires a matching task-scoped capsule; denied calls must never reach the host dispatcher. See the [public engineering portfolio](https://kavi-engineering-evidence.vercel.app/).

## Run it (Python 3.11+)

From the [KCC repository](https://github.com/kOs-tile/kavi-capability-compiler), in a new terminal:

```bash
python -m venv .demo-venv
source .demo-venv/bin/activate  # Windows PowerShell: .demo-venv\Scripts\Activate.ps1
python -m pip install https://github.com/kOs-tile/kavi-capability-compiler/releases/download/v0.1.1/kavi_capability_compiler-0.1.1-py3-none-any.whl
python examples/recruiter_demo.py
```

The pinned wheel is the **published stable v0.1.1**. `main` contains unreleased v0.2 development code, which is intentionally **not required**. For a clean-install verification, run the final command from the checked-out repository with that new virtualenv active, without installing the repository in editable mode. The demo itself makes no requests; the one-time wheel installation downloads the public package.

A successful run ends with `KCC_5_MIN_DEMO: PASS` and a machine-readable `EVIDENCE_JSON=` line. Assertions fail with a nonzero exit status if an unauthorized call invokes the host dispatcher.

## Five-minute walkthrough

| Time | What to show | Engineering point |
| --- | --- | --- |
| 0:00–0:40 | Open the code and identify the two `read_customer` and `delete_customer` definitions | The **host owns** its tool registry and dispatcher |
| 0:40–1:30 | Build an inventory and compile a capsule that grants only one read, limited to `demo-customer-001` | Compile **task-scoped** authority instead of giving the agent all tools |
| 1:30–2:20 | Execute the allowed read once | An allowed operation invokes the real host callback exactly once |
| 2:20–3:40 | Attempt delete, a different customer ID, an extra argument, and an expired capsule | Rejection happens **before** invoking the host callback |
| 3:40–4:30 | Compile the deletion as `approval_required`; attempt it | The approval exception is a **handoff requirement**, not permission to run |
| 4:30–5:00 | Read the `EVIDENCE_JSON` output and assert `delete_dispatches: 0` | Distinguish a reason string from actual dispatch evidence |

## Expected proof

```text
  ALLOW read_customer(demo-customer-001): dispatched exactly once
  BLOCK ungranted deletion: capability_not_granted [dispatcher unchanged]
  BLOCK wrong customer: parameter_mismatch:customer_id [dispatcher unchanged]
  BLOCK extra argument: parameter_not_granted:export [dispatcher unchanged]
  BLOCK expired capsule: expired [dispatcher unchanged]
  BLOCK human-approval gate: approval_required [dispatcher unchanged]
KCC_5_MIN_DEMO: PASS
```

This is deterministic functional verification of the intended in-process KCC boundary, **not** a production security certification or penetration test.

## What this demo does *not* claim

- KCC does not intercept host code that bypasses `Guard` entirely. The host must mediate protected paths.
- The unsigned capsule is suitable for a trusted in-process demonstration. Cross-boundary execution needs independently authenticated transport or signed capsules.
- A compiled `approval_required` state does not implement an approval workflow; the host owns it.
- This demo uses **v0.1.1** and does not demonstrate the **unreleased v0.2 current-authority revocation resolver**.
- No real business/customer system, production tenant, external service, or durability guarantee is tested.

**Technical context:** [KCC SDK contracts](SDK_COMPATIBILITY.md) · [Integration recipes](INTEGRATION_RECIPES.md) · [Benchmark boundaries](BENCHMARK_REPORT_V0.1.md) · [External revocation case study](https://github.com/kOs-tile/kOs-tile/blob/main/case-studies/kcc-dispatch-time-revocation.md).
