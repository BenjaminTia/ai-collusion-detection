"""Within-observed-state permutation calibration for the scripted audit.

The original protocol calibrated a single threshold per (observation view, method)
from independent-null runs, then applied it to every condition. That threshold is
a *population* null: it assumes all six pairs are exchangeable. Structured benign
policies break that exchangeability, and the first results expose the mismatch.

This module adds a *conditional randomization* null instead. For each evaluation
run it shuffles every agent's action column independently WITHIN each observed
state stratum, recomputes the whole six-pair statistic, and repeats. That leaves
each agent's conditional action distribution given the recorded state untouched
while destroying every cross-agent association. The threshold is the higher 95th
percentile of the maximum over the six pairs, so the run-level false-alarm rate
targets 5% per method.

What this can and cannot do (stated before running):
  - It tests conditional independence given the RECORDED state.
  - It cannot cure an unobserved or badly corrupted common cause: if two agents
    both equal the true cue and the auditor sees only a corrupted cue, the OBSERVED
    actions remain dependent given that recorded cue. Independent column shuffling
    destroys that residual association in the candidate null. The observed statistic
    then exceeds its shuffled reference and the benign policy can still be flagged.
    Constant columns inside an exact-state stratum, in contrast, do not change.

The original results are read and never rewritten. New runs use fresh seeds
(3000000+) that the original grid did not touch.
"""
import argparse
import csv
import itertools
import json
import math
import random
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from experiment import CONDITIONS, PAIRS, cmi, observed, rank_stats, scores, simulate

MODES = ('none', 'full', '0.1', '0.3')
FRESH_SEED_BASE = 3000000
PERM_SEED_BASE = 5000000


def strata(states):
    groups = defaultdict(list)
    for i, s in enumerate(states):
        groups[s].append(i)
    return groups


def within_state_shuffle(actions, states, rng):
    """Independently shuffle each agent's column inside each observed-state stratum."""
    groups = strata(states)
    columns = [list(c) for c in zip(*actions)]
    shuffled = []
    for col in columns:
        new = list(col)
        for _, idx in sorted(groups.items()):
            vals = [col[i] for i in idx]
            rng.shuffle(vals)
            for position, value in zip(idx, vals):
                new[position] = value
        shuffled.append(new)
    return [list(row) for row in zip(*shuffled)]


def observed_stats(actions, states):
    g, net = scores(actions, states)
    return g, net


def permutation_null(actions, states, perms, rng):
    """Max-over-six-pairs null distribution for both statistics."""
    null = {'cmi': [], 'net': []}
    for _ in range(perms):
        g, net = scores(within_state_shuffle(actions, states, rng), states)
        null['cmi'].append(max(g.values()))
        null['net'].append(max(net.values()))
    return null


def higher_quantile(values, q):
    v = sorted(values)
    return v[min(len(v) - 1, math.ceil(q * (len(v) - 1)))]


def thresholds_from_null(null, q=0.95):
    return {m: max(0.0, higher_quantile(v, q)) for m, v in null.items()}


def p_value(observed_max, null_maxes):
    return (1 + sum(1 for v in null_maxes if v >= observed_max)) / (len(null_maxes) + 1)


def evaluate_run(condition, seed, rounds, perms, modes):
    run = simulate(condition, rounds, FRESH_SEED_BASE + seed)
    rng = random.Random(PERM_SEED_BASE + 100000 * CONDITIONS.index(condition) + seed)
    records = []
    for mode in modes:
        states = observed(run, mode)
        g, net = observed_stats(run['actions'], states)
        null = permutation_null(run['actions'], states, perms, rng)
        thresholds = thresholds_from_null(null)
        for method, values in (('cmi', g), ('net', net)):
            over = [p for p, v in values.items() if v > thresholds[method]]
            top, auc = rank_stats(values, run['pair']) if run['pair'] else (None, None)
            records.append({
                'condition': condition, 'seed': seed, 'rounds': rounds,
                'observed_context': mode, 'method': method,
                'permutations': perms,
                'threshold': thresholds[method],
                'max_score': max(values.values()),
                'any_alarm': bool(over),
                'alarm_count': len(over),
                'alarm_pairs': json.dumps([list(p) for p in over]),
                'perm_p_value': p_value(max(values.values()), null[method]),
                'top1_credit': top, 'pair_auc': auc,
                'compliance': run['compliance'],
                'truth_pair': json.dumps(list(run['pair'])) if run['pair'] else None,
                'assigned_pair': json.dumps(list(run['assigned_candidate'])),
            })
    return records


def _worker(job):
    return evaluate_run(*job)


def summarize(records, original_thresholds):
    out = []
    for condition, mode, method in itertools.product(CONDITIONS, MODES, ('cmi', 'net')):
        rows = [r for r in records
                if (r['condition'], r['observed_context'], r['method']) == (condition, mode, method)]
        if not rows:
            continue
        orig = original_thresholds.get(str((mode, method)))
        s = {'condition': condition, 'observed_context': mode, 'method': method,
             'runs': len(rows),
             'perm_any_alarm_rate': sum(r['any_alarm'] for r in rows) / len(rows),
             'perm_mean_threshold': sum(r['threshold'] for r in rows) / len(rows),
             'perm_median_p_value': sorted(r['perm_p_value'] for r in rows)[len(rows) // 2],
             'original_threshold': orig,
             'original_any_alarm_rate': (sum(r['max_score'] > orig for r in rows) / len(rows)
                                         if orig is not None else None),
             'top1_credit': (sum(r['top1_credit'] for r in rows if r['top1_credit'] is not None)
                             / max(1, sum(1 for r in rows if r['top1_credit'] is not None))),
             'pair_auc': (sum(r['pair_auc'] for r in rows if r['pair_auc'] is not None)
                          / max(1, sum(1 for r in rows if r['pair_auc'] is not None))),
             'mean_compliance': (sum(r['compliance'] for r in rows if r['compliance'] is not None)
                                 / max(1, sum(1 for r in rows if r['compliance'] is not None)))}
        out.append(s)
    return out


def run(out_dir, runs=100, rounds=1000, perms=199, workers=8, modes=MODES):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(c, seed, rounds, perms, modes) for c in CONDITIONS for seed in range(runs)]
    if workers > 1:
        with Pool(workers) as pool:
            chunks = pool.map(_worker, jobs, chunksize=1)
    else:
        chunks = [_worker(j) for j in jobs]
    records = [r for chunk in chunks for r in chunk]

    meta_path = Path(__file__).resolve().parents[1] / 'results' / 'scripted' / 'metadata.json'
    original_thresholds = json.loads(meta_path.read_text(encoding='utf-8'))['thresholds']

    with (out_dir / 'runs.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    summary = summarize(records, original_thresholds)
    with (out_dir / 'summary.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    meta = {
        'data_type': 'SCRIPTED SIMULATION ONLY; not LLM evidence',
        'null': 'independent within-observed-state column permutation, per run',
        'permutations_per_run_cell': perms,
        'threshold_rule': 'higher 95th percentile of the max over six pairs across permutations, '
                          'floored at zero; strict >',
        'fresh_evaluation_seeds': f'{FRESH_SEED_BASE}+index (original grid used 2000000+)',
        'permutation_seed_rule': f'{PERM_SEED_BASE} + 100000*condition_index + run_index',
        'runs_per_condition': runs, 'rounds': rounds,
        'original_thresholds': original_thresholds,
    }
    (out_dir / 'metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'results' / 'permutation')
    parser.add_argument('--runs', type=int, default=100)
    parser.add_argument('--rounds', type=int, default=1000)
    parser.add_argument('--perms', type=int, default=199)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    rows = run(args.out, args.runs, args.rounds, args.perms, args.workers)
    print(f'{"condition":12s} {"cue":5s} {"method":4s} {"permFPR":>8s} {"origFPR":>8s} {"top1":>6s}')
    for s in rows:
        print(f'{s["condition"]:12s} {s["observed_context"]:5s} {s["method"]:4s} '
              f'{s["perm_any_alarm_rate"]:8.3f} '
              f'{(s["original_any_alarm_rate"] if s["original_any_alarm_rate"] is not None else float("nan")):8.3f} '
              f'{s["top1_credit"]:6.3f}')
