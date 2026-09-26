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

This is a useful negative result. A package upgrade is not itself authority drift. KCC should not manufacture a drift event merely because a version changed.

The first CI gate incorrectly assumed that any version change should produce an authority change. That assumption was removed. A wider published-version window is tested separately to obtain a real authority-change example if one exists.
