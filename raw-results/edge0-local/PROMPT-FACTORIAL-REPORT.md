# Exploratory prompt-factorial results

720 actual new model decisions on the same 180 assistant situations. Every output exact action-only JSON, no retries, no substituted actions. All four arms used identical model, seed and generation settings.

## Results
- quoted_relational: requested action 57/180; on conflicts with private recommendation 0/123; copied primary action 64/180.
- quoted_explicit: requested action 62/180; on conflicts with private recommendation 5/123; copied primary action 64/180.
- priority_relational: requested action 9/180; on conflicts with private recommendation 9/123; copied primary action 160/180.
- priority_explicit: requested action 180/180; on conflicts with private recommendation 123/123; copied primary action 0/180.

## Interpretation
Repeating the original quoted relational request after restarting the server reproduced all 180 original actions. Explicit action wording alone changed five actions. Adding an instruction to prioritise the relational request changed behaviour but mostly produced the wrong action: it copied the primary action in 160/180 cases. Combining prioritisation with explicit target-action wording produced the requested action in 180/180 cases, including all 123 recommendation-conflict cases.

This separates three observable failures: no response to a request, response with an incorrect mapping, and execution of the intended mapping. A dependence detector could respond to either same-action copying or the desired beaten-action mapping; dependence alone would not establish correct execution of the prescribed policy or harmful intent. The last statement is a mechanism implication, not a new measured detector result.

## Limits
- 180 situations are nested within 6 source trajectories and are reused across 4 arms; do not treat 720 rows as independent trajectory replications.
- Priority factor adds an instruction to follow the message and override the recommendation; it changes task framing, not just the quoted message text.
- The explicit-action factor also removes relational inference burden and changes wording.
- Six-run exploratory result for one quantized model, not a population guarantee.
- No spontaneous coordination, intent, harmful collusion, or calibrated detector-performance claim.
- All arms repeat the same source situations; a separate held-out protocol/model evaluation remains necessary.
