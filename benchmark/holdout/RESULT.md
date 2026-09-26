# Sealed holdout result — M1

Classifier freeze:
- branch checkpoint: `e30e88c61f495f2876d93fdeac0b153cb70825e2`
- classifier blob: `6624647b95df4721dd2500195d658d822f421105`

The holdout labels were committed before the evaluator was added and before the first evaluation was run.

## First reveal

- samples: 63
- surfaces: 2
- dangerous samples: 27
- accuracy: 80.95%
- dangerous recall: 100%
- false-safe: 0 / 27
- overblocking: 0%
- unknown rate: 23.81%

The result is intentionally not back-fitted. The classifier was not changed in response to this first reveal.

## Interpretation

The primary safety invariant generalized to two previously unseen surfaces: no dangerous capability was silently reduced to ordinary read authority.

General classification quality is weaker than on the development corpus. The main gap is uncertainty: almost one quarter of the unseen tools remain `unknown`. That is acceptable for fail-closed safety, but it increases approval burden and limits automation.

After this first reveal, this dataset is no longer considered blind. It becomes a regression set. Any later product/release claim requiring unseen evaluation must use a new sealed holdout.
