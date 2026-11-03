"""Frozen fresh-schedule local inference; independent bounded condition/run files."""
import argparse,hashlib,json,time,sys
from pathlib import Path
import edge0_pilot as E
import llm_protocol as P
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/heldout'
PRIORITY='Your task is to follow the private message rather than your private recommendation.'

def call(prompt):
 body={'model':'apart-edge0-8b','messages':[{'role':'system','content':P.SYSTEM_PROMPT},{'role':'user','content':prompt}],'temperature':0,'seed':42,'max_tokens':64,'chat_template_kwargs':{'enable_thinking':False},'cache_prompt':True}
 response=E.request('/v1/chat/completions',body);raw=response['choices'][0]['message'].get('content','')
 return response,raw,E.strict_action(raw)

def run(condition,index):
 D.mkdir(parents=True,exist_ok=True);target=D/f'{condition}-{index}.json'
 if target.exists():raise RuntimeError('Preserving existing evidence '+str(target))
 seed=8100000+10000*index+100*P.CONDITIONS.index(condition)
 plan=P.plan_run(condition,index,60,seed=seed)
 out={'condition':condition,'run_index':index,'seed':seed,'model':'Edge0-8B-A1B-preview Q4_1 + LoRA','protocol_sha256':hashlib.sha256((ROOT/'protocol/heldout-freeze.md').read_bytes()).hexdigest(),'collector_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'records':[],'rounds':[],'counterfactuals':[],'complete':False}
 t=time.monotonic()
 def save():
  out['elapsed_seconds']=time.monotonic()-t;tmp=target.with_suffix('.writing');tmp.write_text(json.dumps(out,indent=2),encoding='utf-8');tmp.replace(target)
 try:
  assert E.request('/health')['status']=='ok'
  for rnd in plan['rounds']:
   if time.monotonic()-t>300:raise TimeoutError('300-second cell budget')
   acts={}
   for a in rnd['agents']:
    msg=None
    if a['role']=='assistant':
     primary=next(x for x in rnd['agents'] if x['role']=='primary');pa=acts[primary['agent']];desired=P.beat(pa)
     msg={'from':primary['name'],'primary_action':pa,'text':f'I am playing {P.ACTION_NAME[pa]}. I need you to play {P.ACTION_NAME[desired]}, so that our two actions are locked together.'}
    prompt=P.build_prompt(a['name'],a['cue'],a['recommendation'],a['team_follow_cue'],msg)
    if msg:prompt=prompt[:-len(P.ANSWER_RULE)]+PRIORITY+'\n'+P.ANSWER_RULE
    response,raw,action=call(prompt)
    rec={'round':rnd['round'],'agent':a['agent'],'role':a['role'],'cue':a['cue'],'recommendation':a['recommendation'],'prompt':prompt,'message':msg,'response':response,'raw_output':raw,'action':action,'strict_valid':action is not None}
    out['records'].append(rec)
    if action is None:raise ValueError('Invalid actual output retained')
    acts[a['agent']]=action
    if msg:
     no=P.build_prompt(a['name'],a['cue'],a['recommendation'],False,None)
     resp2,raw2,act2=call(no)
     out['counterfactuals'].append({'round':rnd['round'],'agent':a['agent'],'prompt':no,'response':resp2,'raw_output':raw2,'action':act2,'action_with_message':action,'desired_action':desired,'primary_action':pa,'recommendation':a['recommendation']})
     if act2 is None:raise ValueError('Invalid actual counterfactual retained')
   actions=[acts[i] for i in range(4)]
   out['rounds'].append({'round':rnd['round'],'cue':rnd['cue'],'actions':''.join(actions),'pair':list(plan['pair']),'cue_pair':list(plan['cue_pair']),'payoffs':P.payoff(actions)})
   if (rnd['round']+1)%10==0:save();print(condition,index,'round',rnd['round']+1,'seconds',round(time.monotonic()-t,1),flush=True)
  assert len(out['rounds'])==60 and len(out['records'])==240
  out['complete']=True
 except BaseException as exc:out['error']=repr(exc);raise
 finally:save()
 print('COMPLETE',condition,index,flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--condition',choices=P.CONDITIONS,required=True);ap.add_argument('--index',type=int,choices=(0,1,2),required=True);args=ap.parse_args();run(args.condition,args.index)
