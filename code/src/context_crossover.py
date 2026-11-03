"""Predeclared mechanism check on NEW scripted seeds; no cloud/model calls.
50 trajectories, 1000 rounds, fixed coordination strength 0.8.
Use identical trajectories across corruption views. Descriptive ranking only,
no alarm calibration or significance tests. Not LLM evidence.
"""
import json
import math
from pathlib import Path
from experiment import simulate, observed, scores, rank_stats

ROOT=Path(__file__).resolve().parents[1]
ERRORS=(0., .10, .15, .18, .19, .20, .25, .30)

def entropy_error(e):
    return -(1-e)*math.log(1-e)-e*math.log(e/2) if e else 0.

def main():
    strength=.8
    p=strength+(1-strength)/3
    q=(1-strength)/3
    linked_mi=math.log(3)+p*math.log(p)+2*q*math.log(q)
    lo,hi=0.,2/3
    for _ in range(80):
        m=(lo+hi)/2
        if entropy_error(m)<linked_mi:lo=m
        else:hi=m
    rows=[]
    out=ROOT/'results/context-crossover'
    out.mkdir(parents=True,exist_ok=True)
    with (out/'trajectories.jsonl').open('w',encoding='utf-8') as f:
        for seed in range(50):
            run=simulate('combined',1000,9000000+seed,strength=strength)
            f.write(json.dumps({'seed':9000000+seed,**run})+'\n')
            for e in ERRORS:
                g,net=scores(run['actions'],observed(run,str(e)))
                for method,values in [('cmi',g),('net',net)]:
                    top,auc=rank_stats(values,run['pair'])
                    rows.append({'seed':9000000+seed,'error':e,'method':method,'top1_credit':top,'auc':auc})
    cells=[]
    for e in ERRORS:
        for method in ('cmi','net'):
            rs=[r for r in rows if r['error']==e and r['method']==method]
            assert len(rs)==50
            cells.append({'error':e,'method':method,'runs':50,'mean_top1_credit':sum(r['top1_credit'] for r in rs)/50,'population_benign_cmi':entropy_error(e),'population_seeded_cmi':linked_mi})
    result={'label':'NEW SCRIPTED MECHANISM CHECK, not LLM evidence','seeds':'9000000..9000049','rounds':1000,'strength':strength,'population_crossover_error':(lo+hi)/2,'interpretation':'In the population construction, all cross-pair CMI terms are zero, so net and CMI share the same top-ranking crossover. This is construction-specific, not a general equivalence theorem.','rows':rows,'summary':cells}
    (out/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('TRAJECTORIES',50,'RESULT_ROWS',len(rows),'CROSSOVER',(lo+hi)/2)
    for c in cells:print(c)

if __name__=='__main__':main()
