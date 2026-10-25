"""Validate cases: factor IDs exist, anchors verbatim, case block <= 350 words. Build cases-all.yaml."""
import yaml, glob, re, sys
sys.path.insert(0, '/home/claude/data-scaling/pilot/tools')
from anchor import find
P='/home/claude/data-scaling/pilot'
cat=yaml.safe_load(open(f'{P}/catalog-F.yaml'))['catalog']
ids=set(cat['factors_B'])|{k for k in cat['factors_A'] if k!='A20d'}|set(cat['factors_doctrine'])
ids|={v['id'] for v in cat['factors_A']['A20d']['scale'].values()}
allc={}; ok=True
for f in sorted(glob.glob(f'{P}/cases/DOHA-F-*.yaml')):
    raw=open(f).read(); d=yaml.safe_load(raw); c=d['case']
    fid=re.search(r'FileId/(\d+)/',c['source']['url']).group(1)
    words=len(yaml.safe_dump(c,sort_keys=False,width=1000).split())
    tags={t for fct in c['facts'] for t in fct['factors']}|set(c['reason'])
    bad=tags-ids
    anchors=[c['reason_cite']['anchor']]
    pg=find(fid,anchors[0])
    # verify quoted fragments inside flip-rule bases and watch_for (text inside single quotes after "p. N:")
    strs=[str(r.get('basis','')) for r in c.get('flip_rules',[])]+[w['what'] for w in c.get('watch_for',[])]
    quoted=[q for x in strs for q in re.findall(r"'([^']{25,})'", x)]
    qmiss=[q for q in quoted if not find(fid,q.replace(' ... ',' ').split(' ... ')[0]) and not all(find(fid,part) for part in q.split(' ... '))]
    status='OK' if (not bad and pg and words<=350 and not qmiss) else 'FAIL'
    if status=='FAIL': ok=False
    print(f"{c['id']} {c['source']['caseno']} out={c['outcome']} words={words} anchor_page={pg} (cited {c['reason_cite']['page']}) unknown_ids={sorted(bad)} quote_miss={qmiss} {status}")
    allc[c['id']]=d
yaml.safe_dump({'cases':allc},open(f'{P}/cases-all.yaml','w'),sort_keys=False,width=110,allow_unicode=True)
print('ALL OK' if ok else 'SOME FAILED')
