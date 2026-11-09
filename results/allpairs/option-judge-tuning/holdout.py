import json, sys, random, os
sys.path.insert(0, '/home/ubuntu/benchbook-labs/code'); os.chdir('/home/ubuntu/benchbook-labs')
exec(open('/tmp/claude-1000/-home-ubuntu/4e83879d-8bf3-416b-b63a-9e4e4e93dd18/scratchpad/optexp/run.py').read().split("labels_idx")[0])
SP='/tmp/claude-1000/-home-ubuntu/4e83879d-8bf3-416b-b63a-9e4e4e93dd18/scratchpad/'
used = {c[0] for c in json.load(open(SP+'band.json'))}
st = Store(); judge = CachedJudge(JevJudge(), path='results/judge_cache.sqlite')
R = [json.loads(l) for l in open('results/allpairs/B2/samples.jsonl')]
cand = [r for r in R if r.get('details_path') and r['sample_id'] not in used]
random.seed(11); pick = random.sample(cand, 12)
for r in pick:
    p = parse_reply(open('results/allpairs/B2/'+r['raw_path']).read(), noref=r['x2'] is None)
    opts = (p.steps.get('fact_enumeration', {}) or {}).get('options') or {}
    gen = {k: (v.get('do') if isinstance(v, dict) else str(v)) for k, v in opts.items()} if isinstance(opts, dict) else {}
    T = st.scenario(r['x1']); gold = {f'LIVE-O{i+1}': o.do for i, o in enumerate(T.case.options.values())}
    al2 = A.align(gen, gold, judge, 0.5, V2)
    print('='*80); print(r['sample_id'][:100])
    for k, v in gen.items(): print('  M', k, ':', v[:115])
    for k, v in gold.items(): print('  G', k, ':', v[:115])
    print('  v2 pairs >0.5:', [(g, m, round(s, 2)) for g, m, s in al2.pairs], '| v2 S:', [[round(x, 2) for x in row] for row in al2.S])
