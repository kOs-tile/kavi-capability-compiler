# M1 Failure Taxonomy — 101 Capability Checkpoint

This document records failures before changing the classifier.

## Frozen checkpoint

- Samples: 101
- Dangerous samples: 43
- Accuracy: 68.32%
- False-safe count: 0
- False-safe rate: 0%
- Classifier unknown rate is reported by CI; aggregate accuracy is not treated as the primary safety metric.

These numbers describe this benchmark snapshot only.

## Observed failure families

### F1 — Effect and destructiveness are conflated

Examples such as filesystem `write_file`, `edit_file`, and `move_file` demonstrate that a capability can have a write/move effect while also being destructive.

A single enum cannot faithfully represent both dimensions.

**Implication:** Authority Model v2 should separate semantic effect from risk properties.

### F2 — Context-dependent browser actions do not have one stable effect

`browser_click`, `browser_type`, `browser_press_key`, `browser_tabs`, and similar tools can be harmless UI interaction or trigger external mutation depending on target and arguments.

**Implication:** some capabilities require operation/parameter-level constraints or approval rather than a tool-level safe/unsafe label.

### F3 — Lexical rules miss semantically obvious mutations

Examples include `add_observations`, Git operations, and verbs not present in the seed rule list.

**Implication:** expanding a verb dictionary alone will overfit. Evidence needs structure and provenance.

### F4 — Safe reads can remain unknown

Metadata/context operations with neutral names or descriptions can fail lexical read detection.

**Implication:** declared read-only annotations and provider evidence are useful, but remain hints rather than authority.

### F5 — Tool annotations can contradict stronger evidence

An adversarial regression test proved that `readOnlyHint=true` could previously turn a destructive capability into ordinary read authority.

**Invariant:** strong contradictory dangerous evidence must win over declared hints.

### F6 — Multi-operation tools break tool-level classification

Some tools multiplex read and mutation methods behind one capability.

**Implication:** the compiler must be able to constrain operation names and parameters inside a capability, not only include/exclude whole tools.

## Authority Model v2 requirements

Do not implement until these requirements are represented in tests:

1. Separate `effect` from `risk_flags`.
2. Preserve evidence with source and confidence.
3. Represent declared annotations separately from inferred properties.
4. Support mixed/context-dependent effect.
5. Allow operation/parameter constraints in execution capsules.
6. Unknown remains fail-closed.
7. No probabilistic component may silently expand authority.

The next benchmark stage should test this model against the frozen 101-capability corpus before expanding the product surface.

### F7 — Substring matching creates false-safe semantic collisions

The 415-capability expansion exposed four false-safe cases. Raw substring matching treated incidental words as actions: a Redis `list` noun made `lpush`/ `rpush` look read-only, “mark … as read” made a Slack mutation look like a read, and multi-action membership management collapsed to its list operation.

The fix was architectural rather than a four-name exception list: classification now prioritizes tool-name action tokens, explicit high-impact evidence, mixed-operation descriptions, and only then the description's leading action.

On the canonical 487-capability / 30-surface checkpoint this family is covered by regression tests and the false-safe count is zero.

## M1 expanded checkpoint

- Capabilities: 487
- Distinct canonical surfaces: 30
- Dangerous recall: 100%
- False-safe count: 0
- Accuracy: 89.73%
- Unknown rate: 11.91%
- Overblocking rate: 3.50%
- Mean task authority reduction: 99.49%
- Drift recall: 100%

These are benchmark checkpoint measurements, not production security guarantees.
