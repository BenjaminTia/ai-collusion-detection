"""LABELLED CPU FALLBACK for the frozen pilot protocol.

The workspace cannot launch any GPU (L4 or T4) without a payment method on file, so
this app runs the identical frozen protocol on a CPU container. It is NOT the GPU
smoke test and its latency numbers must not be read as GPU numbers. What it does
establish: real model outputs for every prompt, JSON-action validity, retry and
fallback rates, seed-message compliance, action variation, and a measured CPU cost.

    modal run llm/modal_cpu.py --stage smoke
    modal run llm/modal_cpu.py --stage pilot --runs 3 --rounds 30
"""
import json
import sys
import time
from pathlib import Path

LLM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LLM_DIR))
sys.path.insert(0, str(LLM_DIR.parent))

import modal  # noqa: E402

import llm_protocol as P  # noqa: E402
import engine as E  # noqa: E402

app = modal.App('apart-collusion-cpu-pilot')

image = (
    modal.Image.debian_slim(python_version='3.11')
    .pip_install(
        'torch==2.5.1',
        'transformers==4.46.3',
        'accelerate==1.1.1',
        'huggingface_hub==0.26.2',
        'safetensors==0.4.5',
        'numpy<2.3',
    )
    .env({'HF_HUB_DISABLE_TELEMETRY': '1', 'TOKENIZERS_PARALLELISM': 'false'})
    .add_local_python_source('llm_protocol', 'engine')
)

DEADLINE_S = 780
# Seeded/combined first, then one run of every condition before any second run, so a
# deadline truncation still leaves every condition represented.
CONDITION_ORDER = ('seeded', 'combined', 'benign', 'independent')


@app.function(image=image, cpu=16, memory=32768, timeout=900, max_containers=1, retries=0)
def pilot(stage='smoke', runs=3, rounds=30, block=6, dtype='float32', threads=16):
    started = time.time()
    runner = E.Runner(device='cpu', dtype=dtype, threads=threads)
    payload = {
        'stage': stage,
        'compute': {'device': 'cpu', 'dtype': dtype, 'cpu_cores': 16,
                    'memory_mb': 32768, 'threads': threads,
                    'label': 'CPU FALLBACK: not a GPU result'},
        'model': {'id': P.MODEL_ID, 'revision': P.MODEL_REVISION,
                  'versions': runner.versions, 'load_seconds': round(runner.load_s, 1)},
        'frozen': P.frozen_block(),
        'block_rounds': block,
    }
    if stage == 'bench':
        plan = P.plan_run('seeded', 0, 12)
        prompts = []
        for rnd in plan['rounds']:
            for a in rnd['agents']:
                prompts.append(P.build_prompt(a['name'], a['cue'], a['recommendation'],
                                              a['team_follow_cue'], None))
        prompts = prompts[:24]
        payload['bench'] = []
        for label, dt, nth in [('fp32_16t', 'float32', 16), ('bf16_16t', 'bfloat16', 16),
                               ('bf16_8t', 'bfloat16', 8), ('fp32_8t', 'float32', 8)]:
            runner.model.to({'float32': runner.torch.float32,
                             'bfloat16': runner.torch.bfloat16}[dt])
            runner.torch.set_num_threads(nth)
            runner.generate(prompts[:4])                      # warm-up, not timed
            t = time.time()
            runner.generate(prompts)
            seconds = time.time() - t
            payload['bench'].append({'label': label, 'dtype': dt, 'threads': nth,
                                     'batch': len(prompts),
                                     'seconds': round(seconds, 2),
                                     'ms_per_prompt': round(seconds * 1000 / len(prompts), 1),
                                     'projected_1440_prompts_s': round(seconds * 1440 / len(prompts), 0)})
            print('[bench]', payload['bench'][-1], flush=True)
    elif stage == 'smoke':
        t = time.time()
        payload['smoke'] = E.smoke(runner, probes=8)
        payload['smoke_seconds'] = round(time.time() - t, 1)
    else:
        all_records, all_rounds, run_rows = [], [], []
        truncated_any = False
        for run_index in range(runs):
            for condition in CONDITION_ORDER:
                records, round_rows, truncated, plan = E.run_condition(
                    runner, condition, run_index, rounds, started, DEADLINE_S, block)
                truncated_any = truncated_any or truncated
                all_records.extend(records)
                all_rounds.extend(round_rows)
                run_rows.append({'condition': condition, 'run_index': run_index,
                                 'seed': plan['seed'], 'pair': list(plan['pair']),
                                 'cue_pair': list(plan['cue_pair']),
                                 'names': plan['names'],
                                 'rounds_completed': len(round_rows)})
                print(f'[cpu-pilot] {condition} run {run_index}: {len(round_rows)} rounds, '
                      f'{time.time() - started:.1f}s elapsed', flush=True)
        payload['records'] = all_records
        payload['rounds'] = all_rounds
        payload['runs'] = run_rows
        payload['truncated'] = truncated_any
    payload['timing'] = {'load_seconds': round(runner.load_s, 1),
                         'total_seconds': round(time.time() - started, 1)}
    print('[cpu-pilot] returning payload', flush=True)
    # Force a pure-JSON payload: the local client must not need torch to deserialise
    # the result, and nothing that is not JSON belongs in a raw-output log.
    return json.loads(json.dumps(payload, default=str))


@app.local_entrypoint()
def main(stage: str = 'smoke', runs: int = 3, rounds: int = 30, block: int = 6,
         dtype: str = 'float32', threads: int = 16,
         out: str = 'results/llm-pilot'):
    started = time.time()
    payload = pilot.remote(stage=stage, runs=runs, rounds=rounds, block=block,
                           dtype=dtype, threads=threads)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"cpu-{stage}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    payload['local_wall_seconds'] = round(time.time() - started, 1)
    target.write_text(json.dumps(payload, indent=1), encoding='utf-8')
    print(json.dumps({'stage': stage, 'path': str(target), 'compute': payload['compute'],
                      'model': payload['model'], 'timing': payload['timing'],
                      'smoke_seconds': payload.get('smoke_seconds'),
                      'n_records': len(payload.get('records', [])),
                      'n_rounds': len(payload.get('rounds', [])),
                      'truncated': payload.get('truncated')}, indent=2))
