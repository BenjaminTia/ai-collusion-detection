import itertools
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from experiment import cmi,scores,payoff,simulate,observed,rank_stats

class Validation(unittest.TestCase):
    def test_exact_independence(self):
        triples=list(itertools.product(range(3),repeat=3))*10
        self.assertAlmostEqual(cmi([a for a,b,s in triples],[b for a,b,s in triples],[s for a,b,s in triples]),0)
    def test_perfect_link(self):
        a=[0,1,2]*100;b=[(x-1)%3 for x in a]
        self.assertAlmostEqual(cmi(a,b,[0]*len(a)),math.log(3))
    def test_public_cue(self):
        s=[0,1,2]*100
        self.assertAlmostEqual(cmi(s,s,[0]*len(s)),math.log(3))
        self.assertAlmostEqual(cmi(s,s,s),0)
    def test_constant_coordination_is_invisible(self):
        self.assertEqual(cmi([0]*100,[2]*100,[0]*100),0)
    def test_action_relabelling(self):
        r=simulate('combined',1000,19)
        before=scores(r['actions'],r['cue'])
        mapping={0:2,1:0,2:1}
        after=scores([[mapping[x] for x in row] for row in r['actions']],r['cue'])
        for x,y in zip(before,after):
            for p in x:self.assertAlmostEqual(x[p],y[p])
    def test_agent_relabelling(self):
        r=simulate('seeded',1000,42);order=[2,0,3,1]
        before=scores(r['actions'],r['cue']);after=scores([[row[i] for i in order] for row in r['actions']],r['cue'])
        for x,y in zip(before,after):
            for (i,j),v in y.items():self.assertAlmostEqual(v,x[tuple(sorted((order[i],order[j])))])
    def test_strong_seeded_pair(self):
        r=simulate('seeded',3000,8,strength=1)
        _,net=scores(r['actions'],r['cue'])
        self.assertEqual(max(net,key=net.get),r['pair'])
        self.assertEqual(r['compliance'],1)
    def test_deterministic_replay(self):
        self.assertEqual(simulate('combined',30,8),simulate('combined',30,8))
    def test_no_coalition_ground_truth(self):
        for c in ['independent','benign']:self.assertIsNone(simulate(c,50,6)['pair'])
    def test_ties(self):
        _,net=scores([[0,0,0,0]]*20,[0]*20)
        top,auc=rank_stats(net,(0,1))
        self.assertAlmostEqual(top,1/6);self.assertEqual(auc,0.5)
    def test_payoffs(self):
        self.assertEqual(payoff([0,0,0,0]),[0,0,0,0])
        self.assertEqual(payoff([0,1,2,0]),[1,1,1,1])
        self.assertEqual(payoff([0,2,2,0]),[1,0,0,1])
    def test_input_validation(self):
        with self.assertRaises(ValueError):cmi([],[],[])
        with self.assertRaises(ValueError):cmi([1],[],[])

if __name__=='__main__':unittest.main()
