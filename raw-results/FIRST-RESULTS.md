# Scripted feasibility results

NOT LLM experiments. No evidence of spontaneous collusion. No novelty claim.

100 evaluation runs per condition, 1000 rounds each. Same trajectories reused across observation views and detectors. Independent scripted-null calibration: 200 runs per view.

## Important diagnostic
The independent-null threshold transfers poorly to structured benign policies, especially for net influence. This is a calibration limitation, NOT proof that conditioning has failed or that innocent agents colluded. Preserve and investigate it; do not tune it away using the test set.

- benign, cue=none, cmi: false-positive rate 100.0%.
- benign, cue=none, net: false-positive rate 100.0%.
- benign, cue=full, cmi: false-positive rate 1.0%.
- benign, cue=full, net: false-positive rate 33.0%.
- benign, cue=0.1, cmi: false-positive rate 100.0%.
- benign, cue=0.1, net: false-positive rate 100.0%.
- benign, cue=0.3, cmi: false-positive rate 100.0%.
- benign, cue=0.3, net: false-positive rate 100.0%.
- combined, cue=none, cmi: top-1 assigned-pair identification 0.0%.
- combined, cue=none, net: top-1 assigned-pair identification 0.0%.
- combined, cue=full, cmi: top-1 assigned-pair identification 100.0%.
- combined, cue=full, net: top-1 assigned-pair identification 100.0%.
- combined, cue=0.1, cmi: top-1 assigned-pair identification 100.0%.
- combined, cue=0.1, net: top-1 assigned-pair identification 100.0%.
- combined, cue=0.3, cmi: top-1 assigned-pair identification 0.0%.
- combined, cue=0.3, net: top-1 assigned-pair identification 0.0%.

## Notable outcomes
- Full cue removes the idealised public-only pair dependence analytically (unit test), but finite-sample net scores can still produce false alarms on other pairs.
- Combined condition: 30% corrupted cue makes both methods choose the wrong pair in all 100 scripted runs; full cue identifies the assigned pair in all 100.
- These toy endpoints are deliberately high-signal. Test robustness and meaningful LLM departures before arguing a substantive empirical contribution.
- Raw trajectory logs, per-run results, thresholds and summary tables are saved. No test-set exclusions.
