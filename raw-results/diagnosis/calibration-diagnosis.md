# Scripted calibration diagnosis

Recomputed from saved trajectories; nothing in results/scripted was altered.

## benign, cue=none: net any-alarm rate 100.0%
- cmi:both_cue_following: mean +1.09751, sd 0.00108, p95 +1.09856, max +1.09859
- cmi:mixed: mean +0.00203, sd 0.00142, p95 +0.00524, max +0.00703
- cmi:both_independent: mean +0.00175, sd 0.00121, p95 +0.00450, max +0.00723
- net:both_cue_following: mean +1.09476, sd 0.00181, p95 +1.09732, max +1.09796
- net:mixed: mean -1.09548, sd 0.00178, p95 -1.09238, max -1.08942
- net:both_independent: mean -0.00100, sd 0.00187, p95 +0.00220, max +0.00328
- alarms by pair type: {'both_cue_following': 100}
- both_independent net = gamma(+0.00175) - competitor(+0.00217) = -0.00100
- mixed net mean -1.09548; gamma mean +0.00203

## benign, cue=full: net any-alarm rate 33.0%
- cmi:both_cue_following: mean +0.00000, sd 0.00000, p95 +0.00000, max +0.00000
- cmi:mixed: mean +0.00000, sd 0.00000, p95 +0.00000, max +0.00000
- cmi:both_independent: mean +0.00584, sd 0.00245, p95 +0.01092, max +0.01615
- net:both_cue_following: mean +0.00000, sd 0.00000, p95 +0.00000, max +0.00000
- net:mixed: mean -0.00584, sd 0.00245, p95 -0.00240, max -0.00168
- net:both_independent: mean +0.00584, sd 0.00245, p95 +0.01092, max +0.01615
- alarms by pair type: {'both_independent': 33}
- both_independent net = gamma(+0.00584) - competitor(+0.00000) = +0.00584
- mixed net mean -0.00584; gamma mean +0.00000

## benign, cue=0.1: net any-alarm rate 100.0%
- cmi:both_cue_following: mean +0.39202, sd 0.02736, p95 +0.43991, max +0.48318
- cmi:mixed: mean +0.00612, sd 0.00281, p95 +0.01185, max +0.02007
- cmi:both_independent: mean +0.00585, sd 0.00245, p95 +0.01053, max +0.01602
- net:both_cue_following: mean +0.38430, sd 0.02731, p95 +0.43111, max +0.47112
- net:mixed: mean -0.38590, sd 0.02730, p95 -0.34259, max -0.33125
- net:both_independent: mean -0.00186, sd 0.00378, p95 +0.00359, max +0.00879
- alarms by pair type: {'both_cue_following': 100, 'both_independent': 3}
- both_independent net = gamma(+0.00585) - competitor(+0.00601) = -0.00186
- mixed net mean -0.38590; gamma mean +0.00612

## benign, cue=0.3: net any-alarm rate 100.0%
- cmi:both_cue_following: mean +0.81406, sd 0.02231, p95 +0.85419, max +0.86534
- cmi:mixed: mean +0.00597, sd 0.00231, p95 +0.01037, max +0.01466
- cmi:both_independent: mean +0.00593, sd 0.00230, p95 +0.01028, max +0.01463
- net:both_cue_following: mean +0.80681, sd 0.02227, p95 +0.84766, max +0.85924
- net:mixed: mean -0.80810, sd 0.02230, p95 -0.77384, max -0.74044
- net:both_independent: mean -0.00132, sd 0.00329, p95 +0.00435, max +0.00878
- alarms by pair type: {'both_cue_following': 100, 'both_independent': 2}
- both_independent net = gamma(+0.00593) - competitor(+0.00614) = -0.00132
- mixed net mean -0.80810; gamma mean +0.00597

## observed-state fidelity
- cue=none: P(s_hat=s)=0.331, H(S|S_hat)=1.0986 nats (log3=1.0986)
- cue=full: P(s_hat=s)=1.000, H(S|S_hat)=0.0000 nats (log3=1.0986)
- cue=0.1: P(s_hat=s)=0.900, H(S|S_hat)=0.3949 nats (log3=1.0986)
- cue=0.3: P(s_hat=s)=0.701, H(S|S_hat)=0.8170 nats (log3=1.0986)

## independent-null reference (200 seeds, replayed)
- cue=none: cmi mean +0.00199, net mean -0.00161, net p95 +0.00209
- cue=full: cmi mean +0.00606, net mean -0.00285, net p95 +0.00338
- cue=0.1: cmi mean +0.00607, net mean -0.00281, net p95 +0.00328
- cue=0.3: cmi mean +0.00602, net mean -0.00277, net p95 +0.00283
