"""Artifact-grounded regression checks for the research harness, no inference."""
import itertools,json,random,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'llm')]
import llm_protocol as P
from edge0_pilot import strict_action
from experiment import scores,simulate,observed

class ProtocolGates(unittest.TestCase):
 def test_exact_json(self):
  for a in P.ACTIONS:self.assertEqual(strict_action(json.dumps({'action':a})),a)
 def test_no_extra_keys(self):self.assertIsNone(strict_action('{"action":"P","reason":"x"}'))
 def test_no_prose(self):self.assertIsNone(strict_action('I choose {"action":"P"}'))
 def test_no_fenced_json(self):self.assertIsNone(strict_action('```json\n{"action":"P"}\n```'))
 def test_invalid_action(self):self.assertIsNone(strict_action('{"action":"X"}'))
 def test_round_payoff(self):
  for x in itertools.product(P.ACTIONS,repeat=4):
   result=P.payoff(x);self.assertEqual(len(result),4);self.assertTrue(set(result)<= {0,1})
 def test_private_actual_action(self):
  for a in P.ACTIONS:
   m=P.seed_message('A',a);self.assertIn(P.ACTION_NAME[a],m['text']);self.assertEqual(m['primary_action'],a)
 def test_new_seed_separation(self):
  seeds={8100000+10000*i+100*c for i in range(3) for c in range(4)}
  self.assertEqual(len(seeds),12);self.assertTrue(seeds.isdisjoint({7000000+100*c+i for c in range(4) for i in range(3)}))
 def test_single_agent_action_relabelling_invariance(self):
  # An information statistic ignores a bijective relabelling of any ONE agent's
  # symbols, not only a common relabelling of all agents. Scope: these scores.
  for seed in range(5):
   run=simulate('combined',300,seed)
   changed=[[((x+1)%3 if i==1 else x) for i,x in enumerate(row)] for row in run['actions']]
   for mode in ('none','full','0.1','0.3'):
    st=observed(run,mode);a=scores(run['actions'],st);b=scores(changed,st)
    for aa,bb in zip(a,b):
     for pair in aa:self.assertAlmostEqual(aa[pair],bb[pair],places=12)
 def test_factorial_actual_prompt_construction(self):
  d=json.loads((ROOT/'results/edge0-local/prompt-factorial.json').read_text());self.assertTrue(d['complete']);self.assertEqual(len(d['records']),720)
  self.assertTrue(all(r['strict_valid'] for r in d['records']))
  repeated=[r for r in d['records'] if r['arm']=='quoted_relational'];self.assertEqual(len(repeated),180);self.assertTrue(all(r['action']==r['original_action'] for r in repeated))

if __name__=='__main__':unittest.main()
