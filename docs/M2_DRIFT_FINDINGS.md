# M2 Published-Version Drift Findings

KCC compares live discovered capability fingerprints, not package version numbers.

## Filesystem 2026.7.10 → 2026.8.31

First published-version experiment:

- old tool count: 14
- new tool count: 14
- added: 0
- removed: 0
- changed fingerprints: 0
- old inventory digest == new inventory digest

**Result: clean.**

A package upgrade is not itself authority drift. KCC correctly did not manufacture a drift event merely because a version changed.

The first CI gate incorrectly assumed that any version change should produce an authority change. That assumption was corrected.

## Filesystem 2026.1.14 → 2026.8.31

A wider published-version window produced real authority metadata drift:

- old tool count: 14
- new tool count: 14
- added: 0
- removed: 0
- changed fingerprints: **14**
- inventory digest changed

Every live-discovered filesystem capability changed fingerprint, including read, write, edit, move, search, metadata, and directory operations.

**Result: drift detected even though the tool count and tool IDs remained stable.**

This demonstrates why KCC locks the observed capability contract rather than only tool names or package versions. Changes to description, schema, or annotations remain authority-relevant evidence.
