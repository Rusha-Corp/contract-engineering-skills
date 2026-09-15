---
name: contract-admission
description: Run fail-closed Contract Engineering design and packet admission.
---

# Contract Admission

Run the repository validators before any worker execution:

```text
python3 scripts/validate-design-contracts.py --root .contract-engineering/designs
python3 scripts/validate-contract-records.py
python3 scripts/validate-admission.py --root .contract-engineering --all-ready
```

Block on missing design approval, stale artifacts, missing reviews, scope
violations, missing criterion references, incomplete dependencies, lock
conflicts, missing owners, or invalid records. Do not infer approval from a
plan, chat message, or command invocation. Show blocked reasons and leave the
packet state unchanged.
