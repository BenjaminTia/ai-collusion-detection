"""Device-agnostic generation engine for the frozen pilot protocol.

Shared by the GPU app (llm/modal_pilot.py) and the CPU fallback app
(llm/modal_cpu.py) so both produce the identical record schema. No statistics
are computed here: raw outputs are the source of truth and are analysed locally.

Rounds are processed in blocks only to batch prompts on the device. Within a block
the assistant prompt for round r is built from that same round's primary action, so
the sequential dependency of the seeded protocol is preserved exactly. Every prompt
is still a single stateless turn: no agent ever sees another agent's prompt.
"""
import hashlib
import json
import time

import llm_protocol as P


class Runner:
    def __init__(self, device='cuda', dtype='float16', threads=None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        if threads:
            torch.set_num_threads(threads)
        torch_dtype = {'float16': torch.float16, 'bfloat16': torch.bfloat16,
                       'float32': torch.float32}[dtype]
        self.dtype = dtype
        self.device = device
        t0 = time.time()
        self.tok = AutoTokenizer.from_pretrained(P.MODEL_ID, revision=P.MODEL_REVISION)
        # transformers >=5 renamed torch_dtype to dtype; keep one code path for both.
        # No device_map: that path requires `accelerate`, and a plain .to(device) is
        # enough for a single 1.5B model.
        common = {'revision': P.MODEL_REVISION}
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                P.MODEL_ID, dtype=torch_dtype, **common)
        except TypeError:
            self.model = AutoModelForCausalLM.from_pretrained(
                P.MODEL_ID, torch_dtype=torch_dtype, **common)
        self.model.to(device if device != 'cpu' else 'cpu')
        self.model.eval()
        self.tok.padding_side = 'left'
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.load_s = time.time() - t0
        self.versions = {'torch': torch.__version__}
        try:
            import transformers
            self.versions['transformers'] = transformers.__version__
        except Exception:
            pass
        if device == 'cuda':
            self.gpu = torch.cuda.get_device_name(0)
            self.vram_gb = round(
                torch.cuda.get_device_properties(0).total_memory / 2**30, 1)
        else:
            self.gpu = None
            self.vram_gb = None

    def chat_text(self, user):
        return self.tok.apply_chat_template(
            [{'role': 'system', 'content': P.SYSTEM_PROMPT},
             {'role': 'user', 'content': user}],
            tokenize=False, add_generation_prompt=True)

    def generate(self, prompts):
        """One batched greedy call. Returns [(raw_text, new_tokens)], latency_ms, prompt_tokens."""
        texts = [self.chat_text(p) for p in prompts]
        enc = self.tok(texts, return_tensors='pt', padding=True, truncation=True,
                       max_length=768).to(self.device)
        prompt_tokens = int(enc['input_ids'].shape[1])
        start = time.time()
        with self.torch.inference_mode():
            out = self.model.generate(
                **enc, max_new_tokens=P.MAX_NEW_TOKENS, do_sample=False,
                num_beams=1, pad_token_id=self.tok.pad_token_id)
        latency_ms = (time.time() - start) * 1000
        new = out[:, enc['input_ids'].shape[1]:]
        raws = self.tok.batch_decode(new, skip_special_tokens=True)
        counts = [int((row != self.tok.pad_token_id).sum()) for row in new]
        return list(zip(raws, counts)), latency_ms, prompt_tokens


def base_record(prompt, agent, condition, run_index, round_no, raw, ntok, latency, ptok,
                batch_size):
    action, how = P.parse_action(raw)
    return {
        'condition': condition, 'run_index': run_index, 'round': round_no,
        'agent': agent['agent'], 'name': agent['name'], 'role': agent['role'],
        'cue': agent['cue'], 'recommendation': agent['recommendation'],
        'team_follow_cue': agent['team_follow_cue'],
        'recommendation_shown': not agent['team_follow_cue'],
        'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
        'prompt_chars': len(prompt), 'prompt_tokens': ptok,
        'raw_output': raw, 'new_tokens': ntok,
        'latency_ms': round(latency / max(1, batch_size), 1),
        'batch_size': batch_size,
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


def run_condition(runner, condition, run_index, rounds, started, deadline_s, block=6):
    plan = P.plan_run(condition, run_index, rounds)
    blocks = [plan['rounds'][i:i + block] for i in range(0, len(plan['rounds']), block)]
    records, round_rows = [], []
    truncated = False
    for group in blocks:
        if time.time() - started > deadline_s:
            truncated = True
            break
        first_wave, assistant_prompts = [], []
        for rnd in group:
            assistant = next((a for a in rnd['agents'] if a['role'] == 'assistant'), None)
            for a in rnd['agents']:
                if a is assistant:
                    continue
                first_wave.append((rnd, a, P.build_prompt(
                    a['name'], a['cue'], a['recommendation'], a['team_follow_cue'], None)))
        outs, latency, ptok = runner.generate([p for _, _, p in first_wave])
        wave_records = {}
        for (rnd, a, prompt), (raw, ntok) in zip(first_wave, outs):
            rec = base_record(prompt, a, condition, run_index, rnd['round'],
                              raw, ntok, latency, ptok, len(first_wave))
            rec = settle(runner, rec, prompt, a)
            wave_records.setdefault(rnd['round'], []).append(rec)
        pending = []          # (rnd, assistant, prompt)
        for rnd in group:
            assistant = next((a for a in rnd['agents'] if a['role'] == 'assistant'), None)
            if assistant is None:
                continue
            primary = next(a for a in rnd['agents'] if a['role'] == 'primary')
            primary_action = next(r['action'] for r in wave_records[rnd['round']]
                                  if r['agent'] == primary['agent'])
            msg = P.seed_message(primary['name'], primary_action)
            prompt = P.build_prompt(assistant['name'], assistant['cue'],
                                    assistant['recommendation'],
                                    assistant['team_follow_cue'], msg)
            pending.append((rnd, assistant, prompt, msg))
        if pending:
            outs, latency, ptok = runner.generate([p for _, _, p, _ in pending])
            for (rnd, assistant, prompt, msg), (raw, ntok) in zip(pending, outs):
                rec = base_record(prompt, assistant, condition, run_index, rnd['round'],
                                  raw, ntok, latency, ptok, len(pending))
                rec['message'] = json.dumps(msg)
                rec = settle(runner, rec, prompt, assistant)
                wave_records[rnd['round']].append(rec)
        for rnd in group:
            rows = sorted(wave_records.get(rnd['round'], []), key=lambda x: x['agent'])
            if len(rows) != 4:
                continue
            actions = [r['action'] for r in rows]
            round_rows.append({'condition': condition, 'run_index': run_index,
                               'round': rnd['round'], 'cue': rnd['cue'],
                               'actions': ''.join(actions), 'payoffs': P.payoff(actions),
                               'pair': list(rnd['pair']), 'cue_pair': list(rnd['cue_pair']),
                               'recommendations': ''.join(rnd['recommendations'])})
            records.extend(rows)
    return records, round_rows, truncated, plan


def smoke(runner, probes=8):
    plan = P.plan_run('combined', 0, 2)
    items = []
    for rnd in plan['rounds']:
        for a in rnd['agents']:
            msg = P.seed_message('A', 'P') if a['role'] == 'assistant' else None
            items.append((a['role'], P.build_prompt(
                a['name'], a['cue'], a['recommendation'], a['team_follow_cue'], msg)))
    items = items[:probes]
    outs, latency, ptok = runner.generate([p for _, p in items])
    return {'probes': [{'role': role, 'prompt': prompt, 'raw_output': raw,
                        'new_tokens': n, 'parse': P.parse_action(raw)[1],
                        'action': P.parse_action(raw)[0]}
                       for (role, prompt), (raw, n) in zip(items, outs)],
            'batch_size': len(items), 'batch_latency_ms': round(latency, 1),
            'prompt_tokens': ptok,
            'ms_per_prompt': round(latency / max(1, len(items)), 1)}
