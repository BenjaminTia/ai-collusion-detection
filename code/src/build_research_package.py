"""Build an author-facing evidence package from executed artifacts only.
Requires all held-out cells and final regression results. No inference/network.
"""
import hashlib,html,json,math,statistics,zipfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from docx import Document
from docx.shared import Inches,Pt
import fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'submission';FIG=OUT/'figures'
TITLE='When Dependence Misleads: Context and Treatment Checks for AI Coordination Audits'

def j(rel):return json.loads((ROOT/rel).read_text(encoding='utf-8'))
def mean_sd(v):return f'{statistics.mean(v):.3f} (SD {statistics.stdev(v):.3f})' if len(v)>1 else str(v[0])
def count_pair(k,n):return f'{k}/{n}' if n else 'N/A'

def main():
 held=j('results/heldout/analysis.json');fac=j('results/edge0-local/prompt-factorial-analysis.json');cross=j('results/context-crossover/results.json')
 assert held['decisions']==2880 and held['counterfactual_decisions']==360
 regression=(ROOT/'results/final-regression-package.log').read_text(encoding='utf-8')
 assert '\nOK' in regression and 'FAILED (' not in regression
 OUT.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 # Figure 1: each point is a mean across 50 preserved trajectories, not a new replication.
 fig,ax=plt.subplots(figsize=(7.1,2.9),layout='constrained')
 for meth,mark in [('cmi','o'),('net','x')]:
  rs=[r for r in cross['summary'] if r['method']==meth]
  ax.plot([100*r['error'] for r in rs],[r['mean_top1_credit'] for r in rs],marker=mark,label=meth.upper())
 ax.axvline(100*cross['population_crossover_error'],ls='--',color='#bb5533',label='Population crossover (18.8%)')
 ax.set(xlabel='Auditor cue corruption (%)',ylabel='Assigned-pair top-rank credit',ylim=(-.03,1.05));ax.legend(fontsize=8)
 fig.savefig(FIG/'01-context.png',dpi=200);fig.savefig(FIG/'01-context.pdf');plt.close(fig)
 # Figure 2: six run-cluster outcomes, not independent-binomial intervals.
 fig,ax=plt.subplots(figsize=(7.1,2.9),layout='constrained');labels=['Quoted\nrelational','Quoted\nexplicit','Priority\nrelational','Priority\nexplicit']
 for i,s in enumerate(fac['summaries']):
  ys=[r['desired']/r['n'] for r in s['per_run']]
  ax.bar(i,s['desired']/s['n'],color=['#71879c','#6c9daa','#c68c64','#39805b'][i],alpha=.7)
  ax.scatter([i+(k-2.5)*.035 for k in range(len(ys))],ys,s=15,c='black',zorder=3)
 ax.set(xticks=range(4),xticklabels=labels,ylabel='Intended-action compliance',ylim=(0,1.08));fig.savefig(FIG/'02-prompts.png',dpi=200);fig.savefig(FIG/'02-prompts.pdf');plt.close(fig)
 # Figure 3: run-level detector identification, three trajectories per cell.
 fig,ax=plt.subplots(figsize=(7.1,2.9),layout='constrained');views=['none','full','0.1','0.3']
 for method,offset,col in [('cmi',-.06,'#2b7097'),('net',.06,'#b26038')]:
  ys=[]
  for v in views:
   rs=[r['top1_credit'] for r in held['detectors'] if r['condition']=='combined' and r['view']==v and r['method']==method]
   ys.append(statistics.mean(rs));ax.scatter([views.index(v)+offset]*3,rs,c=col,s=18,alpha=.7)
  ax.plot([i+offset for i in range(4)],ys,c=col,label=method.upper())
 ax.set(xticks=range(4),xticklabels=['Omitted','Full','10% error','30% error'],ylabel='Held-out assigned-pair top-rank credit',ylim=(-.04,1.06));ax.legend();fig.savefig(FIG/'03-heldout.png',dpi=200);fig.savefig(FIG/'03-heldout.pdf');plt.close(fig)
 summaries={s['condition']:s for s in held['summary']}
 seed=summaries['seeded'];combo=summaries['combined'];ben=summaries['benign']
 # Preserve an abstract candidate as a source-grounded authoring aid; not approved final prose.
 abstract=('An information-theoretic alarm can detect dependence without establishing intentional coordination. '
 'We audit this distinction using controlled categorical games and real local language-model outputs. '
 'A scripted common-cause construction yields a population ranking crossover near 18.8 percent auditor-context corruption, '
 'and fresh simulations exhibit the predicted transition. A separate language-model pilot reveals that delivered private requests '
 'need not change actions. Paired message-removal replay and a four-arm prompt intervention separate nonresponse, '
 'incorrect action mapping, and successful instructed coordination. We then evaluate the selected treatment on fresh held-out schedules, '
 'preserving all raw outputs and reporting trajectory-level results. The study demonstrates why auditing requires distinct checks '
 'for context adequacy, behavioural influence, and mapping compliance. Its scope is one quantized model and an artificial stateless game; '
 'it does not establish spontaneous coordination, harmful collusion, general detector reliability, or superiority over existing methods. '
 'We provide an author-facing evidence package with reproducible analyses and explicit limitations for practical auditing.')
 words=abstract.split()
 # Word count is stated mechanically; don't silently pad an abstract to satisfy conflicting rules.
 abstract_meta={'candidate_words':len(words),'guidelines_limit':150,'template_range':[150,250],'status':'Author revision needed; source discrepancy requires exactly 150 words for practical intersection'}
 (OUT/'abstract-candidate.md').write_text(abstract+'\n\nWord count: '+str(len(words))+'\nAI-assisted candidate for author revision, not an approved submission abstract.\n',encoding='utf-8')
 (OUT/'abstract-count.json').write_text(json.dumps(abstract_meta,indent=2))
 # A document model drives the Markdown, official-template DOCX and technical PDF.
 pages=[]
 pages.append([
 ('title',TITLE),('p','AI-assisted technical evidence draft. Prepared for Benjamin Harris Chen Tia, Hong Kong Metropolitan University. Not author-approved and not submitted.'),
 ('h','Abstract candidate'),('p',abstract),
 ('h','1. Introduction'),('p','A detector may correctly find statistical dependence yet provide weak evidence of intentional or harmful collusion. We study two failure modes in a controlled four-agent setting: common context can dominate a seeded pair, and an assigned coordination instruction can fail to change behaviour or elicit the wrong policy. The output is a limited evaluation protocol, not a new state-of-the-art detector.'),
 ('h','2. Related work and contribution boundary'),('p','Bonjour, Aggarwal and Bhargava introduced information-theoretic collusion detection in discrete and partially observable games.[1] We implement a restricted common-observed-state CMI/net screen, not their full sequential method. The overlapping Raj-Taware repository already reports calibration failures, permutation tests and LLM experiments.[2] Those results are author-reported, not reproduced here. We do not claim first application, first calibration repair, or priority. Our specific evidence is the controlled context-corruption crossover and the separation of message delivery, behavioural influence and correct policy execution.')])
 pages.append([
 ('h','3. Methods: context and calibration'),('p','Four players choose R/P/S. Four conditions separate independent recommendations, two benign public-cue followers, a privately instructed pair, and their combination. Choices are stateless, without conversation history. Categorical CMI uses natural logs; the net screen subtracts the largest competing pair dependence in each direction and takes the minimum. Pair rankings award fractional credit on ties.'),
 ('p','For each run, 199 independent within-recorded-state column permutations preserve conditional marginals and calibrate the maximum of six pair scores, separately per method/view. Decisions strictly exceed the higher empirical 95th percentile, floored at zero. This targets the complete conditional-independence null under within-state exchangeability, not intent or strong innocent-pair control under arbitrary alternatives. Paired auditor views reuse actions.'),
 ('h','4. Scripted mechanism results'),('p','Fresh calibration-transfer evaluation used 100 runs per condition and 1,000 rounds/run. In benign/full-context data, original net thresholds alarmed on 39/100 runs versus 4/100 with per-run permutations. CMI changed from 1/100 to 4/100, so the result is not a uniform improvement. The marginal Wilson interval for 4/100 is 1.57%-9.84%; it does not prove population error at or below 5%.'),
 ('img','01-context.png'),('caption','Figure 1. Fresh scripted mechanism check: 50 trajectories, 1,000 rounds each, same actions under eight corruption views. Points are trajectory-mean ranking credit. At coupling probability 0.8, seeded-pair population CMI is 0.6135 nats. Benign residual H(S|observed S) crosses it at 18.795%, predicting a ranking change, not an exact finite-sample alarm threshold. The CMI and net curves coincide here.')])
 pages.append([
 ('h','5. Real local-model exploration'),('p','The experimental model was Edge0-8B-A1B-preview, locally converted Q4_1 plus its trained LoRA on an RTX 4050 laptop. The model card describes a preview and limited agent capability.[3] Its authors\' quality claims are not independently reproduced. GPT-6.1 Sol assisted study design, implementation, analysis and review; experimental action outputs were generated by Edge0. Model/adapter hashes and full generation settings are included. Greedy decoding used seed 42, 64 output-token cap and thinking disabled; no retries, grammar constraints or synthetic actions.'),
 ('p','A 48-decision smoke preceded 1,440 pilot decisions across 12 trajectories, 30 rounds each. Every pilot output was exact action-only JSON. Public instructions were followed in 360/360 decisions. Private mapping matches were 18/90 (seeded) and 39/90 (combined). Removing the private-message paragraph in 180 actual replays changed zero actions: matching the target had not shown an effect of the request.'),
 ('img','02-prompts.png'),('caption','Figure 2. Exploratory four-arm intervention on the same 180 assistant situations, nested in six source trajectories. Bars pool descriptive compliance; dots show six run-cluster proportions. Quoted relational: 57/180; quoted explicit: 62/180; priority relational: 9/180; priority explicit: 180/180. In the priority-relational arm, outputs copied the primary in 160/180 cases, usually failing the intended mapping. These edits bundle wording, priority and task-framing changes.'),
 ('p','The repeated original arm reproduced all 180 prior actions after a server restart. Each factorial output was valid JSON. Only the last arm supplied the intended mapping in all 123 recommendation-conflict cases. This prompted a fresh-schedule holdout; it was not a preregistered discovery or evidence of spontaneous/harmful collusion.')])
 htext=[]
 for c in ('independent','benign','seeded','combined'):
  s=summaries[c]
  htext.append(f"{c}: valid {count_pair(s['strict_valid'],s['decisions'])}; cue {count_pair(s['cue_followed'],s['cue_n'])}; mapping {count_pair(s['message_followed'],s['message_n'])}; baseline matches {count_pair(s['no_message_target_matches'],s['counterfactual_n'])}; action changes {count_pair(s['message_changed_action'],s['counterfactual_n'])}.")
 for c in ('seeded','combined'):
  rr=[r for r in held['cells'] if r['condition']==c]
  htext.append(c+' per-run intended-action counts: '+', '.join(str(r['message_followed'])+'/60' for r in rr)+'.')
 pages.append([
 ('h','6. Frozen fresh-schedule follow-up'),('p','The within-project protocol was written before collecting this follow-up. Twelve fresh schedules (3/condition), 60 rounds each, produced 2,880 model decisions and 360 real assistant counterfactual decisions. Every cell was required, with no outcome-selected exclusions. Fresh seed rules, collector/protocol hashes and complete raw records are preserved. The selected treatment names the actual primary and exact target action, then gives the priority instruction. The no-message baseline omits both the message and priority sentence: this is a bundled-treatment contrast, not a private-information-only effect.'),
 *[('p',t) for t in htext],
 ('p','Both detectors alarmed in 0/3 independent-control runs under every view. In benign controls, they alarmed in 3/3 runs with omitted or corrupted context and 0/3 with full context. In combined runs, mean assigned-pair top-rank credit rose from 1/3 with context omitted to 1 with full context. Combined runs still alarmed in every view: context improved pair identification, not overall alarm suppression. These are observed three-run outcomes, not population error guarantees. The LLM treatment is nearly deterministic, unlike the scripted coupling probability of 0.8; the 18.8% scripted crossover is not a claimed LLM threshold.'),
 ('img','03-heldout.png'),('caption','Figure 3. Held-out combined-condition assigned-pair top-rank credit under paired auditor views. Three trajectory points per method/view, with means connected. Rounds, pairs and views are not independent trajectory replicates. These detector results are descriptive; three runs/cell cannot validate a general error-rate guarantee.'),
 ('p','The model and prompts remain selected after exploration. The follow-up tests fresh schedules, not a second model or a fresh task distribution. Repeated finite categorical situations can occur even when complete schedules differ. Per-run maximum detector scores, thresholds, Monte Carlo p-values and ranking credits are in results/heldout/analysis.json and detector-runs.csv.')])
 pages.append([
 ('h','7. Discussion and practical use'),('p','Use three explicit gates before a collusion claim: adequate recorded common context; evidence that the coordination treatment changed behaviour; and evidence that the resulting policy matches the intended intervention. Add a separate competitive-harm assessment before using the term harmful collusion. The context example and prompt interventions show why these gates differ. They do not establish that any particular field deployment is colluding.'),
 ('p','The fixed-other-actions payoff reconstruction does not support a harm claim: mean outsider payoff changes were +0.061 per player/round in seeded runs and +0.156 in combined runs, relative to replacing the assistant action with its actual no-message response. These descriptive improvements in the toy payoff function are not equilibrium or real-world welfare estimates.'),
 ('h','Appendix A. Limitations and Dual-Use / Ethical Considerations'),('p','One quantized preview model, greedy decoding, three held-out schedules per condition and a deliberately artificial stateless game limit transfer. No adversarial economics, hidden-channel emergence or adaptive long-horizon play was established. The detector randomization assumes exchangeability and complete conditional independence within state; it is not a causal-intent test. The observed action/payoff interventions are fixed-other-actions comparisons, not counterfactual equilibria. Harm remains unestablished, not disproved.'),
 ('p','False accusations may lead to unjustified sanctions. Conversely, making coordination instructions more effective could lower barriers to coordinating agents. This package therefore documents a toy evaluation and its limitations, not operational advice for covert real-world collusion. Do not use alarms alone for consequential decisions.'),
 ('h','Reproducibility and provenance'),('p','All substantive counts are computed from saved raw artifacts. Analysis scripts rebuild the figures without a GPU. Model weights and private credentials are not distributed in the evidence ZIP. The initial pilot was interrupted after 10 saved trajectories; two remaining runs were collected separately with unchanged prompts/settings. The old blocked Modal/Qwen attempts are historical failures, not successful experimental evidence. The held-out supervisor owns and stops its local server; its final status is included.'),
 ('h','LLM usage and author approval'),('p','GPT-6.1 Sol substantially assisted design, code, analysis, critique and this technical draft. Experimental actions came from Edge0. This is not an author-approved final report. Apart requires the team to own its writing; Benjamin must author/revise and approve the final narrative and disclosure before manually submitting.[4][5] A local artifact does not prove a public repository or portal submission.'),
 ('h','References')])
 refs=json.loads((ROOT/'sources/citation-ledger.json').read_text())['sources']
 names={1:'Bonjour, T., Aggarwal, V., & Bhargava, B. (2022). Information theoretic approach to detect collusion in multi-agent games. UAI, PMLR 180, 223-232.',2:'Raj-Taware. Collusion-net-influence. Public repository; author-reported concurrent/overlapping work, retrieved during this study.',3:'Edge0. Edge0-8B-A1B-preview model card. Preview release; runtime/conversion differs from the advertised MLX path.',4:'Apart Research. AI Collusion Research Sprint, October 2026. Guidelines and judging rubric.',5:'Apart Research. Official report template linked from the sprint Guidelines.'}
 for r in refs:pages[-1].append(('ref',f"[{r['id']}] {names[r['id']]} {r['url']}"))
 # Plain Markdown author draft.
 md=[]
 for page in pages:
  for kind,text in page:
   if kind=='title':md+=['# '+text,'']
   elif kind=='h':md+=['## '+text,'']
   elif kind=='img':md+=['![](figures/'+text+')','']
   else:md+=[text,'']
 md+=['## Sources','']+[f"[{r['id']}] {r['url']}" for r in refs]+['']
 (OUT/'technical-evidence-draft.md').write_text('\n'.join(md),encoding='utf-8')
 # DOCX: use actual official template package and retain its section dimensions.
 doc=Document(ROOT/'sources/official-template.docx')
 for child in list(doc._element.body):
  if child.tag.endswith('}sectPr'):continue
  doc._element.body.remove(child)
 normal=doc.styles['Normal'];normal.font.name='Arial';normal.font.size=Pt(10)
 for pi,page in enumerate(pages):
  if pi:doc.add_page_break()
  for kind,text in page:
   if kind=='title':doc.add_heading(text,0)
   elif kind=='h':doc.add_heading(text,2)
   elif kind=='img':doc.add_picture(str(FIG/text),width=Inches(6.1))
   else:doc.add_paragraph(text)
 doc.save(OUT/'technical-evidence-draft.docx')
 # Readable technical PDF, clearly labelled, not a claim of official final format.
 pdfmetrics.registerFont(TTFont('ArialEvidence','C:/Windows/Fonts/arial.ttf'))
 pdfmetrics.registerFont(TTFont('ArialEvidenceBold','C:/Windows/Fonts/arialbd.ttf'))
 styles=getSampleStyleSheet();styles.add(ParagraphStyle('BodyEvidence',fontName='ArialEvidence',fontSize=9,leading=12,spaceAfter=7));styles.add(ParagraphStyle('HeadEvidence',fontName='ArialEvidenceBold',fontSize=11,leading=14,spaceBefore=8,spaceAfter=6));styles.add(ParagraphStyle('SmallEvidence',fontName='ArialEvidence',fontSize=7.5,leading=10,spaceAfter=5));styles.add(ParagraphStyle('TitleEvidence',fontName='ArialEvidenceBold',fontSize=17,leading=20,spaceAfter=10))
 story=[]
 for pi,page in enumerate(pages):
  if pi:story.append(PageBreak())
  for kind,text in page:
   if kind=='img':story.append(Image(str(FIG/text),width=468,height=191));continue
   style=styles['TitleEvidence' if kind=='title' else 'HeadEvidence' if kind=='h' else 'SmallEvidence' if kind in ('caption','ref') else 'BodyEvidence']
   story.append(Paragraph(html.escape(text),style))
 def footer(c,doc):
  c.setFont('ArialEvidence',7);c.drawString(48,27,'AI-assisted evidence draft: author revision required, not submitted');c.drawRightString(564,27,str(doc.page))
 pdf=OUT/'technical-evidence-draft.pdf'
 SimpleDocTemplate(str(pdf),pagesize=(612,792),rightMargin=48,leftMargin=48,topMargin=40,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
 # Verify text layer, pages, all blocks bounded inside page, and required disclosure.
 f=fitz.open(pdf);assert 4<=len(f)<=8
 text='\n'.join(p.get_text() for p in f)
 assert '2880' in text.replace(',','') and 'Dual-Use' in text and 'not submitted' in text
 clipped=[]
 for pi,page in enumerate(f):
  for block in page.get_text('blocks'):
   if block[0]<0 or block[1]<0 or block[2]>page.rect.width+1 or block[3]>page.rect.height+1:clipped.append((pi,block[:4]))
 assert not clipped,clipped
 receipt={'pdf_pages':len(f),'pdf_text_characters':len(text),'out_of_page_text_blocks':0,'abstract_candidate_words':len(words),'heldout_decisions':held['decisions'],'counterfactual_decisions':held['counterfactual_decisions'],'author_approval_required':True,'submitted':False}
 f.close()
 (OUT/'document-verification.json').write_text(json.dumps(receipt,indent=2))
 # Evidence zip: explicit directories/extensions, no weights/cache/credentials or failed downloads.
 selected=[]
 for folder in ('src','tests','llm','protocol','paper','reviews','sources'):
  for p in (ROOT/folder).rglob('*'):
   if p.is_file() and p.suffix in ('.py','.md','.json','.csv','.pdf','.docx') and '__pycache__' not in p.parts and '.bak' not in p.name and 'query' not in p.name:selected.append(p)
 selected.extend([ROOT/'llm_protocol.py',ROOT/'README.md'])
 for folder in ('results/scripted','results/diagnosis','results/permutation','results/context-crossover','results/edge0-local','results/heldout'):
  for p in (ROOT/folder).rglob('*'):
   if p.is_file() and p.suffix in ('.json','.jsonl','.csv','.md'):selected.append(p)
 selected.extend([ROOT/'results/final-regression.log',ROOT/'results/final-regression-package.log'])
 selected +=[p for p in OUT.rglob('*') if p.is_file() and p.suffix in ('.md','.json','.pdf','.docx','.png') and p.name!='package-manifest.json']
 selected=sorted(set(selected))
 manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in selected]
 (OUT/'package-manifest.json').write_text(json.dumps(manifest,indent=2))
 zpath=OUT/'research-evidence-package.zip'
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in selected:z.write(p,p.relative_to(ROOT).as_posix())
  z.write(OUT/'package-manifest.json','submission/package-manifest.json')
 with zipfile.ZipFile(zpath) as z:
  assert z.testzip() is None
  assert len(z.namelist())==len(manifest)+1
  for m in manifest:assert hashlib.sha256(z.read(m['path'])).hexdigest()==m['sha256']
 print(json.dumps({**receipt,'zip':str(zpath),'zip_members':len(manifest)+1,'zip_bytes':zpath.stat().st_size},indent=2))

if __name__=='__main__':main()
