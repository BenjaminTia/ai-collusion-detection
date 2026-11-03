"""Tests for the within-state permutation calibration. Execute, do not assume."""
import random
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from experiment import cmi, observed, scores, simulate  # noqa: E402
from permutation_calibration import (evaluate_run, permutation_null,  # noqa: E402
                                     strata, thresholds_from_null, within_state_shuffle)


class PermutationMechanics(unittest.TestCase):
    def setUp(self):
        self.run = simulate('combined', 600, 11)
        self.states = observed(self.run, '0.3')

    def test_within_state_marginals_preserved(self):
        shuffled = within_state_shuffle(self.run['actions'], self.states, random.Random(7))
        groups = strata(self.states)
        for col in range(4):
            for _, idx in groups.items():
                before = Counter(self.run['actions'][i][col] for i in idx)
                after = Counter(shuffled[i][col] for i in idx)
                self.assertEqual(before, after)

    def test_state_alignment_preserved(self):
        shuffled = within_state_shuffle(self.run['actions'], self.states, random.Random(8))
        self.assertEqual(len(shuffled), len(self.states))
        # Each column is shuffled independently, so the tuple at a position need not
        # match an original row. The invariant is that every value at position i for
        # column c is drawn from column c's multiset inside position i's stratum.
        groups = strata(self.states)
        for col in range(4):
            for i, s in enumerate(self.states):
                allowed = {self.run['actions'][j][col] for j in groups[s]}
                self.assertIn(shuffled[i][col], allowed)

    def test_shuffle_is_deterministic(self):
        a = within_state_shuffle(self.run['actions'], self.states, random.Random(3))
        b = within_state_shuffle(self.run['actions'], self.states, random.Random(3))
        self.assertEqual(a, b)

    def test_shuffle_breaks_a_perfect_link(self):
        actions = [[0, 0, 0, 0], [1, 1, 1, 1], [2, 2, 2, 2]] * 200
        states = [0] * len(actions)
        g_before, _ = scores(actions, states)
        shuffled = within_state_shuffle(actions, states, random.Random(5))
        g_after, _ = scores(shuffled, states)
        self.assertGreater(g_before[0, 1], 1.0)
        self.assertLess(g_after[0, 1], 0.05)

    def test_constant_columns_within_observed_state_do_not_change(self):
        cue = [0, 1, 2] * 200
        actions = [[s, s, 0, 1] for s in cue]
        shuffled = within_state_shuffle(actions, cue, random.Random(6))
        self.assertEqual(actions, shuffled)
        g_after, _ = scores(shuffled, cue)
        self.assertAlmostEqual(g_after[0, 1], 0.0)

    def test_missing_context_dependence_exceeds_shuffled_null(self):
        # The observed benign dependence remains; independent column permutation
        # destroys it under the candidate null. That mismatch explains rejection.
        cue = [0, 1, 2] * 200
        actions = [[s, s, 0, 1] for s in cue]
        missing = [0] * len(cue)
        shuffled = within_state_shuffle(actions, missing, random.Random(6))
        before, _ = scores(actions, missing)
        after, _ = scores(shuffled, missing)
        self.assertGreater(before[0, 1], 1.0)
        self.assertLess(after[0, 1], 0.05)


class CalibrationBehaviour(unittest.TestCase):
    def _fpr(self, condition, mode, method, runs=30, rounds=600, perms=99):
        alarms = 0
        for seed in range(runs):
            recs = evaluate_run(condition, seed, rounds, perms, (mode,))
            alarms += sum(r['any_alarm'] for r in recs if r['method'] == method)
        return alarms / runs

    def test_benign_full_cue_is_controlled(self):
        # The original independent-null threshold produced 33% net false alarms here.
        for method in ('cmi', 'net'):
            fpr = self._fpr('benign', 'full', method)
            self.assertLessEqual(fpr, 0.20, f'benign/full/{method} FPR {fpr:.3f} not controlled')

    def test_independent_runs_are_controlled(self):
        for method in ('cmi', 'net'):
            fpr = self._fpr('independent', 'full', method, runs=40)
            self.assertLessEqual(fpr, 0.18, f'independent/full/{method} FPR {fpr:.3f}')

    def test_missing_cue_stays_at_ceiling(self):
        # Honest limitation: permutation tests conditional independence given the
        # recorded state and cannot cure an unobserved common cause.
        for method in ('cmi', 'net'):
            fpr = self._fpr('benign', 'none', method, runs=20)
            self.assertGreaterEqual(fpr, 0.85, f'benign/none/{method} FPR {fpr:.3f}')

    def test_power_on_seeded_combined_is_preserved(self):
        for seed in range(10):
            recs = evaluate_run('combined', seed, 600, 99, ('full',))
            for method in ('cmi', 'net'):
                row = [r for r in recs if r['method'] == method][0]
                self.assertTrue(row['any_alarm'], f'combined/full/{method} failed to alarm')
                self.assertEqual(row['top1_credit'], 1.0, f'combined/full/{method} top1')

    def test_null_marginals_match_the_conditional_independence_null(self):
        run = simulate('benign', 800, 21)
        states = observed(run, 'full')
        null = permutation_null(run['actions'], states, 60, random.Random(4))
        thr = thresholds_from_null(null)
        self.assertGreaterEqual(thr['cmi'], 0.0)
        self.assertGreaterEqual(thr['net'], 0.0)
        # cue-following columns are constant inside a stratum, so the permuted
        # mixed-pair CMI stays at the finite-sample floor, not at log 3
        self.assertLess(thr['cmi'], 0.10)


if __name__ == '__main__':
    unittest.main()
