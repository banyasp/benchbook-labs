"""Verify salience spans are verbatim in the scenario items and measure the decision-relevant word share."""
import yaml, glob, os, re
D='/home/claude/data-scaling/pilot/live-scenario'
sal=yaml.safe_load(open(f'{D}/salience.yaml'))
files={os.path.basename(p)[:-4]:open(p).read() for p in glob.glob(f'{D}/*/*.txt')}
total=sum(len(t.split()) for t in files.values())
norm=lambda s: re.sub(r'\s+',' ',s).strip()
rel={'decisive':0,'supporting':0,'task':0,'near_miss':0}; miss=[]; rows=[]
for it in sal['items']:
    txt=norm(files[it['id']]); w=0
    for sp in it.get('spans',[]):
        if norm(sp) not in txt: miss.append((it['id'],sp[:60]))
        else: w+=len(sp.split())
    rel[it['role']]=rel.get(it['role'],0)+w
    rows.append((it['id'],it['role'],len(files[it['id']].split()),w))
assert set(files)=={i['id'] for i in sal['items']}, set(files)^{i['id'] for i in sal['items']}
for r in rows: print(f"{r[0]:40s} {r[1]:12s} words={r[2]:4d} relevant_span_words={r[3]}")
core=rel['decisive']+rel['supporting']
print(f"TOTAL words {total}; decisive+supporting spans {core} ({core/total:.0%}); near-miss spans {rel['near_miss']} ({rel['near_miss']/total:.0%}); task {rel['task']}")
print(f"Non-decision-relevant share = {1-(core+rel['task'])/total:.0%} (counting near-miss text as non-relevant); {1-(core+rel['task']+rel['near_miss'])/total:.0%} if near-miss spans count as relevant")
print('span misses:', miss or 'none')

# Paragraph-level measure: a blank-line-separated block counts as relevant if it contains a span;
# near-miss material (item 10 whole; Northgate, TY2027 plan, NSF line in item 08) counts as must-process.
blk_rel=0; nm_extra=0
for it in sal['items']:
    raw=files[it['id']]
    blocks=[b for b in re.split(r'\n\s*\n', raw) if b.strip()]
    lines=[l for b in blocks for l in b.split('\n')]
    spans=[norm(s) for s in it.get('spans',[])]
    if it['role']=='near_miss': blk_rel+=len(raw.split()); continue
    for ln in lines:
        n=norm(ln)
        if n and any(n in s or (len(n)>25 and n[:25] in s) or s in n for s in spans): blk_rel+=len(ln.split())
    if it['id']=='08_payment-records':
        nm_extra+=sum(len(l.split()) for l in lines if re.search(r'NORTHGATE|4471|SETTLED IN FULL|TY 2027|03/15/2029|returned 1|No further balance|Balance at placement|To: Rodrigo|Re: Original', l))
print(f"Line-level relevant (lines touching a span) + near-miss items: {blk_rel+nm_extra} words = {(blk_rel+nm_extra)/total:.0%}; non-relevant {1-(blk_rel+nm_extra)/total:.0%}")
