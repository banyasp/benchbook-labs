"""Classify DOHA decision texts: case no, date, guidelines in SOR, outcome, F-only flag, length."""
import re, glob, os, sys, json
RAW = "/home/claude/data-scaling/pilot/raw"
urls = {l.split("\t")[0]: l.split("\t")[2].strip() for l in open(f"{RAW}/doha2026_list.tsv")}
rows = []
for p in sorted(glob.glob(f"{RAW}/doha/*.txt")):
    fid = os.path.basename(p)[:-4]
    t = open(p, errors="ignore").read()
    flat = re.sub(r"\s+", " ", t)
    case = re.search(r"(ISCR|ADP) Case No\.\s*([0-9]{2}-[0-9]{5})", flat)
    date = re.search(r"Pro se\s+(\d{2}/\d{2}/\d{4})|Esq\.?[^0-9]{0,80}?(\d{2}/\d{2}/\d{4})|(\d{2}/\d{2}/\d{4})", flat)
    d = next((g for g in (date.groups() if date else []) if g), None)
    guides = sorted(set(re.findall(r"Paragraph \d+, Guideline ([A-M])", flat)))
    concl = flat[flat.rfind("Conclusion"):] if "Conclusion" in flat else flat[-1500:]
    out = "GRANTED" if re.search(r"(is|are) granted|GRANTED", concl) else ("DENIED" if re.search(r"denied|DENIED|revoked", concl) else "?")
    ff = re.findall(r"Paragraph \d+, Guideline ([A-M])[^:]*:\s*(FOR|AGAINST) APPLICANT", flat)
    rows.append(dict(fid=fid, case=(case.group(1)+" "+case.group(2)) if case else "?", date=d, guides=guides,
                     formal=ff, outcome=out, words=len(flat.split()), counsel="Pro se" if "Applicant: Pro se" in flat else "counsel",
                     url=urls.get(fid, "")))
F = [r for r in rows if "F" in r["guides"]]
print(f"total {len(rows)}; with F {len(F)}; F-only {sum(1 for r in F if r['guides']==['F'])}")
for r in rows:
    print(r["fid"], r["case"], r["date"], "".join(r["guides"]), r["outcome"], r["words"], r["counsel"], r["formal"])
json.dump(rows, open(f"{RAW}/classified.json", "w"), indent=1)
