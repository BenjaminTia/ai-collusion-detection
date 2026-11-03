"""Separate local Edge0 pilot. No downloads, cloud APIs or invented actions.
Frozen collection: four conditions, stateless greedy calls, source schedule;
48-decision smoke (3 rounds/condition), then only if manually approved 3x30 pilot.
No retries, no substituted actions. Invalid output aborts the run and is retained.
Thinking off, 64 output tokens, no grammar constraint. Full prompts/responses saved.
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import llm_protocol as P
URL='http://127.0.0.1:18080'
OUT=ROOT/'results/edge0-local'

def request(path,data=None):
    req=urllib.request.Request(URL+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def strict_action(raw):
    try:
        d=json.loads(raw)
        if isinstance(d,dict) and set(d)=={'action'} and d['action'] in P.ACTIONS:return d['action']
    except (ValueError,TypeError):pass
    return None

def collect(stage):
    OUT.mkdir(parents=True,exist_ok=True)
    assert request('/health')['status']=='ok'
    model=request('/v1/models')
    nr,nt=(1,3) if stage=='smoke' else ((1,30) if stage=='pilot-remainder' else (3,30))
    conditions=('seeded','combined') if stage=='pilot-remainder' else P.CONDITIONS
    indices=(2,) if stage=='pilot-remainder' else range(nr)
    result={'stage':stage,'model':'Edge0-8B-A1B-preview local Q4_1 + trained LoRA','api_model':model,'source_protocol_hash':P.prompt_fingerprint(),'collector_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'settings':{'temperature':0,'max_tokens':64,'enable_thinking':False,'retries':0,'fallback_actions':False},'records':[],'rounds':[],'runs':[],'complete':False}
    target=OUT/(stage+'.json')
    if target.exists():raise RuntimeError('Refusing to overwrite existing collection')
    start=time.monotonic()
    def save():
        result['elapsed_seconds']=time.monotonic()-start
        tmp=target.with_suffix('.writing');tmp.write_text(json.dumps(result,indent=2),encoding='utf-8');tmp.replace(target)
    try:
        for idx in indices:
            for condition in conditions:
                plan=P.plan_run(condition,idx,nt)
                for rnd in plan['rounds']:
                    if time.monotonic()-start>570:raise TimeoutError('570-second collection budget')
                    # Primary precedes assistant by schedule; other agents cannot see their prompts.
                    acts={}
                    for a in rnd['agents']:
                        message=None
                        if a['role']=='assistant':
                            primary=next(x for x in rnd['agents'] if x['role']=='primary')
                            message=P.seed_message(primary['name'],acts[primary['agent']])
                            assert P.ACTION_NAME[message['primary_action']] in message['text']
                        prompt=P.build_prompt(a['name'],a['cue'],a['recommendation'],a['team_follow_cue'],message)
                        body={'model':'apart-edge0-8b','messages':[{'role':'system','content':P.SYSTEM_PROMPT},{'role':'user','content':prompt}],'temperature':0,'seed':42,'max_tokens':64,'chat_template_kwargs':{'enable_thinking':False},'cache_prompt':True}
                        t=time.monotonic();response=request('/v1/chat/completions',body)
                        raw=response['choices'][0]['message'].get('content','')
                        action=strict_action(raw)
                        rec={'condition':condition,'run_index':idx,'round':rnd['round'],'agent':a['agent'],'role':a['role'],'cue':a['cue'],'recommendation':a['recommendation'],'prompt':prompt,'message':message,'response':response,'raw_output':raw,'action':action,'strict_valid':action is not None,'latency_seconds':time.monotonic()-t}
                        result['records'].append(rec)
                        if action is None:
                            save();raise ValueError('Invalid actual model output; no replacement')
                        acts[a['agent']]=action
                    actions=[acts[i] for i in range(4)]
                    result['rounds'].append({'condition':condition,'run_index':idx,'round':rnd['round'],'cue':rnd['cue'],'actions':''.join(actions),'payoffs':P.payoff(actions),'pair':list(plan['pair']),'cue_pair':list(plan['cue_pair'])})
                result['runs'].append({'condition':condition,'run_index':idx,'seed':plan['seed'],'rounds_completed':nt})
                save();print(condition,idx,'rounds',nt,'seconds',round(time.monotonic()-start,1),flush=True)
        assert len(result['records'])==len(indices)*nt*4*len(conditions)
        result['complete']=True
    except BaseException as exc:
        result['error']=repr(exc);raise
    finally:save()
    print('COMPLETE',len(result['records']),'decisions',len(result['rounds']),'rounds',target,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=('smoke','pilot','pilot-remainder'),default='smoke');args=parser.parse_args();collect(args.stage)
