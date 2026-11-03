"""Bounded Modal GPU pilot for the Apart collusion audit. One GPU container, one model.

Frozen protocol in ../llm_protocol.py. This file only generates, logs and returns
raw records; all statistics are computed locally from the returned JSON so the raw
outputs stay the single source of truth.

Run from the project root:
    modal run llm/modal_pilot.py --stage smoke
    modal run llm/modal_pilot.py --stage pilot --runs 3 --rounds 30

Cost control: gpu L4 (USD 0.000222/s list price, checked 23 Oct 2026), max_containers=1,
timeout 900 s, a hard internal stop at 780 s that returns partial results, and no
deployed endpoint (min_containers default 0, so the container exits after the call).
"""
import hashlib
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import modal  # noqa: E402

import llm_protocol as P  # noqa: E402

app = modal.App('apart-collusion-llm-pilot')

image = (
    modal.Image.debian_slim(python_version='3.11')
    .pip_install(
        'torch==2.5.1',
        'transformers==4.46.3',
        'accelerate==1.1.1',
        'huggingface_hub==0.26.2',
        'safetensors==0.4.5',
    )
    .env({'HF_HUB_DISABLE_TELEMETRY': '1', 'TOKENIZERS_PARALLELISM': 'false'})
    .add_local_python_source('llm_protocol')
)

WALL_DEADLINE_S = 780


class Runner:
    def __init__(self):
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.t0 = time.time()
        self.tok = AutoTokenizer.from_pretrained(P.MODEL_ID, revision=P.MODEL_REVISION)
        self.model = AutoModelForCausalLM.from_pretrained(
            P.MODEL_ID, revision=P.MODEL_REVISION,
            torch_dtype=torch.float16, device_map={'': 0})
        self.model.eval()
        self.tok.padding_side = 'left'
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.load_s = time.time() - self.t0
        self.versions = {'torch': torch.__version__, 'transformers': transformers.__version__}
        self.gpu = torch.cuda.get_device_name(0)
        self.vram_gb = torch.cuda.get_device_properties(0).total_memory / 2**30

    def chat_text(self, user):
        return self.tok.apply_chat_template(
            [{'role': 'system', 'content': P.SYSTEM_PROMPT},
             {'role': 'user', 'content': user}],
            tokenize=False, add_generation_prompt=True)

    def generate(self, prompts):
        """One batched greedy call. Returns list of (raw_text, new_tokens, latency_ms, prompt_tokens)."""
        texts = [self.chat_text(p) for p in prompts]
        enc = self.tok(texts, return_tensors='pt', padding=True, truncation=True,
                       max_length=768).to('cuda')
        prompt_tokens = int(enc['input_ids'].shape[1])
        start = time.time()
        with self.torch.no_grad():
            out = self.model.generate(
                **enc, max_new_tokens=P.MAX_NEW_TOKENS, do_sample=False,
                num_beams=1, pad_token_id=self.tok.pad_token_id)
        latency_ms = (time.time() - start) * 1000
        new = out[:, enc['input_ids'].shape[1]:]
        raws = self.tok.batch_decode(new, skip_special_tokens=True)
        counts = [int((row != self.tok.pad_token_id).sum()) for row in new]
        return list(zip(raws, counts)), latency_ms, prompt_tokens


def base_record(prompt, agent, condition, run_index, round_no, raw, ntok, latency, ptok):
    action, how = P.parse_action(raw)
    return {
        'condition': condition, 'run_index': run_index, 'round': round_no,
        'agent': agent['agent'], 'name': agent['name'], 'role': agent['role'],
        'cue': agent['cue'], 'recommendation': agent['recommendation'],
        'team_follow_cue': agent['team_follow_cue'],
        'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
        'prompt_chars': len(prompt), 'prompt_tokens': ptok,
        'raw_output': raw, 'new_tokens': ntok, 'latency_ms': round(latency, 1),
        'parse': how, 'action': action,
        'retried': False, 'retry_raw': None, 'retry_parse': None,
        'retry_new_tokens': None, 'fallback': False,
    }


def settle(runner, record, prompt, agent):
    """Prespecified handling: one retry, then fall back to the recommendation, logged."""
    if record['action'] is not None:
        return record
    outs, latency, _ = runner.generate([prompt + P.RETRY_SUFFIX])
    raw2, ntok2 = outs[0]
    action2, how2 = P.parse_action(raw2)
    record.update({'retried': True, 'retry_raw': raw2, 'retry_parse': how2,
                   'retry_new_tokens': ntok2, 'retry_latency_ms': round(latency, 1)})
    if action2 is not None:
        record.update({'action': action2, 'parse': 'retry:' + how2})
    else:
        record.update({'action': agent['recommendation'], 'fallback': True,
                       'parse': 'fallback_to_recommendation'})
    return record


def run_condition(runner, condition, run_index, rounds, started):
    plan = P.plan_run(condition, run_index, rounds)
    records, round_rows = [], []
    truncated = False
    for rnd in plan['rounds']:
        if time.time() - started > WALL_DEADLINE_S:
            truncated = True
            break
        agents = rnd['agents']
        assistant = next((a for a in agents if a['role'] == 'assistant'), None)
        first_wave = [a for a in agents if a is not assistant]
        prompts = [P.build_prompt(a['name'], a['cue'], a['recommendation'],
                                  a['team_follow_cue'], None) for a in first_wave]
        outs, latency, ptok = runner.generate(prompts)
        wave_records = []
        for a, prompt, (raw, ntok) in zip(first_wave, prompts, outs):
            rec = base_record(prompt, a, condition, run_index, rnd['round'],
                              raw, ntok, latency / max(1, len(prompts)), ptok)
            wave_records.append(settle(runner, rec, prompt, a))
        if assistant is not None:
            primary = next(a for a in agents if a['role'] == 'primary')
            primary_action = next(rec['action'] for rec in wave_records
                                  if rec['agent'] == primary['agent'])
            msg = P.seed_message(primary['name'], primary_action)
            prompt = P.build_prompt(assistant['name'], assistant['cue'],
                                    assistant['recommendation'],
                                    assistant['team_follow_cue'], msg)
            outs, latency, ptok = runner.generate([prompt])
            raw, ntok = outs[0]
            rec = base_record(prompt, assistant, condition, run_index, rnd['round'],
                              raw, ntok, latency, ptok)
            rec['message'] = json.dumps(msg)
            wave_records.append(settle(runner, rec, prompt, assistant))
        by_agent = sorted(wave_records, key=lambda x: x['agent'])
        actions = [r['action'] for r in by_agent]
        payoffs = P.payoff(actions)
        round_rows.append({'condition': condition, 'run_index': run_index,
                           'round': rnd['round'], 'cue': rnd['cue'],
                           'actions': ''.join(actions), 'payoffs': payoffs,
                           'pair': list(rnd['pair']), 'cue_pair': list(rnd['cue_pair']),
                           'recommendations': ''.join(rnd['recommendations'])})
        records.extend(wave_records)
    return records, round_rows, truncated, plan


@app.function(image=image, gpu=['L4', 'T4'], timeout=900, max_containers=1,
              retries=0)
def pilot(stage='smoke', runs=3, rounds=30):
    started = time.time()
    runner = Runner()
    payload = {
        'stage': stage,
        'model': {'id': P.MODEL_ID, 'revision': P.MODEL_REVISION,
                  'gpu': runner.gpu, 'vram_gb': round(runner.vram_gb, 1),
                  'dtype': 'float16', 'versions': runner.versions,
                  'load_seconds': round(runner.load_s, 1)},
        'frozen': P.frozen_block(),
    }
    if stage == 'smoke':
        probes = []
        plan = P.plan_run('combined', 0, 2)
        for rnd in plan['rounds']:
            for a in rnd['agents']:
                msg = P.seed_message('A', 'P') if a['role'] == 'assistant' else None
                probes.append((a['role'], P.build_prompt(
                    a['name'], a['cue'], a['recommendation'],
                    a['team_follow_cue'], msg)))
        outs, latency, ptok = runner.generate([p for _, p in probes])
        payload['smoke'] = [{'role': role, 'prompt': prompt, 'raw_output': raw,
                             'new_tokens': n, 'parse': P.parse_action(raw)[1],
                             'action': P.parse_action(raw)[0]}
                            for (role, prompt), (raw, n) in zip(probes, outs)]
        payload['prompt_tokens'] = ptok
        payload['batch_latency_ms'] = round(latency, 1)
    else:
        all_records, all_rounds = [], []
        truncated_any = False
        for condition in P.CONDITIONS:
            for run_index in range(runs):
                records, round_rows, truncated, plan = run_condition(
                    runner, condition, run_index, rounds, started)
                truncated_any = truncated_any or truncated
                all_records.extend(records)
                all_rounds.extend(round_rows)
                payload.setdefault('runs', []).append({
                    'condition': condition, 'run_index': run_index, 'seed': plan['seed'],
                    'pair': list(plan['pair']), 'cue_pair': list(plan['cue_pair']),
                    'names': plan['names'], 'rounds_completed': len(round_rows)})
                print(f"[pilot] {condition} run {run_index}: {len(round_rows)} rounds, "
                      f"{time.time() - started:.1f}s elapsed", flush=True)
        payload['records'] = all_records
        payload['rounds'] = all_rounds
        payload['truncated'] = truncated_any
    payload['timing'] = {'load_seconds': round(runner.load_s, 1),
                         'total_seconds': round(time.time() - started, 1)}
    # Pure-JSON payload: the local client must not need torch to deserialise the result.
    return json.loads(json.dumps(payload, default=str))


@app.local_entrypoint()
def main(stage: str = 'smoke', runs: int = 3, rounds: int = 30,
         out: str = 'results/llm-pilot'):
    started = time.time()
    payload = pilot.remote(stage=stage, runs=runs, rounds=rounds)
    wall = time.time() - started
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{stage}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    payload['local_wall_seconds'] = round(wall, 1)
    target.write_text(json.dumps(payload, indent=1), encoding='utf-8')
    print(json.dumps({'stage': stage, 'path': str(target),
                      'model': payload['model'], 'timing': payload['timing'],
                      'local_wall_seconds': round(wall, 1),
                      'n_records': len(payload.get('records', [])),
                      'n_rounds': len(payload.get('rounds', [])),
                      'truncated': payload.get('truncated')}, indent=2))
