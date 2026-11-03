"""LOCAL GPU FALLBACK for the frozen pilot protocol.

Modal refused every GPU type on this workspace ("Please add a payment method to use
L4/T4 GPU functions"), so the pilot runs on the local RTX 4050 with the same frozen
protocol, prompts, model revision and record schema as llm/modal_pilot.py. This is a
real 1.5B instruct model producing real outputs; it is NOT a Modal GPU result, and its
latency figures describe a laptop GPU only.

    python llm/local_pilot.py --stage smoke
    python llm/local_pilot.py --stage pilot --runs 3 --rounds 30

`--sealed` is NOT used here: nothing about the run is hidden, every raw output is kept.
"""
import argparse
import json
import sys
import time
from pathlib import Path

LLM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LLM_DIR))
sys.path.insert(0, str(LLM_DIR.parent))

import engine as E  # noqa: E402
import llm_protocol as P  # noqa: E402

CONDITION_ORDER = ('seeded', 'combined', 'benign', 'independent')


def run(stage='smoke', runs=3, rounds=30, block=6, out='results/llm-pilot',
        dtype='float16', deadline_s=780):
    started = time.time()
    runner = E.Runner(device='cuda', dtype=dtype)
    payload = {
        'stage': stage,
        'compute': {'device': 'cuda', 'dtype': dtype, 'gpu': runner.gpu,
                    'vram_gb': runner.vram_gb, 'host': 'local Windows machine (RTX 4050 laptop)',
                    'label': 'LOCAL GPU FALLBACK: real model outputs, not a Modal run'},
        'model': {'id': P.MODEL_ID, 'revision': P.MODEL_REVISION,
                  'versions': runner.versions, 'load_seconds': round(runner.load_s, 1)},
        'frozen': P.frozen_block(),
        'block_rounds': block,
    }
    if stage == 'smoke':
        t = time.time()
        payload['smoke'] = E.smoke(runner, probes=8)
        payload['smoke_seconds'] = round(time.time() - t, 1)
    else:
        records, round_rows, run_rows = [], [], []
        truncated_any = False
        for run_index in range(runs):
            for condition in CONDITION_ORDER:
                recs, rows, truncated, plan = E.run_condition(
                    runner, condition, run_index, rounds, started, deadline_s, block)
                truncated_any = truncated_any or truncated
                records.extend(recs)
                round_rows.extend(rows)
                run_rows.append({'condition': condition, 'run_index': run_index,
                                 'seed': plan['seed'], 'pair': list(plan['pair']),
                                 'cue_pair': list(plan['cue_pair']), 'names': plan['names'],
                                 'rounds_completed': len(rows)})
                print(f"[local] {condition} run {run_index}: {len(rows)} rounds, "
                      f"{time.time() - started:.1f}s", flush=True)
        payload.update({'records': records, 'rounds': round_rows, 'runs': run_rows,
                        'truncated': truncated_any})
    payload['timing'] = {'load_seconds': round(runner.load_s, 1),
                         'total_seconds': round(time.time() - started, 1)}
    return json.loads(json.dumps(payload, default=str))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='smoke')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--rounds', type=int, default=30)
    parser.add_argument('--block', type=int, default=6)
    parser.add_argument('--dtype', default='float16')
    parser.add_argument('--out', default='results/llm-pilot')
    args = parser.parse_args()
    payload = run(args.stage, args.runs, args.rounds, args.block, args.out, args.dtype)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"local-{args.stage}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    target.write_text(json.dumps(payload, indent=1), encoding='utf-8')
    print(json.dumps({'stage': args.stage, 'path': str(target),
                      'compute': payload['compute'], 'model': payload['model'],
                      'timing': payload['timing'],
                      'smoke_seconds': payload.get('smoke_seconds'),
                      'n_records': len(payload.get('records', [])),
                      'n_rounds': len(payload.get('rounds', [])),
                      'truncated': payload.get('truncated')}, indent=2))


if __name__ == '__main__':
    main()
