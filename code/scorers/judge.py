"""Judges for the Benchbook scorers (PDF v0.4 pp. 21-24: Jev Choice for alignment, Jev_Noul for free-text fields).

One interface, three implementations:

    judge.choice(item, candidates, context=None, instruction=None) -> list[float]
        A probability distribution over `candidates` + one trailing "none of these" entry (len = len(candidates)+1,
        sums to 1). Used by the two alignment passes (facts, options, considerations, now, flip conditions).
    judge.noul(reference, candidate, question) -> float
        P(yes) that `candidate` matches `reference` under `question` (frame articulation x3, course).

    JevJudge()      TypeSafe Jev on OpenRouter (model id from bench.models.role("judge_choice"/"judge_noul").bare),
                    probabilities from OpenRouter's Decisions API (choice -> `probabilities`, noul -> P(yes)).
    StubJudge()     deterministic offline stand-in: normalized token overlap; identical text (after normalization)
                    is an exact match. For tests and dry runs only; its numbers mean nothing.
    CachedJudge(inner, path)   SQLite cache keyed by sha256(model id, method, rendered prompt).

Prompts live in scorers/prompts/*.v1.md + instructions.v1.yaml (PROMPT_VERSION). The candidate order is permuted
deterministically per call (seeded by the call's content) so position bias does not line up with id order, and the
permutation is part of the rendered prompt, hence of the cache key.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sqlite3
import string
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

PROMPT_VERSION = "v1"
PROMPTS = Path(__file__).resolve().parent / "prompts"
CHOICE_TEMPLATE = (PROMPTS / f"choice.{PROMPT_VERSION}.md").read_text()
NOUL_TEMPLATE = (PROMPTS / f"noul.{PROMPT_VERSION}.md").read_text()
INSTRUCTIONS = yaml.safe_load((PROMPTS / f"instructions.{PROMPT_VERSION}.yaml").read_text())
DEFAULT_CHOICE_INSTRUCTION = INSTRUCTIONS["choice"]["fact"]
LABELS = string.ascii_uppercase            # A..Z: one token each in every tokenizer we care about
MAX_PER_CALL = len(LABELS) - 1             # 25 candidates + "none" per call; more are chunked (see _chunks)


def instruction(kind: str) -> str:
    return INSTRUCTIONS["choice"][kind]


def noul_question(kind: str) -> str:
    return INSTRUCTIONS["noul"][kind]


# ---------------------------------------------------------------- prompt rendering (shared by every judge)
def _perm(item: str, candidates: list[str]) -> list[int]:
    seed = int(hashlib.sha256(json.dumps([item, candidates]).encode()).hexdigest()[:16], 16)
    order = list(range(len(candidates)))
    random.Random(seed).shuffle(order)
    return order


def render_choice(item: str, candidates: list[str], context: str | None = None,
                  instruction: str | None = None) -> tuple[str, list[int], list[str]]:
    """-> (prompt, perm, labels). perm[k] = index (into `candidates`) of the candidate shown with label k; the
    "none" label is labels[-1]. len(candidates) must be <= MAX_PER_CALL."""
    if len(candidates) > MAX_PER_CALL:
        raise ValueError(f"at most {MAX_PER_CALL} candidates per call (got {len(candidates)}); use Judge.choice")
    perm = _perm(item, candidates)
    labels = list(LABELS[:len(candidates) + 1])
    lines = [f"{labels[k]}. {_one_line(candidates[i])}" for k, i in enumerate(perm)]
    lines.append(f"{labels[-1]}. None of these")
    ctx = f"\nContext:\n{context}\n" if context else ""
    prompt = CHOICE_TEMPLATE.format(instruction=(instruction or DEFAULT_CHOICE_INSTRUCTION).strip(),
                                    context_block=ctx, item=_one_line(item), candidates="\n".join(lines),
                                    none_label=labels[-1])
    return prompt, perm, labels


def render_noul(reference: str, candidate: str, question: str) -> str:
    return NOUL_TEMPLATE.format(question=question.strip(), reference=_one_line(reference),
                                candidate=_one_line(candidate))


def _one_line(s) -> str:
    return " ".join(str(s).split())


def _chunks(n: int) -> list[range]:
    return [range(i, min(i + MAX_PER_CALL, n)) for i in range(0, n, MAX_PER_CALL)]


def _merge_chunks(parts: list[list[float]]) -> list[float]:
    """Combine per-chunk distributions (each over its chunk + none). Approximation, used only above 25 candidates:
    a candidate keeps its in-chunk probability; P(none) = product of the chunk nones; renormalize."""
    vals = [p for part in parts for p in part[:-1]]
    none = math.prod(part[-1] for part in parts)
    tot = sum(vals) + none
    return [v / tot for v in vals] + [none / tot] if tot > 0 else [0.0] * len(vals) + [1.0]


# ---------------------------------------------------------------- the interface
class Judge:
    """Base class. Subclasses implement _choice_call (<= MAX_PER_CALL candidates) and noul."""
    model_id = "abstract"

    def choice(self, item: str, candidates: list[str], context: str | None = None,
               instruction: str | None = None) -> list[float]:
        if not candidates:
            return [1.0]
        if len(candidates) <= MAX_PER_CALL:
            return self._choice_call(item, candidates, context, instruction)
        return _merge_chunks([self._choice_call(item, [candidates[i] for i in r], context, instruction)
                              for r in _chunks(len(candidates))])

    def choice_many(self, requests: list[dict]) -> list[list[float]]:
        """requests: [{item, candidates, context?, instruction?}]. Default: sequential."""
        return [self.choice(**r) for r in requests]

    def _choice_call(self, item, candidates, context, instruction) -> list[float]:
        raise NotImplementedError

    def noul(self, reference: str, candidate: str, question: str) -> float:
        raise NotImplementedError


# ---------------------------------------------------------------- StubJudge
_STOP = set("a an the of to and or in on at for by with is are was were be been it its this that as from will "
            "would can could may might do does did not no but if then so than".split())
_TOK = re.compile(r"[a-z0-9]+")


def _norm(s) -> str:
    return " ".join(_TOK.findall(str(s).lower()))


def _toks(s) -> set[str]:
    t = set(_TOK.findall(str(s).lower()))
    return (t - _STOP) or t


def similarity(a, b) -> float:
    """Mean of Dice and the overlap coefficient on content tokens; 1.0 iff the normalized texts are identical."""
    if _norm(a) == _norm(b):
        return 1.0
    ta, tb = _toks(a), _toks(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    dice = 2 * inter / (len(ta) + len(tb))
    overlap = inter / min(len(ta), len(tb))
    return min(0.99, (dice + overlap) / 2)


class StubJudge(Judge):
    """Deterministic, offline. choice: identical text takes 0.98 of the mass (split among identical candidates);
    otherwise weights sim**3 against a none weight (1 - max sim)**3, renormalized. noul: similarity."""
    model_id = "stub/overlap-v1"

    def __init__(self, exact_mass: float = 0.98, power: float = 3.0):
        self.exact_mass, self.power = exact_mass, power
        self.calls = {"choice": 0, "noul": 0}

    def _choice_call(self, item, candidates, context, instruction):
        self.calls["choice"] += 1
        sims = [similarity(item, c) for c in candidates]
        exact = [i for i, s in enumerate(sims) if s >= 1.0]
        w = [s ** self.power for s in sims]
        if exact:
            rest = [0.0 if i in exact else w[i] for i in range(len(w))] + [1e-3]
            tot = sum(rest)
            out = [(1 - self.exact_mass) * r / tot for r in rest]
            for i in exact:
                out[i] += self.exact_mass / len(exact)
            return out
        none = max(1 - max(sims), 0.02) ** self.power
        tot = sum(w) + none
        return [x / tot for x in w] + [none / tot]

    def noul(self, reference, candidate, question):
        self.calls["noul"] += 1
        return similarity(reference, candidate)


class MatrixJudge(Judge):
    """Test helper: answers from fixed tables. rows[item] = distribution over candidates+none, keyed by item text."""
    model_id = "test/matrix"

    def __init__(self, table: dict[tuple[str, tuple[str, ...]], list[float]] | None = None,
                 noul_table: dict[tuple[str, str], float] | None = None, fallback: Judge | None = None):
        self.table, self.noul_table, self.fallback = table or {}, noul_table or {}, fallback

    def _choice_call(self, item, candidates, context, instruction):
        key = (item, tuple(candidates))
        if key in self.table:
            return list(self.table[key])
        if self.fallback:
            return self.fallback.choice(item, candidates, context, instruction)
        raise KeyError(key)

    def noul(self, reference, candidate, question):
        if (reference, candidate) in self.noul_table:
            return self.noul_table[(reference, candidate)]
        return self.fallback.noul(reference, candidate, question) if self.fallback else 0.0


# ---------------------------------------------------------------- JevJudge (OpenRouter Decisions API)
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


class JevJudgeError(RuntimeError):
    pass


class JevJudge(Judge):
    """TypeSafe Jev through OpenRouter's **Decisions API** (POST /api/alpha/decisions; Jev is a decisions model and
    is refused on /chat/completions). One typed question per call:
      choice -> criteria {label: candidate text} (labels shuffled deterministically, last label = "None of these");
                the answer's `probabilities` is the distribution over labels (PDF: Jev Choice).
      noul   -> the answer's `noul` is P(yes) (PDF: Jev_Noul).
    The item/reference/candidate go in `state`; the instruction/question in `instructions`.
    Validated live 2026-10-25 (typesafe/jev-1.14 -> build jev-1.14-20261014; ~$2e-5 per call)."""

    def __init__(self, choice_model: str | None = None, noul_model: str | None = None, api_key: str | None = None,
                 timeout: float = 60.0, max_retries: int = 4, max_workers: int = 8, floor: float = 1e-6,
                 extra: dict | None = None):
        if choice_model is None or noul_model is None:
            from bench.models import role
            choice_model = choice_model or role("judge_choice").bare
            noul_model = noul_model or role("judge_noul").bare
        self.choice_model, self.noul_model = choice_model, noul_model
        self.model_id = f"openrouter-decisions/{choice_model}|{noul_model}"
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.timeout, self.max_retries, self.max_workers = timeout, max_retries, max_workers
        self.floor, self.extra = floor, extra or {}
        self.last_raw: dict | None = None
        self.builds: set[str] = set()          # exact model builds that answered (provenance)

    # -- transport
    def _post(self, model: str, state, questions: dict) -> dict:
        if not self.api_key:
            raise JevJudgeError("OPENROUTER_API_KEY is not set")
        import httpx
        body = {"model": model, "state": state, "questions": questions,
                "provider": {"data_collection": "deny"}, **self.extra}
        headers = {"Authorization": f"Bearer {self.api_key}", "X-Title": "benchbook-scorers"}
        err = None
        for attempt in range(self.max_retries + 1):
            try:
                r = httpx.post(DECISIONS_URL, json=body, headers=headers, timeout=self.timeout)
                if r.status_code in (429, 500, 502, 503, 504):
                    err = JevJudgeError(f"HTTP {r.status_code}: {r.text[:300]}")
                    time.sleep(min(30, 2 ** attempt))
                    continue
                if r.status_code != 200:
                    raise JevJudgeError(f"HTTP {r.status_code}: {r.text[:500]}")
                data = r.json()
                self.last_raw = data
                if "error" in data:
                    raise JevJudgeError(str(data["error"])[:500])
                if data.get("model"):
                    self.builds.add(data["model"])
                return data
            except httpx.HTTPError as e:      # network
                err = e
                time.sleep(min(30, 2 ** attempt))
        raise JevJudgeError(f"OpenRouter decisions failed after retries: {err}")

    @staticmethod
    def _answer(data: dict, qid: str, kind: str) -> dict:
        a = (data.get("answers") or {}).get(qid)
        if not isinstance(a, dict) or a.get("type") != kind:
            raise JevJudgeError(f"expected a `{kind}` answer for `{qid}`, got {str(a)[:200]}")
        return a

    # -- interface
    def _choice_call(self, item, candidates, context, instruction):
        _, perm, labels = render_choice(item, candidates, context, instruction)
        criteria = {labels[k]: _one_line(candidates[i]) for k, i in enumerate(perm)}
        criteria[labels[-1]] = "None of these: no candidate matches the item"
        state = {"item": _one_line(item), **({"context": context} if context else {})}
        q = {"match": {"type": "choice", "instructions": (instruction or DEFAULT_CHOICE_INSTRUCTION).strip(),
                       "criteria": criteria}}
        a = self._answer(self._post(self.choice_model, state, q), "match", "choice")
        probs = a.get("probabilities")
        if not probs:                          # schema marks probabilities optional: degrade to the argmax
            probs = {a.get("choice"): 1.0}
        vals = [max(float(probs.get(l, 0.0) or 0.0), self.floor) for l in labels]
        tot = sum(vals)
        dist = [v / tot for v in vals]
        out = [0.0] * (len(candidates) + 1)
        for k, i in enumerate(perm):
            out[i] = dist[k]
        out[-1] = dist[-1]
        return out

    def choice_many(self, requests):
        with ThreadPoolExecutor(self.max_workers) as ex:
            return list(ex.map(lambda r: self.choice(**r), requests))

    def noul(self, reference, candidate, question):
        state = {"reference": _one_line(reference), "candidate": _one_line(candidate)}
        q = {"q": {"type": "noul", "instructions": question.strip()}}
        a = self._answer(self._post(self.noul_model, state, q), "q", "noul")
        return float(a["noul"])


# ---------------------------------------------------------------- CachedJudge
class CachedJudge(Judge):
    """SQLite cache in front of any judge. Key = sha256(model id, method, rendered prompt): a prompt-version bump,
    a model swap or a different candidate order are all cache misses. Thread-safe."""

    def __init__(self, inner: Judge, path: str | os.PathLike = "results/judge_cache.sqlite"):
        self.inner = inner
        self.model_id = inner.model_id
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, model TEXT, method TEXT, "
                         "prompt TEXT, result TEXT, created REAL)")
        self._db.commit()
        self._lock = threading.Lock()
        self.hits = self.misses = 0

    @staticmethod
    def key(model_id: str, method: str, prompt: str) -> str:
        return hashlib.sha256(json.dumps([model_id, method, prompt]).encode()).hexdigest()

    def _get(self, k):
        with self._lock:
            row = self._db.execute("SELECT result FROM cache WHERE key=?", (k,)).fetchone()
        return json.loads(row[0]) if row else None

    def _put(self, k, method, prompt, result):
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?,?,?,?)",
                             (k, self.model_id, method, prompt, json.dumps(result), time.time()))
            self._db.commit()

    def _choice_call(self, item, candidates, context, instruction):
        prompt = render_choice(item, candidates, context, instruction)[0]
        k = self.key(self.model_id, "choice", prompt)
        got = self._get(k)
        if got is not None:
            self.hits += 1
            return got
        self.misses += 1
        res = self.inner._choice_call(item, candidates, context, instruction)
        self._put(k, "choice", prompt, res)
        return res

    def choice_many(self, requests):
        out: list = [None] * len(requests)
        todo = []
        for n, r in enumerate(requests):
            cands = r["candidates"]
            if not cands or len(cands) > MAX_PER_CALL:
                todo.append(n)
                continue
            prompt = render_choice(r["item"], cands, r.get("context"), r.get("instruction"))[0]
            got = self._get(self.key(self.model_id, "choice", prompt))
            if got is not None:
                self.hits += 1
                out[n] = got
            else:
                todo.append(n)
        if todo:
            self.misses += len(todo)
            res = self.inner.choice_many([requests[n] for n in todo])
            for n, v in zip(todo, res):
                r = requests[n]
                if r["candidates"] and len(r["candidates"]) <= MAX_PER_CALL:
                    prompt = render_choice(r["item"], r["candidates"], r.get("context"), r.get("instruction"))[0]
                    self._put(self.key(self.model_id, "choice", prompt), "choice", prompt, v)
                out[n] = v
        return out

    def noul(self, reference, candidate, question):
        prompt = render_noul(reference, candidate, question)
        k = self.key(self.model_id, "noul", prompt)
        got = self._get(k)
        if got is not None:
            self.hits += 1
            return got
        self.misses += 1
        res = self.inner.noul(reference, candidate, question)
        self._put(k, "noul", prompt, res)
        return res
