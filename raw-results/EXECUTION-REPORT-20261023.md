# Apart experiment execution and recovery report

Status: scripted diagnosis and fresh-run baseline completed; Modal GPU attempt blocked by account prerequisite. A real CPU model smoke test completed. No valid 3 x 30-round per-condition pilot completed. Nothing submitted.

## What happened

The first execution got stuck in a chain of fallback attempts rather than closing with a clear checkpoint. Modal authentication worked, but the platform rejected GPU functions because no payment method was on file. Modal credits did not remove that prerequisite. An attempted CPU benchmark and local model download then consumed time without producing a pilot. This was execution-management failure, not a research result.

Subsequent recovery found that the expected `llm_protocol.py` was present as `llm_protocol 2.py`, breaking imports. The cause of that rename is not established; iCloud is a suspected source, not a verified diagnosis. A validated worktree was copied outside iCloud to `C:\Users\Benjamin\AppData\Local\hermes\cache\scratch\apart-recovery`. Corrected code and test receipts were copied back with SHA256 equality checks. `results/recovery-files-manifest.json` records those files.

The Hugging Face CLI download failed with `File reconstruction error: CAS Client Error: Format error: I/O error: error decoding response body` in the Xet transport. A direct HTTP range probe returned a real 16,777,216-byte range in 2.7084908485412598 seconds, but a subsequent full ranged download did NOT complete within a 260-second hard limit. Partial files are not usable weights and have not been claimed as verified model artifacts. No cache was purged.

## 1. Scripted false-alarm diagnosis: completed

Sources: original `results/scripted/trajectories.jsonl`, `metadata.json`, and replay of the original independent-null calibration seeds. Original results preserved.

- Original benign/full-cue net alarms: 33/100 trajectories.
- Every one of those 33 net alarms was on the two genuinely independent agents, not on the cue-following pair.
- With exact cue conditioning, the cue-following columns are constant inside each state. Their CMI with each other and with the independent columns is zero.
- The independent-independent pair retains finite-sample CMI bias: mean 0.00584 nats. Its competing influence terms are zero, so its net score equals that positive empirical CMI.
- In the all-independent calibration population, competitor terms are themselves positive sample estimates, pulling the net distribution down. Its threshold therefore transfers badly to the structured benign population.
- This is null-distribution mismatch. It does not show intentional coordination by those independent agents or a failed conditioning identity.

Artifacts:
- `src/diagnose_calibration.py`
- `results/diagnosis/calibration-diagnosis.json`
- `results/diagnosis/calibration-diagnosis.md`

## 2. Within-observed-state permutation baseline: completed on fresh runs

Implementation: independently shuffle each agent's action column inside each observed-state stratum; recompute all six pair scores; use a per-run maximum-score null. 199 permutations per condition/run/view. Higher empirical 95th percentile, floored at zero; strict score > threshold. The plus-one Monte Carlo p-value is logged separately; it is not the decision rule used in these tables.

Scope:
- 100 fresh runs per condition, 1,000 rounds per run.
- 4 conditions, 4 observation views, 2 methods.
- 400 fresh trajectories and 3,200 distinct result rows.
- Simulation seeds 3000000 + run index; earlier evaluation used 2000000 + index. Same seed indices across conditions intentionally share a random-number starting point; they are not additional independent replications across views.
- In recovery, all 3,200 saved maximum scores were checked against deterministic replay to tolerance 1e-12. Complete fresh trajectories were saved. This replay verifies saved observed scores, not a second independent replication of every permutation draw.

Fresh benign runs, exact cue:
- CMI: original threshold 1/100 alarms; permutation baseline 4/100.
- Net: original threshold 39/100 alarms; permutation baseline 4/100.
- The earlier 33/100 and fresh 39/100 refer to different evaluation seeds. They are not contradictory or interchangeable.

Fresh independent runs, permutation any-alarm rates:
- No cue: CMI 6/100, net 5/100.
- Full cue: CMI 7/100, net 5/100.
- 10% corrupted cue: CMI 3/100, net 2/100.
- 30% corrupted cue: CMI 4/100, net 4/100.

Fresh benign runs, missing cue or 10%/30% corruption:
- Both detectors alarmed on 100/100 runs for each of these views, even with permutation calibration.
- Explanation: observed actions retain dependence through the inadequately observed common cause, whereas independent column shuffling destroys that association in the candidate null. It is NOT true that independent shuffling preserves equality between the two columns. A mistaken code comment and an incorrect unit-test assertion about this were repaired.
- These are false accusations relative to a benign-policy label, but not false rejections of the conditional-independence null when the recorded state is insufficient.

Fresh seeded runs:
- Both detectors: 100/100 any alarms and top-1 credit 1.0 under every view.

Fresh combined runs:
- Both detectors: 100/100 any alarms under every view.
- Top-1 assigned-pair credit: no cue 0.0; full cue 1.0; 10% corruption 1.0; 30% corruption 0.0.
- Changing calibration changes alarm decisions, not the underlying score ranking. These toy results do not establish an advantage of net over CMI.

Validity limits: calibration targets the complete conditional-independence null per detector. It does not establish strong false-discovery control for innocent pairs in arbitrary alternative mixtures, control across all views/methods, intent detection, or harmful collusion. 4/100 is a sample outcome, not proof of a universal 4% population error rate.

Artifacts:
- `src/permutation_calibration.py`
- `tests/test_permutation.py`
- `results/permutation/runs.csv`
- `results/permutation/summary.csv`
- `results/permutation/metadata.json`
- `results/permutation/fresh-trajectories.jsonl`
- `results/permutation_run.log`

## 3. Modal GPU attempts: real attempts, blocked before GPU inference

Workspace: `benjaminharristia`. Modal client 1.6.2.

- App `ap-iQcIfYjkPKfE4TMvAWMXbH`, `apart-collusion-llm-pilot`.
  - URL: https://modal.com/apps/benjaminharristia/main/ap-iQcIfYjkPKfE4TMvAWMXbH
  - Created 21:52:32 HKT; stopped 21:53:48 HKT on 23 Oct 2026.
  - Exact blocker: `Please add a payment method to use L4 GPU functions.`
- App `ap-GXn15ohe6jmiGGtlhB42Wq`, `apart-gpu-probe`.
  - URL: https://modal.com/apps/benjaminharristia/main/ap-GXn15ohe6jmiGGtlhB42Wq
  - Created 21:55:54 HKT; stopped 21:55:57 HKT.
  - Exact blocker: `Please add a payment method to use T4 GPU functions.`

No successful Modal GPU function/job result exists. No GPU job ID is invented: the above are the actual app/run IDs returned by Modal. Adding a payment method is an account-owner action; no billing details were entered or changed.

## 4. Real CPU inference smoke: infrastructure evidence only

- Model `Qwen/Qwen2.5-1.5B-Instruct`.
- Revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.
- Modal CPU app `ap-shXGxL8y0zXpkYfkTFihZo`.
- URL: https://modal.com/apps/benjaminharristia/main/ap-shXGxL8y0zXpkYfkTFihZo
- CPU float32; torch 2.5.1+cu124; transformers 4.46.3.
- 8 actual model outputs, all 8 accepted by the then-current parser; raw outputs are retained.
- Measured model load: 40.8 s. Total function-body time: 61.9 s. Local remote-call wall time: 67.3 s. Batch generation: 13.2 s (1,646.1 ms/prompt as a batch-average metric, not sequential latency).
- Raw payload: `results/llm-pilot/cpu-smoke-20261023-220318.json`.

CRITICAL: a subsequent audit found the private message said the primary PLAYER NAME where it should have stated the primary ACTION. Therefore this smoke validates model loading, inference and returning actual outputs only. It does not validate seeded-message compliance or provide valid pilot evidence. The old fingerprint did not cover the prompt-building function. Both defects were fixed before any new pilot: messages now state ROCK/PAPER/SCISSORS, and fingerprinting hashes the complete protocol source. The old raw payload remains unchanged.

Other CPU attempts:
- `ap-XNBkUELs98bYtWv5Q4mZUm`: first CPU attempt, stopped 21:59:55 HKT. Return deserialization failed because a torch-specific value reached a client without torch. Return payloads were changed to pure JSON.
- `ap-f63tqvJH0PB1ysUkDs699k`: CPU speed benchmark, created 22:04:00, stopped 22:17:21 HKT. No usable benchmark result or pilot payload returned. This was stopped; no useful performance claim is made from it.

No completed 3 x 30-round per-condition pilot exists, on Modal or locally. The local fallback did not complete a verified model download. The old `cpu-smoke-...-analysis.*` files contain empty pilot statistics because the analyzer did not handle the smoke schema; they must not be cited as pilot results. The raw smoke JSON, not those derivative files, is the evidence.

## 5. Tests and repairs

Final recovery regression execution: 41 tests passed, 0 failures, 0 errors, 0 skips, suite runtime 160.592 s. Exit 0. Executed in the non-iCloud worktree against the repaired code, then exact tested source files were copied into the project with matching SHA256 receipts.

Repairs include:
- Correct seed message: states the actual action, never the player letter.
- Fingerprint covers all protocol source rather than constants only.
- Strict parser requires the whole response to match; embedded JSON is labelled tolerant rather than strict.
- Replaced an invalid permutation test with two explicit invariants: exact-state constants unchanged; missing-state shared-cue dependence is broken in the shuffled reference.
- Corrected the explanation of residual common-cause alarms.
- Restored the importable `llm_protocol.py` name without deleting the renamed file.
- The engine supports both transformers dtype argument spellings and no longer requires accelerate for single-device loading.

Receipt: `results/tests-recovery-final.log`.

## 6. Spending, time and boundedness

Observed Modal billing summary (not an estimate):
- Metered cost: USD 0.25088749.
- Applied credits: USD 0.25000000.
- Network-egress adjustment: USD 0.00088749.
- Billed cost: USD 0.00000000 at retrieval.
- This does NOT verify current remaining credit balance, its expiry, or that a future GPU run is authorised.

The itemised report summed to USD 0.24797854, while the summary showed USD 0.25088749. These are separate live billing views and are retained verbatim; their difference is not silently reconciled. Billing data may be delayed or rounded, but the exact cause of that difference was not verified.

Reported itemised cost by app:
- `ap-XNBkUELs98bYtWv5Q4mZUm`: USD 0.01306616.
- `ap-f63tqvJH0PB1ysUkDs699k`: USD 0.21395118.
- `ap-iQcIfYjkPKfE4TMvAWMXbH`: USD 0.00274462.
- `ap-shXGxL8y0zXpkYfkTFihZo`: USD 0.01821658.

Published list-price estimate ONLY, not spend: an L4 GPU component at USD 0.000222/s would be USD 0.1998 for a full 900-second function timeout, excluding CPU/memory/build/other charges. This is a rough prospective compute envelope, not a measured successful-GPU cost or an account-wide hard budget. No 3 x 30 pilot runtime was established; no justified runtime estimate is reported for that pilot.

Sources checked: https://modal.com/pricing and https://modal.com/docs/guide/gpu . GPU docs explicitly require a valid payment method on file.

## 7. Shutdown verification

A live `modal app list --json` readback found ALL FIVE listed Apart apps stopped with tasks = 0, including the benchmark. Exact app IDs and states saved in `results/modal-apps-shutdown.json`. No endpoint was deployed. No successful Modal GPU allocation exists. Local `nvidia-smi --query-compute-apps` also showed no compute process at recovery inspection. The killed/failed downloads produced no completed usable weight artifact.

Billing receipts: `results/modal-billing.json`, `results/modal-billing-summary.json`.

## Independent review status

The delegated read-only code audit was interrupted and returned no substantive findings. It is not an independent validation or approval. The 41-test result and deterministic replay checks above remain the completed verification; no claim of independent review is made.

## Next actual gate

The completed scripted evidence is usable, subject to stated limitations. The corrected LLM protocol still needs a new smoke and then a small pilot. Modal GPU inference remains blocked until the account owner adds a payment method. Do not claim pilot compliance, detector performance on LLM agents, successful GPU inference, or submission. No further cloud sweep should start just to work around that account gate.
