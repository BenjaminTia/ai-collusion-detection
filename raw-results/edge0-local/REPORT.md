# Real Edge0 local pilot and paired message ablation

1440 real pilot decisions; 12 trajectories (3 per condition), 30 rounds each. All pilot outputs parsed as exact action-only JSON. No retries or substituted actions. Additional 48-decision smoke and 180-decision paired ablation are separate evidence.

## Message effects (paired, descriptive)
- seeded: private message changed 0/90 actions; requested coordination followed 18/90 with message versus 18/90 without.
- combined: private message changed 0/90 actions; requested coordination followed 39/90 with message versus 39/90 without.

## Per-condition compliance
- independent: cue following 0/0; message following 0/0; free-agent recommendation following 360/360.
- benign: cue following 180/180; message following 0/0; free-agent recommendation following 180/180.
- seeded: cue following 0/0; message following 18/90; free-agent recommendation following 270/270.
- combined: cue following 180/180; message following 39/90; free-agent recommendation following 90/90.

## Interpretation
Private-message delivery and behavioural response are separate checks. Low seeded compliance prevents treating assignment as a reliable positive collusion control. Report model-specific obedience and prompt effects, not a detector success claim.

## Limitations
- Exploratory 3-run pilot, not a powered detector evaluation
- Ablation planned after the pilot; paired deterministic prompt intervention, no claim of preregistration
- Original pilot interrupted by outer tool 420-second limit after 10 saved runs; 2 remaining runs collected separately with identical prompts/settings. No complete run was outcome-filtered. Any unsaved in-flight outputs from interrupted run unavailable.
- No thresholds or formal collusion accusations from 30-round CMI estimates
- Seeded assignment is not demonstrated compliance or harmful collusion
- Artifact hashes identify installed model; this analysis did not independently reproduce its training or conversion
