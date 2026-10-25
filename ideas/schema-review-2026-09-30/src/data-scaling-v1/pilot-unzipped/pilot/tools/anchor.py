"""anchor.py FID "quote" [...] -> page number(s) where the whitespace-normalized quote occurs in the decision."""
import sys,re
norm=lambda s: re.sub(r'\s+',' ',s.replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"')).strip()
def pages(fid):
    t=open(f"/home/claude/data-scaling/pilot/raw/doha/{fid}.txt",errors='ignore').read()
    return [norm(p) for p in t.split('\f')]
def find(fid,q):
    P=pages(fid); nq=norm(q)
    hits=[i+1 for i,p in enumerate(P) if nq in p]
    if not hits:  # may span a page break
        joined=' '.join(P)
        if nq in joined:
            pos=joined.find(nq); acc=0
            for i,p in enumerate(P):
                acc+=len(p)+1
                if acc>pos: return [i+1]
    return hits
if __name__=="__main__":
    fid=sys.argv[1]
    for q in sys.argv[2:]: print(find(fid,q), '|', q[:80])
