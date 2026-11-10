import json,yaml,re,collections,sys
sys.path.insert(0,'code')
from bench.schema import parse_reply
from bench.schema.pipeline import Scenario
from pipeline.store import Store
st=Store()
R=[json.loads(l) for l in open('results/transfer/build-batch2-20261109.jsonl')]
info={}   # flip id -> changed facts, changed considerations, case verdict as X1 option
def load(p): return Scenario.model_validate(yaml.safe_load(open(p))).case
for r in R:
    f=r.get('flip') or {}
    if r.get('bucket')=='accepted' and f.get('bucket')=='accepted':
        S=load(r['path']); F=load(f['path'])
        of={x.id:x.fact for x in S.facts}; ok={k.id:k for k in S.considerations}
        info[f['id']]=dict(chf=[x.id for x in F.facts if of.get(x.id)!=x.fact],
            chk=[k.id for k in F.considerations if k.id in ok and (k.weight!=ok[k.id].weight or set(k.favors)!=set(ok[k.id].favors))],
            wc=[w.id for w in F.flip_conditions.would_change])
def bucket(doc,ref_id):
    if not isinstance(doc,dict): return 'no_doc'
    for b in ('matched','corresponding'):
        for p in doc.get(b) or []:
            if ref_id in json.dumps(p): return b
    for p in doc.get('case_only') or []:
        if ref_id in json.dumps(p): return 'case_only'
    return 'unmentioned'
out=collections.defaultdict(collections.Counter)
rows=[]
for run,model in [('pilot2','granite'),('pilot2-luna','luna')]:
    for l in open(f'results/transfer/{run}/samples.jsonl'):
        r=json.loads(l)
        if r['phase'] not in ('flip','transfer'): continue
        raw=open(f'results/transfer/{run}/'+r['raw_path']).read()
        p=parse_reply(raw); s=p.steps
        v=s.get('verdict') or {}; rel=v.get('relation'); via=v.get('via')
        key=(model,r['phase'])
        c=out[key]; c['n']+=1
        c['rel:'+str(rel)]+=1
        c['correct']+= (r['correct']==1)
        if r['phase']=='flip':
            inf=info.get(r['x2'])
            if not inf: continue
            pre='REF1-'
            fb=[bucket(s.get('fact_mapping'),pre+x) for x in inf['chf']]
            kb=[bucket(s.get('consideration_mapping'),pre+x) for x in inf['chk']]
            c['changed fact: '+('case_only' if 'case_only' in fb else 'matched/corr' if any(b in('matched','corresponding') for b in fb) else 'unmentioned/no_doc')]+=1
            c['flipped cons: '+('case_only' if 'case_only' in kb else 'corresponding' if 'corresponding' in kb else 'matched' if 'matched' in kb else 'unmentioned/no_doc')]+=1
            via_ok = bool(via) and any(pre+w in json.dumps(via) for w in inf['wc'])
            c['via names the would_change']+=via_ok
            txt=json.dumps(s.get('reasoning') or {})+json.dumps(s.get('applicability') or {})
            c['mentions flip cond in reasoning/applic']+= bool(re.search(r'REF1-flip|would[_ ]change|flip condition',txt,re.I))
            rows.append(dict(model=model,x2=r['x2'],raw=r['raw_path'],rel=rel,via=via_ok,correct=r['correct'],fact=fb,cons=kb,tok=(r.get('tokens') or {}).get('completion')))
for k in sorted(out):
    c=out[k]; n=c['n']
    print('==',k,n); 
    for kk,vv in sorted(c.items()):
        if kk!='n': print(f'   {kk:45} {vv:4} {vv/n:5.0%}')
json.dump(rows,open('results/transfer/flip_rows.json','w'))
