"""(d) Monotonicity fuzz (3.6 lint; ArgLLM contestability): on random casebooks and situations, adding a
factor that favors side s never moves the issue's settled outcome away from s, and removing one never
moves it toward s. Also the per-card a fortiori property the red team fuzzed on v2. >= 5,000 probes
(random casebook + situation, every single-step change checked) per catalog."""
import random
import pytest
import solver_v3 as S
from conftest import cat, card

N = 5000


def rand_tags(rnd, c, issue, p=0.45):
    out = set()
    for stem, lad in c.ladder.items():
        if c.factors[stem]["issue"] == issue and rnd.random() < p:
            out.add(lad[rnd.randrange(len(lad))])
    return c.close(out)


def rand_card(rnd, c, issue, i):
    X = rand_tags(rnd, c, issue)
    o = rnd.choice(c.sides(issue))
    stems = [s for s in c.ladder if c.factors[s]["issue"] == issue and c.factors[s]["favors"] == o]
    if not any(c.side(t) == o for t in X):
        X |= c.close([c.ladder[rnd.choice(stems)][0]])
    top = {s: t for s, t in c.top(X).items() if c.factors[s]["favors"] == o}
    pick = rnd.sample(sorted(top), rnd.randint(1, len(top)))
    R = set()
    for s in pick:                                  # a reason rung at or below the observed rung
        R.add(c.ladder[s][rnd.randint(0, c.tag[top[s]][2])])
    return card(f"C{i}", issue, o, c.close(R), X, force=rnd.choice(["required"] * 4 + ["permitted"]),
                rank=rnd.randint(0, 2))


def value(c, cards, Y, issue, s):
    sup = S.support(c, cards, Y, issue)
    return 0 if sup["status"] != "settled" else (1 if sup["side"] == s else -1)


@pytest.mark.parametrize("name,flags", [("AUT", ()), ("VEP", ()), ("SEC-F", ("doctrine",)), ("FISC", ())])
def test_d_monotonicity_fuzz(name, flags):
    c = cat(name, flags)
    rnd = random.Random(7)
    probes = checks = settled = 0
    for n in range(N):
        issue = rnd.choice(list(c.issues))
        cards = [rand_card(rnd, c, issue, i) for i in range(rnd.randint(1, 4))]
        Y = rand_tags(rnd, c, issue)
        base = S.support(c, cards, Y, issue)
        settled += base["status"] == "settled"
        verdicts = {S.card_key(k): S.compare(c, k, Y)["verdict"] for k in cards}
        for ch in S.single_changes(c, Y, issue):
            t = ch[1:]
            if c.is_cond(t):
                continue
            s = c.side(t)
            Y2 = S.apply_change(c, Y, [ch])
            b = 0 if base["status"] != "settled" else (1 if base["side"] == s else -1)
            a = value(c, cards, Y2, issue, s)
            assert (a >= b) if ch[0] == "+" else (a <= b), (name, ch, sorted(Y), cards)
            for k in cards:                          # per card: helping its outcome never breaks a forcing verdict
                helps = (ch[0] == "+") == (s == k["outcome"])
                if helps and verdicts[S.card_key(k)] in S.FORCING:
                    assert S.compare(c, k, Y2)["verdict"] in S.FORCING, (name, ch, sorted(Y), k)
            checks += 1
        probes += 1
    assert probes >= 5000 and checks > probes and settled > probes // 20
