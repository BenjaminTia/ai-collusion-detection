"""Analyse a saved LLM pilot payload. Reads raw records only; invents nothing.

    python src/analyze_llm_pilot.py results/llm-pilot/cpu-pilot-XXXX.json

Writes <input>-analysis.json and <input>-analysis.md next to the input.
Scope note enforced in the output: the pilot is 3 runs x 30 rounds per condition.
Compliance and output-validity numbers are meaningful at this size; the CMI/net
numbers are descriptive only and no threshold claim is made from them.
"""
import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from experiment import scores, rank_stats  # noqa: E402

PAIR_ACTIONS = ('R', 'P', 'S')


def beat(action):
    return PAIR_ACTIONS[(PAIR_ACTIONS.index(action) - 1) % 3]


def entropy(counter, n):
    return -sum(c / n * math.log(c / n) for c in counter.values() if c)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def analyse(payload, cpu_rate=0.0000131, mem_rate=0.00000222, cores=16, mem_gb=32):
    records = payload.get('records', [])
    rounds = payload.get('rounds', [])
    out = {'source_stage': payload.get('stage'),
           'compute': payload.get('compute'),
           'model': payload.get('model'),
           'prompt_fingerprint': payload.get('frozen', {}).get('prompt_fingerprint'),
           'truncated': payload.get('truncated'),
           'n_runs_declared': len(payload.get('runs', [])),
           'n_rounds': len(rounds),
           'n_decisions': len(records)}

    # ---- output validity -------------------------------------------------
    parses = Counter(r['parse'] for r in records)
    retried = [r for r in records if r['retried']]
    fallbacks = [r for r in records if r['fallback']]
    out['validity'] = {
        'parse_counts': dict(parses),
        'strict_rate': parses.get('strict', 0) / len(records) if records else None,
        'retried': len(retried),
        'fallbacks': len(fallbacks),
        'fallback_rate': len(fallbacks) / len(records) if records else None,
        'mean_new_tokens': statistics.fmean([r['new_tokens'] for r in records]) if records else None,
        'mean_prompt_tokens': statistics.fmean([r['prompt_tokens'] for r in records]) if records else None,
        'mean_latency_ms_per_prompt': statistics.fmean([r['latency_ms'] for r in records]) if records else None,
        'invalid_raw_outputs': [r['raw_output'] for r in records if r['parse'] in
                                ('unparsed', 'fallback_to_recommendation')][:10],
    }

    # ---- action behaviour ------------------------------------------------
    by_role = defaultdict(Counter)
    for r in records:
        by_role[r['role']][r['action']] += 1
    out['actions_by_role'] = {role: {'counts': dict(c),
                                     'entropy': entropy(c, sum(c.values()))}
                              for role, c in by_role.items()}
    per_condition = {}
    for condition in sorted({r['condition'] for r in records}):
        subset = [r for r in records if r['condition'] == condition]
        counts = Counter(r['action'] for r in subset)
        per_condition[condition] = {'counts': dict(counts),
                                    'share': {a: counts.get(a, 0) / len(subset) for a in PAIR_ACTIONS},
                                    'entropy': entropy(counts, len(subset))}
    out['actions_by_condition'] = per_condition

    # ---- compliance ------------------------------------------------------
    seeded = [r for r in records if r['role'] == 'assistant']
    primary_by_key = {(r['condition'], r['run_index'], r['round']): r['action']
                      for r in records if r['role'] == 'primary'}
    followed = 0
    seed_rows = []
    for r in seeded:
        key = (r['condition'], r['run_index'], r['round'])
        pa = primary_by_key.get(key)
        ok = pa is not None and r['action'] == beat(pa)
        followed += ok
        seed_rows.append({'condition': r['condition'], 'run_index': r['run_index'],
                          'round': r['round'], 'primary': pa, 'assistant': r['action'],
                          'followed': ok})
    followers = [r for r in records if r['role'] == 'cue_follower']
    cue_ok = sum(r['action'] == r['cue'] for r in followers)
    independent = [r for r in records if r['role'] in ('independent', 'primary')]
    rec_ok = sum(r['action'] == r['recommendation'] for r in independent)
    out['compliance'] = {
        'seed_message_followed': {'n': len(seeded), 'followed': followed,
                                  'rate': followed / len(seeded) if seeded else None},
        'seed_by_condition': {
            c: {'n': sum(1 for r in seed_rows if r['condition'] == c),
                'followed': sum(1 for r in seed_rows if r['condition'] == c and r['followed'])}
            for c in sorted({r['condition'] for r in seed_rows})},
        'cue_followed': {'n': len(followers), 'followed': cue_ok,
                         'rate': cue_ok / len(followers) if followers else None},
        'recommendation_followed_free_agents': {
            'n': len(independent), 'followed': rec_ok,
            'rate': rec_ok / len(independent) if independent else None,
            'note': 'independent agents and seeded primaries see their recommendation'},
    }

    # ---- payoffs ---------------------------------------------------------
    payoff_rows = []
    for rd in rounds:
        for i, p in enumerate(rd['payoffs']):
            payoff_rows.append({'condition': rd['condition'], 'player': i, 'payoff': p})
    payoffs = defaultdict(list)
    for r in payoff_rows:
        payoffs[r['condition']].append(r['payoff'])
    out['mean_payoff'] = {c: statistics.fmean(v) for c, v in payoffs.items()}

    # ---- descriptive influence statistics --------------------------------
    runs = defaultdict(dict)
    for rd in rounds:
        runs[(rd['condition'], rd['run_index'])][rd['round']] = rd
    influence = []
    for (condition, run_index), rows in sorted(runs.items()):
        ordered = [rows[k] for k in sorted(rows)]
        actions = [[PAIR_ACTIONS.index(a) for a in rd['actions']] for rd in ordered]
        states = [PAIR_ACTIONS.index(rd['cue']) for rd in ordered]
        g, net = scores(actions, states)
        truth = tuple(ordered[0]['pair']) if condition in ('seeded', 'combined') else None
        entry = {'condition': condition, 'run_index': run_index, 'rounds': len(ordered),
                 'max_cmi': max(g.values()), 'max_net': max(net.values()),
                 'top_pair_cmi': max(g, key=g.get), 'top_pair_net': max(net, key=net.get),
                 'truth_pair': truth}
        if truth:
            top, auc = rank_stats(g, truth), rank_stats(net, truth)
            entry['cmi_top1'], entry['cmi_auc'] = top[0], top[1]
            entry['net_top1'], entry['net_auc'] = auc[0], auc[1]
        influence.append(entry)
    out['influence_descriptive'] = {
        'note': ('30 rounds per run, 3 runs per condition. CMI/net are reported for pipeline '
                 'sanity only: no threshold, no p-value, no inference at this sample size.'),
        'per_run': influence}

    # ---- cost estimate ---------------------------------------------------
    timing = payload.get('timing', {})
    seconds = timing.get('total_seconds') or 0
    physical_cores = cores / 2
    cpu_cost = seconds * physical_cores * cpu_rate
    mem_cost = seconds * mem_gb * mem_rate
    out['cost_estimate'] = {
        'label': 'ESTIMATE from published Modal rates x measured container seconds; not an invoice',
        'container_seconds': seconds,
        'assumed_physical_cores': physical_cores,
        'cpu_usd': round(cpu_cost, 4),
        'memory_usd': round(mem_cost, 4),
        'total_usd': round(cpu_cost + mem_cost, 4),
        'rates_used': {'cpu_per_physical_core_s': cpu_rate, 'memory_per_gib_s': mem_rate},
    }
    return out


def to_markdown(a):
    lines = ['# LLM pilot analysis', '']
    m = a['model'] or {}
    c = a['compute'] or {}
    lines += [f"- stage: {a['source_stage']}", f"- model: {m.get('id')} @ {m.get('revision')}",
              f"- runtime: {m.get('versions')}", f"- compute: {c.get('label', c)}",
              f"- prompt fingerprint: {a['prompt_fingerprint']}",
              f"- runs declared: {a['n_runs_declared']}, rounds completed: {a['n_rounds']}, "
              f"decisions logged: {a['n_decisions']}, truncated: {a['truncated']}", '']
    v = a['validity']
    lines += ['## Output validity', '',
              f"- parse counts: {v['parse_counts']}",
              f"- strict rate: {v['strict_rate']}",
              f"- retries: {v['retried']}, fallbacks: {v['fallbacks']} (rate {v['fallback_rate']})",
              f"- mean new tokens: {v['mean_new_tokens']}, mean prompt tokens: {v['mean_prompt_tokens']}",
              f"- mean latency per prompt: {v['mean_latency_ms_per_prompt']} ms", '']
    if v['invalid_raw_outputs']:
        lines += ['Invalid raw outputs (first 10):', '']
        lines += [f'- `{x!r}`' for x in v['invalid_raw_outputs']] + ['']
    lines += ['## Action behaviour', '']
    for cond, d in a['actions_by_condition'].items():
        lines.append(f"- {cond}: shares { {k: round(x, 3) for k, x in d['share'].items()} }, "
                     f"entropy {round(d['entropy'], 4)}")
    lines.append('')
    for role, d in a['actions_by_role'].items():
        lines.append(f"- role {role}: counts {d['counts']}, entropy {round(d['entropy'], 4)}")
    lines += ['', '## Compliance', '']
    s = a['compliance']['seed_message_followed']
    lines += [f"- seed message followed: {s['followed']}/{s['n']} = {s['rate']}",
              f"- by condition: {a['compliance']['seed_by_condition']}",
              f"- cue rule followed: {a['compliance']['cue_followed']['followed']}"
              f"/{a['compliance']['cue_followed']['n']} = {a['compliance']['cue_followed']['rate']}",
              f"- recommendation followed (free agents): "
              f"{a['compliance']['recommendation_followed_free_agents']['followed']}"
              f"/{a['compliance']['recommendation_followed_free_agents']['n']} = "
              f"{a['compliance']['recommendation_followed_free_agents']['rate']}", '']
    lines += ['## Mean payoff', ''] + [f'- {k}: {round(v, 3)}' for k, v in a['mean_payoff'].items()] + ['']
    lines += ['## Descriptive influence statistics', '', a['influence_descriptive']['note'], '',
              '| condition | run | rounds | max cmi | max net | cmi top1 | net top1 | truth |',
              '|---|---|---|---|---|---|---|---|']
    for r in a['influence_descriptive']['per_run']:
        lines.append(f"| {r['condition']} | {r['run_index']} | {r['rounds']} | "
                     f"{r['max_cmi']:.4f} | {r['max_net']:.4f} | "
                     f"{r.get('cmi_top1')} | {r.get('net_top1')} | {r['truth_pair']} |")
    lines += ['', '## Cost estimate', '', f"_{a['cost_estimate']['label']}_", '']
    for k, v in a['cost_estimate'].items():
        if k != 'label':
            lines.append(f'- {k}: {v}')
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('payload', type=Path)
    args = parser.parse_args()
    payload = load(args.payload)
    analysis = analyse(payload)
    stem = args.payload.with_suffix('')
    Path(str(stem) + '-analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')
    text = to_markdown(analysis)
    Path(str(stem) + '-analysis.md').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
