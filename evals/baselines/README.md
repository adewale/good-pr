# Frozen eval baselines

`good-pr-8e613be/` is the complete installable `skills/good-pr` tree from commit
`8e613beba912411217ae89b82fadb081a4380bb5`, the `main` revision used as PR #11's
GitHub baseline. It is committed so the three-way benchmark does not depend on a
mutable branch or a sibling checkout.

This directory is generated evidence: do not edit it as a second copy of the
skill. `scripts/build_eval_evidence.py verify` hashes paths, executable modes,
and bytes and fails CI if the frozen snapshot or evaluated skill tree drifts.

Verify it against a checkout of that commit with:

```sh
diff -ru <baseline-checkout>/skills/good-pr evals/baselines/good-pr-8e613be
```
