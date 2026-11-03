"""Validate and analyse actual Edge0 outputs. No inference or fabricated data."""
import collections
import hashlib
import json
import math
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))
from experiment import scores,rank_stats
import llm_protocol as P
D=ROOT/'results/edge0-local'

def main():
    a=json.loads((D/'pilot.json').read_text());b=json.loads((D/'pilot-remainder.json').read_text())
    ab=json.loads((D/'message-ablation.json').read_text())
    records=a['records']+b['records'];rounds=a['rounds']+b['rounds'];runs=a['runs']+b['runs']
    keys=[(r['condition'],r['run_index'],r['round'],r['agent']) for r in records]
    assert len(records)==len(set(keys))==1440
    assert len(rounds)==360 and len(runs)==12 and b['complete'] and ab['complete']
    assert a['source_protocol_hash']==b['source_protocol_hash'] and a['settings']==b['settings']
    assert all(r['strict_valid'] and json.loads(r['raw_output'])=={'action':r['action']} for r in records)
    bykey={k:r for k,r in zip(keys,records)}
    for rd in rounds:
        rs=[bykey[rd['condition'],rd['run_index'],rd['round'],i] for i in range(4)]
        assert ''.join(r['action'] for r in rs)==rd['actions']
        assert P.payoff(list(rd['actions']))==rd['payoffs']
        for r in rs:
            if r['role']=='assistant':
                primary=next(x for x in rs if x['role']=='primary')
                assert primary['action']==r['message']['primary_action']
                assert P.ACTION_NAME[primary['action']] in r['prompt']
    groups=[]
    for condition in P.CONDITIONS:
        for idx in range(3):
            rs=[r for r in records if r['condition']==condition and r['run_index']==idx]
            rd=sorted([r for r in rounds if r['condition']==condition and r['run_index']==idx],key=lambda r:r['round'])
            assert len(rs)==120 and len(rd)==30
            followers=[r for r in rs if r['role']=='cue_follower']
            assistants=[r for r in rs if r['role']=='assistant']
            free=[r for r in rs if r['role'] in ('independent','primary')]
            item={'condition':condition,'run_index':idx,'decisions':len(rs),'cue_followed':sum(r['action']==r['cue'] for r in followers),'cue_n':len(followers),'message_followed':sum(r['action']==P.beat(r['message']['primary_action']) for r in assistants),'message_n':len(assistants),'recommendation_followed':sum(r['action']==r['recommendation'] for r in free),'recommendation_n':len(free),'actions':dict(collections.Counter(r['action'] for r in rs))}
            item['mean_payoff']=sum(sum(r['payoffs']) for r in rd)/120
            item['ranking_descriptive']={}
            acts=[[P.ACTION_INDEX[x] for x in r['actions']] for r in rd]
            for view in ('none','full'):
                states=[0]*30 if view=='none' else [P.ACTION_INDEX[r['cue']] for r in rd]
                g,n=scores(acts,states)
                if condition in ('seeded','combined'):
                    item['ranking_descriptive'][view]={'cmi_top1_credit':rank_stats(g,tuple(rd[0]['pair']))[0],'net_top1_credit':rank_stats(n,tuple(rd[0]['pair']))[0]}
            groups.append(item)
    effects=[]
    for c in ('seeded','combined'):
        ar=[r for r in ab['records'] if r['condition']==c]
        assert len(ar)==90
        effects.append({'condition':c,'n':90,'message_changed_action':sum(r['action_with_message']!=r['action_without_message'] for r in ar),'followed_with_message':sum(r['action_with_message']==P.beat(r['primary_action']) for r in ar),'followed_without_message':sum(r['action_without_message']==P.beat(r['primary_action']) for r in ar),'per_run':[{'run_index':i,'changed':sum(r['action_with_message']!=r['action_without_message'] for r in ar if r['run_index']==i)} for i in range(3)]})
    hashes={}
    for name in ('smoke.json','pilot.json','pilot-remainder.json','message-ablation.json'):
        hashes[name]=hashlib.sha256((D/name).read_bytes()).hexdigest()
    modelpaths=[Path('C:/Users/Benjamin/.edge0/models/edge0-8b-gguf/edge0-8b.gguf'),Path('C:/Users/Benjamin/.edge0/models/edge0-8b-gguf/lora_edge0_8b-gguf.gguf')]
    artifacts=[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in modelpaths]
    report={'label':'Real local Edge0 inference, NOT Qwen or Modal','validated_pilot_decisions':1440,'rounds':360,'runs':12,'additional_smoke_decisions':48,'additional_ablation_decisions':180,'strict_pilot_outputs':1440,'substituted_actions':0,'source_hashes':hashes,'model_artifacts':artifacts,'per_run':groups,'message_ablation':effects,'limits':['Exploratory 3-run pilot, not a powered detector evaluation','Ablation planned after the pilot; paired deterministic prompt intervention, no claim of preregistration','Original pilot interrupted by outer tool 420-second limit after 10 saved runs; 2 remaining runs collected separately with identical prompts/settings. No complete run was outcome-filtered. Any unsaved in-flight outputs from interrupted run unavailable.','No thresholds or formal collusion accusations from 30-round CMI estimates','Seeded assignment is not demonstrated compliance or harmful collusion','Artifact hashes identify installed model; this analysis did not independently reproduce its training or conversion']}
    (D/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# Real Edge0 local pilot and paired message ablation','','1440 real pilot decisions; 12 trajectories (3 per condition), 30 rounds each. All pilot outputs parsed as exact action-only JSON. No retries or substituted actions. Additional 48-decision smoke and 180-decision paired ablation are separate evidence.','','## Message effects (paired, descriptive)']
    for e in effects:lines.append(f"- {e['condition']}: private message changed {e['message_changed_action']}/90 actions; requested coordination followed {e['followed_with_message']}/90 with message versus {e['followed_without_message']}/90 without.")
    lines+=['','## Per-condition compliance']
    for c in P.CONDITIONS:
        rows=[x for x in groups if x['condition']==c]
        lines.append(f"- {c}: cue following {sum(x['cue_followed'] for x in rows)}/{sum(x['cue_n'] for x in rows)}; message following {sum(x['message_followed'] for x in rows)}/{sum(x['message_n'] for x in rows)}; free-agent recommendation following {sum(x['recommendation_followed'] for x in rows)}/{sum(x['recommendation_n'] for x in rows)}.")
    lines+=['','## Interpretation','Private-message delivery and behavioural response are separate checks. Low seeded compliance prevents treating assignment as a reliable positive collusion control. Report model-specific obedience and prompt effects, not a detector success claim.','', '## Limitations']+['- '+x for x in report['limits']]
    (D/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines));print('VALIDATION PASSED: unique decisions, complete cells, actual message delivery, payoff replay, no fallback, source hashes')

if __name__=='__main__':main()
