"""Reanalyse preserved fresh-run evidence, no inference or network calls."""
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/permutation/runs.csv'

def wilson(k, n):
    z = 1.959963984540054
    den = 1 + z*z/n
    center = (k/n + z*z/(2*n))/den
    half = z*math.sqrt((k/n)*(1-k/n)/n + z*z/(4*n*n))/den
    return [max(0, center-half), min(1, center+half)]

def main():
    rows = list(csv.DictReader(SOURCE.open(encoding='utf-8')))
    keys = [(r['condition'], r['seed'], r['observed_context'], r['method']) for r in rows]
    assert len(rows) == len(set(keys)) == 3200
    groups = defaultdict(list)
    for r in rows:
        groups[r['condition'],r['observed_context'],r['method']].append(r)
    cells = []
    for (condition, view, method), rs in sorted(groups.items()):
        n = len(rs)
        assert n == 100
        orig = [float(r['max_score']) > float(r['threshold']) for r in rs] # replaced below: original thresholds are in metadata
        meta = json.loads((ROOT/'results/permutation/metadata.json').read_text())
        threshold = meta['original_thresholds'][str((view, method))]
        orig = [float(r['max_score']) > threshold for r in rs]
        perm = [r['any_alarm'].lower() == 'true' for r in rs]
        p_reject = [float(r['perm_p_value']) <= .05 for r in rs]
        k = sum(perm)
        lost = sum(a and not b for a,b in zip(orig,perm))
        gained = sum(b and not a for a,b in zip(orig,perm))
        m = lost+gained
        p = min(1., 2*sum(math.comb(m,i) for i in range(min(lost,gained)+1))/2**m) if m else 1.
        cells.append(dict(condition=condition,view=view,method=method,n=n,original_alarms=sum(orig),permutation_alarms=k,wilson95=wilson(k,n),original_only=lost,permutation_only=gained,paired_exact_mcnemar_p=p,p_rule_disagreements=sum(a!=b for a,b in zip(perm,p_reject))))
    # This is a paired comparison of the SAME run and view, not independent replicates.
    paired=[]
    lookup={k:r for k,r in zip(keys,rows)}
    for condition in sorted({r['condition'] for r in rows}):
        for view in ('none','full','0.1','0.3'):
            a=[lookup[condition,str(s),view,'cmi'] for s in range(100)]
            b=[lookup[condition,str(s),view,'net'] for s in range(100)]
            paired.append(dict(condition=condition,view=view,alarm_disagreements=sum(x['any_alarm']!=y['any_alarm'] for x,y in zip(a,b)),top1_disagreements=sum(x['top1_credit']!=y['top1_credit'] for x,y in zip(a,b))))
    result={'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'result_rows':len(rows),'cells':cells,'paired_methods':paired,'scope':'Reanalysis of existing scripted trajectories, not new experiments. Wilson intervals are marginal per cell. McNemar p-values are exploratory, unadjusted; no pooling across views.'}
    target=ROOT/'results/checkpoint-analysis.json'
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    for c in cells:
        if c['condition']=='benign' and c['view']=='full': print(json.dumps(c))
    print('ROW_COUNT',len(rows),'P_RULE_DISAGREEMENTS',sum(c['p_rule_disagreements'] for c in cells))
    print('PAIRED_METHODS',json.dumps(paired))
    print('SAVED',target)

if __name__=='__main__':
    main()
