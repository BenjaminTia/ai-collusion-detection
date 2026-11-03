# Immediate next step

Diagnose the existing scripted calibration failure before any paid LLM collection.

1. Inspect which innocent pairs trigger alarms when the full public cue is observed. Compare their score distributions and marginal action distributions against the independent-null calibration set. This separates estimator bugs from a mismatched null model.
2. Evaluate a candidate within-observed-state permutation calibration on fresh, separate scripted runs. Preserve the original results. This tests conditional independence under the recorded state, not intent or collusion. Missing context remains a confound; permutation cannot cure it.
3. Freeze the estimator, null, prompts and failure-handling protocol. Then run a small one-model LLM pilot to check protocol compliance, action variation, outputs, runtime and cost before a larger batch.

No paid model runs until model access/pricing are checked and a spending cap is authorised. No paper claim beyond the completed scripted evidence. Benjamin need not implement this himself; registration/account approval or a budget decision may need his input.
