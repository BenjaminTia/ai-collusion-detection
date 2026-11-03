"""Paired diagnostic ablation AFTER the exploratory pilot, not preregistered.
Replay all 180 seeded/combined assistant decisions with only the private message
removed. Keep recommendation, public cue, role name, decoding and seed identical.
Save every actual response; no action substitution. This measures message effect,
not intent, harm, or independent replication of the original trajectories.
"""
import json,time
from pathlib import Path
import edge0_pilot as E
import llm_protocol as P

D=E.OUT
a=json.loads((D/'pilot.json').read_text());b=json.loads((D/'pilot-remainder.json').read_text())
records=a['records']+b['records']
source=[r for r in records if r['role']=='assistant']
assert len(source)==180
out={'label':'post-pilot paired message-removal diagnostic','records':[],'complete':False}
target=D/'message-ablation.json'
if target.exists():raise RuntimeError('Existing ablation preserved')
t=time.monotonic()
try:
 for r in source:
    if time.monotonic()-t>150:raise TimeoutError('150s ablation budget')
    plan=P.plan_run(r['condition'],r['run_index'],30)
    agent=plan['rounds'][r['round']]['agents'][r['agent']]
    prompt=P.build_prompt(agent['name'],agent['cue'],agent['recommendation'],agent['team_follow_cue'],None)
    body={'model':'apart-edge0-8b','messages':[{'role':'system','content':P.SYSTEM_PROMPT},{'role':'user','content':prompt}],'temperature':0,'seed':42,'max_tokens':64,'chat_template_kwargs':{'enable_thinking':False},'cache_prompt':True}
    resp=E.request('/v1/chat/completions',body)
    raw=resp['choices'][0]['message'].get('content','');action=E.strict_action(raw)
    out['records'].append({'condition':r['condition'],'run_index':r['run_index'],'round':r['round'],'agent':r['agent'],'prompt_without_message':prompt,'response':resp,'action_without_message':action,'action_with_message':r['action'],'primary_action':r['message']['primary_action'],'recommendation':r['recommendation']})
    if action is None:raise ValueError('Invalid ablation output retained')
    if len(out['records'])%30==0:
        target.write_text(json.dumps(out,indent=2),encoding='utf-8');print('saved',len(out['records']),flush=True)
 out['complete']=True
finally:
 out['seconds']=time.monotonic()-t;target.write_text(json.dumps(out,indent=2),encoding='utf-8')
print('COMPLETE',len(out['records']),out['seconds'])
