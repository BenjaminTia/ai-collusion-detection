"""Tests for the frozen LLM pilot protocol. No model, no network."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

import llm_protocol as P  # noqa: E402
import experiment  # noqa: E402


class Parsing(unittest.TestCase):
    def test_strict(self):
        self.assertEqual(P.parse_action('{"action": "P"}'), ('P', 'strict'))

    def test_tolerant_quotes_and_case(self):
        self.assertEqual(P.parse_action("{'action': 's'}")[0], 'S')
        self.assertEqual(P.parse_action('Sure: {"Action":"r"}')[0], 'R')

    def test_unparsed_is_none(self):
        self.assertEqual(P.parse_action('I choose paper.'), (None, 'unparsed'))
        self.assertEqual(P.parse_action(''), (None, 'unparsed'))
        self.assertEqual(P.parse_action(None), (None, 'empty'))

    def test_invalid_action_letter_rejected(self):
        self.assertEqual(P.parse_action('{"action": "X"}'), (None, 'unparsed'))


class PromptShape(unittest.TestCase):
    def test_prompt_is_deterministic_and_carries_context(self):
        a = P.build_prompt('B', 'P', 'R', False, None)
        b = P.build_prompt('B', 'P', 'R', False, None)
        self.assertEqual(a, b)
        self.assertIn('Player B', a)
        self.assertIn('PAPER', a)
        self.assertIn('ROCK', a)          # private recommendation
        self.assertIn('{"action": "R"}', a)

    def test_hidden_cue_is_not_leaked(self):
        prompt = P.build_prompt('B', None, 'R', False, None)
        self.assertIn('no public information', prompt)

    def test_team_rule_replaces_recommendation(self):
        prompt = P.build_prompt('B', 'S', 'R', True, None)
        self.assertIn('team rule', prompt.lower())
        self.assertNotIn('private recommendation', prompt)

    def test_message_is_quoted_verbatim(self):
        msg = P.seed_message('A', 'P')
        prompt = P.build_prompt('B', 'R', 'S', False, msg)
        self.assertIn(msg['text'], prompt)
        self.assertIn('Player A sent you a private message', prompt)

    def test_message_delivers_action_not_player_name(self):
        for action in P.ACTIONS:
            msg = P.seed_message('D', action)
            self.assertIn('I am playing ' + P.ACTION_NAME[action] + '.', msg['text'])
            self.assertNotIn('I am playing D.', msg['text'])
            self.assertEqual(msg['primary_action'], action)

    def test_embedded_json_is_not_strict(self):
        self.assertEqual(P.parse_action('Here: {"action":"R"}')[1], 'tolerant')

    def test_fingerprint_is_stable(self):
        self.assertEqual(P.prompt_fingerprint(), P.prompt_fingerprint())
        self.assertIn('prompt_fingerprint', P.frozen_block())


class Scheduling(unittest.TestCase):
    def test_plan_deterministic(self):
        self.assertEqual(P.plan_run('combined', 0, 5), P.plan_run('combined', 0, 5))

    def test_roles_per_condition(self):
        for condition in P.CONDITIONS:
            plan = P.plan_run(condition, 0, 3)
            roles = [[a['role'] for a in rnd['agents']] for rnd in plan['rounds']]
            flat = roles[0]
            self.assertEqual(len(flat), 4)
            if condition in ('seeded', 'combined'):
                self.assertEqual(flat.count('primary'), 1)
                self.assertEqual(flat.count('assistant'), 1)
                self.assertEqual(plan['pair'][0], flat.index('primary'))
                self.assertEqual(plan['pair'][1], flat.index('assistant'))
            else:
                self.assertNotIn('assistant', flat)
                self.assertNotIn('primary', flat)
            if condition in ('benign', 'combined'):
                self.assertEqual(flat.count('cue_follower'), 2)
                for i, role in enumerate(flat):
                    self.assertEqual(role == 'cue_follower', i in plan['cue_pair'])
                # scripted rule: benign -> the assigned pair follows the cue;
                # combined -> the two outsiders follow it, the assigned pair is seeded
                if condition == 'benign':
                    self.assertEqual(tuple(plan['cue_pair']), tuple(plan['pair']))
                else:
                    self.assertEqual(set(plan['cue_pair']).isdisjoint(set(plan['pair'])), True)
            else:
                self.assertNotIn('cue_follower', flat)

    def test_recommendations_and_cue_in_range(self):
        plan = P.plan_run('independent', 2, 40)
        for rnd in plan['rounds']:
            self.assertIn(rnd['cue'], P.ACTIONS)
            for rec in rnd['recommendations']:
                self.assertIn(rec, P.ACTIONS)
            self.assertEqual(rnd['cue'], rnd['agents'][0]['cue'])


class Game(unittest.TestCase):
    def test_beat_relation(self):
        for a in P.ACTIONS:
            self.assertEqual((P.ACTION_INDEX[a] - P.ACTION_INDEX[P.beat(a)]) % 3, 1)

    def test_message_mapping_matches_the_scripted_rule(self):
        # scripted: assistant = (primary - 1) % 3, i.e. the action primary beats.
        # Paper beats rock, so a PAPER primary asks the assistant for ROCK.
        self.assertEqual(P.beat('P'), 'R')
        self.assertEqual(P.beat('R'), 'S')
        self.assertEqual(P.beat_index(1), 0)
        self.assertEqual(P.beat_index(0), 2)
        for i in range(3):
            self.assertEqual(P.ACTION_INDEX[P.beat(P.ACTIONS[i])], P.beat_index(i))

    def test_payoff_matches_the_scripted_simulator(self):
        import itertools
        for combo in itertools.product(range(3), repeat=4):
            letters = [P.ACTIONS[i] for i in combo]
            self.assertEqual(P.payoff(letters), experiment.payoff(list(combo)),
                             f'mismatch on {combo}')


class FrozenRecord(unittest.TestCase):
    def test_frozen_block_records_model_and_revision(self):
        block = P.frozen_block()
        self.assertEqual(block['model_id'], 'Qwen/Qwen2.5-1.5B-Instruct')
        self.assertEqual(len(block['model_revision']), 40)
        json.dumps(block)   # must be serialisable as logged


if __name__ == '__main__':
    unittest.main()
