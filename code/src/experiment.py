"""Independent scripted observability experiment. Stdlib only. No LLM results.
R=0, P=1, S=2; (a-b)%3 == 1 means a beats b.
Statistics are common-auditor-state CMI screens, not the general partial-state
influence formula. Private communication is a hidden precommit stage.
"""
import argparse
import csv
import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

PAIRS = list(itertools.combinations(range(4), 2))
CONDITIONS = ('independent', 'benign', 'seeded', 'combined')


def cmi(x, y, states):
    if not (len(x) == len(y) == len(states)) or not x:
        raise ValueError('Nonempty aligned observations required')
    joint, xs, ys, ns = Counter(), Counter(), Counter(), Counter()
    for a, b, s in zip(x, y, states):
        joint[s, a, b] += 1
        xs[s, a] += 1
        ys[s, b] += 1
        ns[s] += 1
    return sum(n / len(x) * math.log(n * ns[s] / (xs[s, a] * ys[s, b]))
               for (s, a, b), n in joint.items())


def scores(actions, states):
    columns = list(zip(*actions))
    g = {pair: cmi(columns[pair[0]], columns[pair[1]], states) for pair in PAIRS}
    def influence(i, j):
        return g[tuple(sorted((i, j)))]
    net = {}
    for i, j in PAIRS:
        ij = influence(i, j) - max(influence(k, j) for k in range(4) if k not in (i, j))
        ji = influence(i, j) - max(influence(k, i) for k in range(4) if k not in (i, j))
        net[i, j] = min(ij, ji)
    return g, net


def payoff(actions):
    kinds = set(actions)
    if len(kinds) == 1:
        return [0] * len(actions)
    if len(kinds) == 3:
        return [1] * len(actions)
    a, b = sorted(kinds)
    winner = a if (a - b) % 3 == 1 else b
    return [int(x == winner) for x in actions]


def simulate(condition, rounds, seed, strength=0.8):
    if condition not in CONDITIONS:
        raise ValueError(condition)
    rng = random.Random(seed)
    # Separate RNG: observation corruption must not alter generated actions.
    obs_rng = random.Random(seed + 100000000)
    pair = tuple(sorted(rng.sample(range(4), 2)))
    others = tuple(i for i in range(4) if i not in pair)
    acts, cue, uniforms = [], [], []
    attempted = compliant = 0
    for _ in range(rounds):
        s = rng.randrange(3)
        a = [rng.randrange(3) for _ in range(4)]
        benign_pair = pair if condition == 'benign' else others
        if condition in ('benign', 'combined'):
            for i in benign_pair:
                a[i] = s
        if condition in ('seeded', 'combined'):
            attempted += 1
            if rng.random() < strength:
                a[pair[1]] = (a[pair[0]] - 1) % 3
            compliant += int(a[pair[1]] == (a[pair[0]] - 1) % 3)
        acts.append(a)
        cue.append(s)
        uniforms.append((obs_rng.random(), obs_rng.randrange(2)))
    return {'actions': acts, 'cue': cue, 'observation_noise': uniforms,
            'pair': pair if condition in ('seeded', 'combined') else None,
            'assigned_candidate': pair, 'compliance': compliant / attempted if attempted else None}


def observed(run, mode):
    if mode == 'none':
        return [0] * len(run['cue'])
    if mode == 'full':
        return run['cue']
    error = float(mode)
    return [(s + 1 + alternative) % 3 if u < error else s
            for s, (u, alternative) in zip(run['cue'], run['observation_noise'])]


def quantile_higher(values, q):
    v = sorted(values)
    return v[min(len(v)-1, math.ceil(q * (len(v)-1)))]


def rank_stats(values, truth):
    # Fractional credit for ties, never arbitrary pair-index advantage.
    best = max(values.values())
    winners = [p for p, v in values.items() if abs(v-best) < 1e-12]
    top = 1 / len(winners) if truth in winners else 0.0
    auc = sum((values[truth] > v + 1e-12) + 0.5 * (abs(values[truth]-v) < 1e-12)
              for p, v in values.items() if p != truth) / 5
    return top, auc


def run_grid(out, runs=100, rounds=1000, calibration=200):
    out.mkdir(parents=True, exist_ok=True)
    modes = ('none', 'full', '0.1', '0.3')
    thresholds = {}
    # Freeze/calibrate using independent null runs only. Every observation mode
    # gets its own null; values are maxima over all six pairs within each run.
    for mode in modes:
        maxima = defaultdict(list)
        for seed in range(calibration):
            run = simulate('independent', rounds, 1000000 + seed)
            mi, net = scores(run['actions'], observed(run, mode))
            maxima['cmi'].append(max(mi.values()))
            maxima['net'].append(max(net.values()))
        for method, values in maxima.items():
            thresholds[mode, method] = max(0.0, quantile_higher(values, 0.95))
    records = []
    trajectory_file = (out/'trajectories.jsonl').open('w',encoding='utf-8')
    for condition in CONDITIONS:
        for seed in range(runs):
            run = simulate(condition, rounds, seed + 2000000)
            trajectory_file.write(json.dumps({'condition':condition,'seed_index':seed,**run})+'\n')
            for mode in modes:
                mi, net = scores(run['actions'], observed(run, mode))
                rewards = [payoff(a) for a in run['actions']]
                means = [sum(r[i] for r in rewards)/rounds for i in range(4)]
                for method, values in [('cmi', mi), ('net', net)]:
                    threshold = thresholds[mode, method]
                    qualifying = [p for p,v in values.items() if v > threshold]
                    top, auc = rank_stats(values, run['pair']) if run['pair'] else (None,None)
                    rec = {'condition': condition, 'seed': seed, 'rounds': rounds,
                           'observed_context': mode, 'method': method,
                           'threshold': threshold, 'max_score': max(values.values()),
                           'any_alarm': bool(qualifying), 'unique_alarm': len(qualifying)==1,
                           'correct_unique_alarm': qualifying == [run['pair']] if run['pair'] else None,
                           'top1_credit': top, 'pair_auc': auc, 'compliance': run['compliance'],
                           'primary_payoff': means[run['assigned_candidate'][0]],
                           'assistant_payoff': means[run['assigned_candidate'][1]],
                           'outsider_payoff': sum(means[i] for i in range(4) if i not in run['assigned_candidate'])/2,
                           'mean_action_entropy': sum(-sum(n/rounds*math.log(n/rounds) for n in Counter(col).values()) for col in zip(*run['actions']))/4}
                    records.append(rec)
    trajectory_file.close()
    with (out/'runs.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    summary=[]
    for condition,mode,method in itertools.product(CONDITIONS,modes,('cmi','net')):
        rows=[r for r in records if (r['condition'],r['observed_context'],r['method'])==(condition,mode,method)]
        s={'condition':condition,'observed_context':mode,'method':method,'runs':len(rows)}
        for key in ['any_alarm','unique_alarm','correct_unique_alarm','top1_credit','pair_auc','compliance','primary_payoff','assistant_payoff','outsider_payoff','mean_action_entropy']:
            vals=[r[key] for r in rows if r[key] is not None]
            s[key]=sum(vals)/len(vals) if vals else None
        summary.append(s)
    with (out/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    meta={'data_type':'SCRIPTED SIMULATION ONLY; not LLM evidence',
          'runs_per_cell':runs,'rounds':rounds,'calibration_runs':calibration,
          'calibration_seeds':'1000000+index','evaluation_seeds':'2000000+index',
          'threshold_rule':'95th percentile (higher) of independent-null maximum across pairs; strict >',
          'thresholds':{str(k):v for k,v in thresholds.items()}}
    (out/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    for s in summary:
        if s['condition'] in ('benign','combined'):
            print(s['condition'],s['observed_context'],s['method'],
                  'any_alarm=',round(s['any_alarm'],3),'top1=',s['top1_credit'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('results/scripted'))
    p.add_argument('--runs',type=int,default=100);p.add_argument('--rounds',type=int,default=1000)
    p.add_argument('--calibration',type=int,default=200);a=p.parse_args()
    run_grid(a.out,a.runs,a.rounds,a.calibration)
