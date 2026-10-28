"""Hand-curated pair list (after reading each citing sentence) -> results/h3-pilot/pairs.yaml, with the citing sentence recorded
verbatim from cite-candidates.json. band: same = same guideline AND same issue at the decision point; different = otherwise."""
import json, yaml
from .crawl import OUT

NAME = {"E": "Personal Conduct", "F": "Financial Considerations", "G": "Alcohol Consumption", "H": "Drug Involvement and Substance Misuse",
        "I": "Psychological Conditions", "J": "Criminal Conduct"}
HINT = {
    "bond": " The question is whether the Individual is an unlawful user of a controlled substance or an addict, so that the Bond Amendment bars access authorization.",
    "jsober": " The question is whether the criminal conduct is mitigated, given the time that has passed, any abstinence and treatment.",
    "ghab": " The question is whether the Individual habitually or binge consumed alcohol to the point of impaired judgment and whether that concern is resolved.",
    "gpeth": " The question is what the alcohol biomarker (PEth) evidence shows and whether the Guideline G concern is resolved.",
    "ereg": " The question is whether the Individual's lack of candor or personal conduct concern is mitigated, in light of the laboratory evidence and the expert's qualifications.",
    "": "",
}
# id, citing, cited, T guideline, C guideline, issue hint (T), issue hint (C), band
P = [
 ("22-0084:21-0124", "H", "H", "bond", "bond", "same"), ("22-0084:21-0057", "H", "H", "bond", "bond", "same"),
 ("22-0084:21-0031", "H", "H", "bond", "bond", "same"), ("25-0124:24-0083", "H", "H", "bond", "bond", "same"),
 ("21-0057:21-0031", "H", "H", "bond", "bond", "same"), ("22-0118:21-0031", "H", "H", "bond", "bond", "same"),
 ("22-0102:22-0085", "J", "J", "jsober", "jsober", "same"), ("22-0130:22-0085", "J", "J", "jsober", "jsober", "same"),
 ("23-0012:22-0085", "J", "J", "jsober", "jsober", "same"), ("23-0013:22-0085", "J", "J", "jsober", "jsober", "same"),
 ("23-0015:22-0085", "J", "J", "jsober", "jsober", "same"),
 ("24-0040:22-0085", "J", "J", "jsober", "jsober", "different"),     # drug-related criminal conduct vs alcohol-related
 ("22-0102:22-0064", "G", "G", "", "", "same"),
 ("24-0031:24-0004", "G", "G", "ghab", "ghab", "same"), ("24-0031:18-0034", "G", "G", "ghab", "ghab", "same"),
 ("24-0089:18-0054", "G", "G", "ghab", "ghab", "same"), ("24-0089:18-0034", "G", "G", "ghab", "ghab", "same"),
 ("26-0076:24-0004", "G", "G", "ghab", "ghab", "same"), ("22-0114:18-0034", "G", "G", "ghab", "ghab", "same"),
 ("25-0092:24-0095", "G", "G", "", "", "same"),
 ("25-0054:24-0031", "G", "G", "gpeth", "ghab", "same"), ("24-0109:24-0031", "G", "G", "gpeth", "ghab", "same"),
 ("26-0083:26-0050", "G", "G", "gpeth", "gpeth", "same"),
 ("26-0025:23-0078", "J", "J", "", "", "same"),
 ("23-0055:19-0040", "F", "F", "", "", "same"), ("23-0036:19-0047", "I", "I", "", "", "same"),
 ("24-0088:24-0055", "E", "E", "ereg", "ereg", "same"),
 ("22-0114:18-0025", "G", "H", "ghab", "", "different"),
]


def focus(g, hint):
    return (f"The Guideline {g} ({NAME[g]}) security concern: whether the Individual has resolved or mitigated it, so that access "
            f"authorization can be granted or restored. Decision point: the Administrative Judge's finding on Guideline {g}.{HINT[hint]}")


def main():
    cands = json.load(open(OUT / "cite-candidates.json"))
    pairs = []
    for pid, gt, gc, ht, hc, band in P:
        citing, cited = (f"PSH-{x}" for x in pid.split(":"))
        c = next((x for x in cands if x["citing"] == citing and x["cited"][0] == cited), None)
        pairs.append({"id": f"{citing}__{cited}", "citing": citing, "cited": cited, "relation": "analogous (cited with see/see also, as support)",
                      "citing_sentence": c["sentence"] if c else "[not found]", "citing_span": c["span"] if c else None,
                      "guideline_T": gt, "guideline_C": gc, "band": band, "focus_T": focus(gt, ht), "focus_C": focus(gc, hc)})
    (OUT / "pairs.yaml").write_text(yaml.safe_dump({"pairs": pairs}, sort_keys=False, allow_unicode=True, width=200))
    print(len(pairs), [p["id"] for p in pairs if p["citing_sentence"] == "[not found]"])


if __name__ == "__main__":
    main()
