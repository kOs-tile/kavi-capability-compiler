# Product thesis

KAVI Capability Compiler compiles the smallest verifiable authority an AI agent needs to execute a task.

## Inputs
1. observed capability inventory
2. explicit task intent
3. deterministic policy

## Output
A portable execution capsule containing grants, approvals, denials, fingerprints, constraints, provenance digests, and expiry.

## Differentiation hypothesis
Runtime gates answer **should this call execute?** KCC focuses on the prior question: **why did this execution have this capability at all?**

KCC is not an agent framework, IAM replacement, generic policy engine, or MCP-only gateway.

## Safety invariant
**Unknown authority never becomes silent authority.**
