import json, sys
sys.path.insert(0, '/home/ubuntu/benchbook-labs/code')
import os; os.chdir('/home/ubuntu/benchbook-labs')
from bench.schema import parse_reply
from pipeline.store import Store
from scorers import alignment as A
from scorers.judge import CachedJudge, JevJudge, instruction
SP='/tmp/claude-1000/-home-ubuntu/4e83879d-8bf3-416b-b63a-9e4e4e93dd18/scratchpad/'
V2 = ("Each item is a course of action in one decision. Which candidate makes the same core choice as the one given: "
      "the same decision on the same question (for example act or refrain, approve or reject, include or omit, "
      "which body acts or decides)? Ignore implementation detail around the core choice: routing, channels, "
      "paperwork, timing words, and extra preparatory or follow-up steps. A candidate that bundles the same core "
      "choice with extra steps still counts. A candidate that makes a different or opposite choice does not, even "
      "if the wording overlaps.")
labels_idx = {0:0,1:1,2:0,4:1,5:1,6:1,7:1,8:1,9:1,10:1,13:1,14:1,16:1,17:1,18:0,19:1,20:1,21:1,22:1,23:1,24:1,25:1,
              26:0,27:1,28:1,30:1,31:1,32:0,33:1,35:1,36:1,37:1}
cells = json.load(open(SP+'band.json'))
lab = {(cells[i][0], cells[i][1], cells[i][2]): y for i, y in labels_idx.items()}
st = Store(); judge = CachedJudge(JevJudge(), path='results/judge_cache.sqlite')
R = {json.loads(l)['sample_id']: json.loads(l) for l in open('results/allpairs/B2/samples.jsonl')}
sids = sorted({c[0] for c in cells})
out = []
for sid in sids:
    r = R[sid]; d = json.load(open('results/allpairs/B2/'+r['details_path'])); oa = d['option_alignment']
    p = parse_reply(open('results/allpairs/B2/'+r['raw_path']).read(), noref=r['x2'] is None)
    opts = (p.steps.get('fact_enumeration', {}) or {}).get('options') or {}
    gen = {k: (v.get('do') if isinstance(v, dict) else str(v)) for k, v in opts.items()} if isinstance(opts, dict) else {}
    T = st.scenario(r['x1'])
    gold = {f'LIVE-O{i+1}': o.do for i, o in enumerate(T.case.options.values())}
    if list(gold) != oa['gold_ids'] or list(gen) != oa['gen_ids']:
        print('id mismatch', sid, list(gen), oa['gen_ids']); continue
    al2 = A.align(gen, gold, judge, 0.5, V2)
    for i, g in enumerate(oa['gold_ids']):
        for j, m in enumerate(oa['gen_ids']):
            s1, s2 = oa['S'][i][j], al2.S[i][j]
            y = lab.get((sid, m, g))
            if y is None:
                y = 1 if s1 >= 0.7 else (0 if s1 < 0.2 else None)
            out.append({'sid': sid, 'gen': m, 'gold': g, 's1': s1, 's2': s2, 'y': y, 'hand': (sid, m, g) in lab})
json.dump(out, open(SP+'optexp/result.json', 'w'))
print(len(sids), 'samples', len(out), 'cells', sum(o['hand'] for o in out), 'hand-labelled')
