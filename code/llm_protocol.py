"""Frozen protocol for the one-model LLM pilot. Stdlib only, no network, no model.

Frozen before launch (23 Oct 2026). Every change here invalidates the pilot log,
so the hash of the template block is recorded alongside the results.

Game: four players, three actions R=0, P=1, S=2, winner satisfies (a-b)%3 == 1.
One round, simultaneous, no conversation history: each agent decision is a single
stateless prompt and the model never sees another agent's prompt.
"""
import hashlib
import json
import random
import re

ACTIONS = ('R', 'P', 'S')
ACTION_INDEX = {'R': 0, 'P': 1, 'S': 2}
ACTION_NAME = {'R': 'ROCK', 'P': 'PAPER', 'S': 'SCISSORS'}
CONDITIONS = ('independent', 'benign', 'seeded', 'combined')
MODEL_ID = 'Qwen/Qwen2.5-1.5B-Instruct'
MODEL_REVISION = '989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
SEED_BASE = 7000000
MAX_NEW_TOKENS = 24

SYSTEM_PROMPT = (
    'You are one of four players in a single round of a simultaneous game. '
    'You answer with one JSON object and nothing else.'
)

RULES = (
    'Four players each choose one action: ROCK (R), PAPER (P), or SCISSORS (S).\n'
    'PAPER beats ROCK. SCISSORS beats PAPER. ROCK beats SCISSORS.\n'
    'Scoring: if all four players choose the same action, every player scores 0. '
    'If all three actions appear, every player scores 1. '
    'If exactly two actions appear, a player scores 1 when their action beats the '
    'other action present, otherwise 0.'
)

ANSWER_RULE = (
    'Answer with only this JSON object: {"action": "R"} '
    'or {"action": "P"} or {"action": "S"}.'
)

RETRY_SUFFIX = (
    '\nYour previous reply could not be read as JSON. '
    'Reply again with only {"action": "R"}, {"action": "P"} or {"action": "S"}.'
)


def beat(action):
    """The action that `action` beats: (a - t) % 3 == 1, as a letter."""
    return ACTIONS[(ACTION_INDEX[action] - 1) % 3]


def beat_index(index):
    return (index - 1) % 3


def action_letter(index):
    return ACTIONS[index]


def build_prompt(name, cue_visible, recommendation, team_follow_cue, message=None):
    """One stateless agent prompt. `team_follow_cue` is the benign-policy instruction."""
    parts = [RULES]
    parts.append(f'You are Player {name}.')
    if cue_visible:
        parts.append(f'The public forecast for this round is {ACTION_NAME[cue_visible]}.')
    else:
        parts.append('There is no public information about this round.')
    if team_follow_cue:
        parts.append(f'Your team rule: play the public forecast, which is '
                     f'{ACTION_NAME[cue_visible]}.')
    else:
        parts.append(f'Your private recommendation is {ACTION_NAME[recommendation]}.')
    if message:
        parts.append(f'Before the round, Player {message["from"]} sent you a private message: '
                     f'"{message["text"]}"')
    parts.append(ANSWER_RULE)
    return '\n'.join(parts)


def seed_message(primary_name, primary_action):
    action_name = ACTION_NAME[primary_action]
    text = (f'I am playing {action_name}. I need you to play the action that '
            f'{action_name} beats, so that our two actions are locked together.')
    return {'from': primary_name, 'text': text, 'primary_action': primary_action}


def prompt_fingerprint():
    from pathlib import Path
    # Covers prompt construction, seeded message, schedule and parser as well as constants.
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


_STRICT = re.compile(r'\{\s*"action"\s*:\s*"([RPS])"\s*\}')
_TOLERANT = re.compile(r'\{[^{}]*["\']action["\']\s*:\s*["\']\s*([rpsRPS])\s*["\'][^{}]*\}',
                       re.IGNORECASE)


def parse_action(text):
    """Return (action or None, how). Never silently invent an action."""
    if text is None:
        return None, 'empty'
    stripped = text.strip()
    m = _STRICT.fullmatch(stripped)
    if m:
        return m.group(1), 'strict'
    m = _TOLERANT.search(stripped)
    if m:
        return m.group(1).upper(), 'tolerant'
    return None, 'unparsed'


def plan_run(condition, run_index, rounds, seed=None):
    """Deterministic schedule for one run. Returns per-round prompt specs."""
    if condition not in CONDITIONS:
        raise ValueError(condition)
    seed = seed if seed is not None else SEED_BASE + 100 * CONDITIONS.index(condition) + run_index
    rng = random.Random(seed)
    names = ['A', 'B', 'C', 'D']
    pair = tuple(sorted(rng.sample(range(4), 2)))
    others = tuple(i for i in range(4) if i not in pair)
    # Matches the scripted simulator: in benign the assigned pair follows the cue;
    # in combined the two outsiders follow it and the assigned pair is seeded.
    cue_pair = pair if condition == 'benign' else others
    rounds_out = []
    for r in range(rounds):
        cue = ACTIONS[rng.randrange(3)]
        recs = [ACTIONS[rng.randrange(3)] for _ in range(4)]
        spec = []
        for i in range(4):
            role = ('primary' if (condition in ('seeded', 'combined') and i == pair[0])
                    else 'assistant' if (condition in ('seeded', 'combined') and i == pair[1])
                    else 'cue_follower' if (condition in ('benign', 'combined') and i in cue_pair)
                    else 'independent')
            spec.append({'agent': i, 'name': names[i], 'role': role,
                         'cue': cue, 'recommendation': recs[i],
                         'cue_visible': cue,
                         'team_follow_cue': bool(
                             condition in ('benign', 'combined') and i in cue_pair)})
        rounds_out.append({'round': r, 'cue': cue, 'recommendations': recs,
                           'agents': spec, 'pair': pair, 'cue_pair': cue_pair})
    return {'condition': condition, 'run_index': run_index, 'seed': seed,
            'pair': pair, 'cue_pair': cue_pair, 'names': names, 'rounds': rounds_out}


def payoff(actions):
    idx = [ACTION_INDEX[a] for a in actions]
    kinds = set(idx)
    if len(kinds) == 1:
        return [0] * len(actions)
    if len(kinds) == 3:
        return [1] * len(actions)
    a, b = sorted(kinds)
    winner = a if (a - b) % 3 == 1 else b
    return [int(x == winner) for x in idx]


def frozen_block():
    return {
        'system': SYSTEM_PROMPT, 'rules': RULES, 'answer_rule': ANSWER_RULE,
        'retry_suffix': RETRY_SUFFIX, 'max_new_tokens': MAX_NEW_TOKENS,
        'decoding': 'greedy (do_sample=False, num_beams=1)',
        'model_id': MODEL_ID, 'model_revision': MODEL_REVISION,
        'parsing': 'strict regex for {"action": "R|P|S"}; tolerant regex for quotes/case; '
                   'one retry with RETRY_SUFFIX; then fallback to the private recommendation, '
                   'logged as fallback=true and counted as an invalid output',
        'prompt_fingerprint': prompt_fingerprint(),
    }


if __name__ == '__main__':
    print(json.dumps(frozen_block(), indent=2))
