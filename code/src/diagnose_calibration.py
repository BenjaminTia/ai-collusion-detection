"""Diagnose the scripted calibration-transfer failure. Read-only on old artifacts.

Recomputes per-pair scores from results/scripted/trajectories.jsonl and from a
fresh replay of the independent-null calibration seeds, then decomposes the
net-influence score to locate the source of the benign full-cue false alarms.

Writes results/diagnosis/calibration-diagnosis.json and .md. Never modifies
results/scripted/. Stdlib only.
"""
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from experiment import PAIRS, cmi, scores, simulate, observed, quantile_higher  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TRAJ = ROOT / 'results' / 'scripted' / 'trajectories.jsonl'
META = ROOT / 'results' / 'scripted' / 'metadata.json'
OUT = ROOT / 'results' / 'diagnosis'
MODES = ('none', 'full', '0.1', '0.3')


def load_runs(condition=None, limit=None):
    runs = []
    with TRAJ.open(encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            if condition and rec['condition'] != condition:
                continue
            runs.append(rec)
            if limit and len(runs) >= limit:
                break
    return runs


def pair_type(pair, assigned):
    """benign condition: assigned_candidate is exactly the cue-following pair."""
    if assigned is None:
        return 'no_assigned'
    a, b = pair
    na = a in assigned
    nb = b in assigned
    if na and nb:
        return 'both_cue_following'
    if na or nb:
        return 'mixed'
    return 'both_independent'


def describe(values):
    v = sorted(values)
    return {'n': len(v), 'mean': statistics.fmean(v), 'sd': statistics.pstdev(v),
            'p05': quantile_higher(v, 0.05), 'p50': quantile_higher(v, 0.50),
            'p95': quantile_higher(v, 0.95), 'max': v[-1], 'min': v[0]}


def net_decomposition(actions, states):
    """Recompute net with the competitor terms kept visible."""
    cols = list(zip(*actions))
    g = {p: cmi(cols[p[0]], cols[p[1]], states) for p in PAIRS}
    out = {}
    for i, j in PAIRS:
        comp_j = max(g[tuple(sorted((k, j)))] for k in range(4) if k not in (i, j))
        comp_i = max(g[tuple(sorted((k, i)))] for k in range(4) if k not in (i, j))
        ij = g[i, j] - comp_j
        ji = g[i, j] - comp_i
        out[i, j] = {'gamma': g[i, j], 'competitor_for_j': comp_j,
                     'competitor_for_i': comp_i, 'dir_ij': ij, 'dir_ji': ji,
                     'net': min(ij, ji)}
    return g, out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    thresholds = json.loads(META.read_text(encoding='utf-8'))['thresholds']
    report = {'data_type': 'diagnosis of SCRIPTED SIMULATION results; not LLM evidence',
              'source_trajectories': str(TRAJ),
              'thresholds': thresholds, 'sections': {}}

    # ---- 1. benign, full cue: which pairs alarm and why -------------------
    benign = load_runs('benign')
    full = {}
    for mode in MODES:
        rows = defaultdict(list)          # pair_type -> scores
        alarms = Counter()                # pair_type -> alarm count
        alarm_pair_index = Counter()
        decomp_rows = defaultdict(list)
        per_run_alarm = 0
        for run in benign:
            states = observed(run, mode)
            g, decomp = net_decomposition(run['actions'], states)
            thr_net = thresholds[str((mode, 'net'))]
            thr_cmi = thresholds[str((mode, 'cmi'))]
            hit_net = [(p, v['net']) for p, v in decomp.items() if v['net'] > thr_net]
            per_run_alarm += bool(hit_net)
            for p, v in decomp.items():
                t = pair_type(p, run['assigned_candidate'])
                rows['net:' + t].append(v['net'])
                rows['cmi:' + t].append(v['gamma'])
                decomp_rows[t].append(v)
                if v['net'] > thr_net:
                    alarms['net:' + t] += 1
                if v['gamma'] > thr_cmi:
                    alarms['cmi:' + t] += 1
            for p, _ in hit_net:
                alarm_pair_index[pair_type(p, run['assigned_candidate'])] += 1
        full[mode] = {
            'benign_runs': len(benign),
            'runs_with_any_net_alarm': per_run_alarm,
            'net_fpr': per_run_alarm / len(benign),
            'score_distributions': {k: describe(v) for k, v in rows.items()},
            'alarm_pair_counts': dict(alarms),
            'alarm_pair_types': dict(alarm_pair_index),
            'net_decomposition_by_type': {
                t: {k: describe([r[k] for r in v]) for k in
                    ('gamma', 'competitor_for_j', 'competitor_for_i', 'dir_ij', 'dir_ji', 'net')}
                for t, v in decomp_rows.items()},
        }

    # ---- 2. independent-null reference, same decomposition ----------------
    null = {}
    for mode in MODES:
        rows = defaultdict(list)
        for seed in range(200):
            run = simulate('independent', 1000, 1000000 + seed)
            states = observed(run, mode)
            g, decomp = net_decomposition(run['actions'], states)
            for p, v in decomp.items():
                rows['net:all_independent'].append(v['net'])
                rows['cmi:all_independent'].append(v['gamma'])
        null[mode] = {'score_distributions': {k: describe(v) for k, v in rows.items()}}
    report['sections']['benign_by_mode'] = full
    report['sections']['independent_null_replay'] = null

    # ---- 3. observed-state fidelity and the irreducible CMI floor ---------
    fidelity = {}
    for mode in MODES:
        acc, mis = [], []
        for run in benign[:100]:
            states = observed(run, mode)
            for s, shat in zip(run['cue'], states):
                acc.append(s == shat)
        agree = sum(acc) / len(acc)
        # H(S|S_hat) in nats, computed from the empirical joint of (S, S_hat)
        joint = Counter()
        for run in benign:
            for s, shat in zip(run['cue'], observed(run, mode)):
                joint[s, shat] += 1
        n = sum(joint.values())
        ns, nsh = Counter(), Counter()
        for (s, shat), c in joint.items():
            ns[s] += c
            nsh[shat] += c
        h_cond = sum(c / n * math.log(nsh[shat] / c) for (s, shat), c in joint.items())
        fidelity[mode] = {
            'P_observed_state_equals_true_state': agree,
            'H_S_given_observed_state_nats': h_cond,
            'log3_nats': math.log(3),
            'note': 'benign pair shares the same draw s, so its conditional CMI is exactly H(S|S_hat) '
                    'whatever the estimator; the residual is the unobserved-common-cause floor',
        }
    report['sections']['observed_state_fidelity'] = fidelity

    path = OUT / 'calibration-diagnosis.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    # ---- 4. human-readable summary ---------------------------------------
    lines = ['# Scripted calibration diagnosis', '',
             'Recomputed from saved trajectories; nothing in results/scripted was altered.', '']
    for mode in MODES:
        s = full[mode]
        lines.append(f'## benign, cue={mode}: net any-alarm rate {s["net_fpr"]:.1%}')
        for k in ('cmi:both_cue_following', 'cmi:mixed', 'cmi:both_independent',
                  'net:both_cue_following', 'net:mixed', 'net:both_independent'):
            if k in s['score_distributions']:
                d = s['score_distributions'][k]
                lines.append(f'- {k}: mean {d["mean"]:+.5f}, sd {d["sd"]:.5f}, '
                             f'p95 {d["p95"]:+.5f}, max {d["max"]:+.5f}')
        lines.append(f'- alarms by pair type: {s["alarm_pair_types"]}')
        d = s['net_decomposition_by_type']
        if 'both_independent' in d:
            b = d['both_independent']
            lines.append(f'- both_independent net = gamma({b["gamma"]["mean"]:+.5f}) '
                         f'- competitor({b["competitor_for_j"]["mean"]:+.5f}) '
                         f'= {b["net"]["mean"]:+.5f}')
        if 'mixed' in d:
            b = d['mixed']
            lines.append(f'- mixed net mean {b["net"]["mean"]:+.5f}; '
                         f'gamma mean {b["gamma"]["mean"]:+.5f}')
        lines.append('')
    lines.append('## observed-state fidelity')
    for mode, f in fidelity.items():
        lines.append(f'- cue={mode}: P(s_hat=s)={f["P_observed_state_equals_true_state"]:.3f}, '
                     f'H(S|S_hat)={f["H_S_given_observed_state_nats"]:.4f} nats '
                     f'(log3={f["log3_nats"]:.4f})')
    lines.append('')
    lines.append('## independent-null reference (200 seeds, replayed)')
    for mode in MODES:
        d = null[mode]['score_distributions']
        lines.append(f'- cue={mode}: cmi mean {d["cmi:all_independent"]["mean"]:+.5f}, '
                     f'net mean {d["net:all_independent"]["mean"]:+.5f}, '
                     f'net p95 {d["net:all_independent"]["p95"]:+.5f}')
    lines.append('')
    (OUT / 'calibration-diagnosis.md').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))
    print('\nwrote', path)


if __name__ == '__main__':
    main()
