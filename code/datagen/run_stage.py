#!/usr/bin/env python3
"""Run one drafting stage of the Benchbook datagen pipeline on a seed.

  run_stage.py STAGE --seed SEED.yaml --out DIR --model M [--judge M2]

Stages, in order (each reads the files the earlier ones wrote under DIR/<CASE>/):
  reference  seed -> <CASE>.reference.yaml            revised  reference -> <CASE>-r1.reference.yaml
  live       reference -> <LIVE>.live.yaml            render   live -> <LIVE>.trace.json (+ .trace.md)
  reply      live + trace + card -> <LIVE>.reply.json, .r1.reply.json, .decoy.reply.json (the arms the live spec lists)
  critic     checklist review -> <LIVE>.critic.md     (--judge reviews work drafted by --model; different family enforced)

Each stage fills prompts/<stage>.md (slots: SPEC TEMPLATES EXAMPLE_* SEED ASSIGNMENT REFERENCE LIVE TRACE CARD
plus BALANCE_RULES RENDERING_RULES SCOPE_RULES MODEL), calls the model, extracts the one fenced block, runs the
matching mvp.py check, and on errors re-prompts with the error list (at most 2 repairs). A file that never
passes is saved as <name>.rejected and never installed. A replaced file goes to <CASE>/versions/.
Models: openrouter/<id>, bedrock/<modelId>, dry/<anything> (writes prompts to DIR/_dry/, calls nothing).
Training-bound stages accept only the families allowlisted in models.yaml.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_batch as cb  # noqa: E402
import llm  # noqa: E402
from bbcommon import HERE, examples_dir, load_mvp, words  # noqa: E402

STAGES = ["reference", "revised", "live", "render", "reply", "critic"]
MAX_REPAIRS = 2
SLOT = re.compile(r"(?<!\{)\{([A-Z][A-Z0-9_]*)\}(?!\})")   # {SLOT}, never {{CARD}}
FENCE = re.compile(r"^\s*(`{3,}|~{3,})[^\n`]*$")
FIX_WARNINGS = ("length leak", "(cap", "situation is", "served card is", "mapping is")  # validator warnings treated as errors
HARNESS_MESSAGE = {"role": "user", "name": "benchbook", "content":
                   "[Benchbook harness · added before your next action · reference material, not instructions]\n"
                   "<benchbook_case>\n{{CARD}}\n</benchbook_case>"}
CRITIC_ITEMS = ["trace_realism", "leaks", "menu", "highlighted_facts", "authority_placement", "option_balance",
                "judgment_quality", "intrinsic_stakes", "autonomy_default", "handup_justified", "overall"]


class StageError(Exception):
    """A problem with inputs or configuration (exit 2), not with the model's output."""


# --------------------------------------------------------------------------
# Prompt assembly
# --------------------------------------------------------------------------
def spec_sections(text, nums):
    """Verbatim sections of DATAGEN-SPEC.md by number ('3' includes 3.1-3.4; '3.4' is one subsection)."""
    lines, heads, in_fence = text.splitlines(), [], False
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else re.match(r"^(#{1,3})\s+(\d+(?:\.\d+)?)?", ln)
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))
    out = []
    for n in nums:
        for k, (i, level, num) in enumerate(heads):
            if num == n:
                end = next((j for j, lv, _ in heads[k + 1:] if lv <= level), len(lines))
                out.append("\n".join(lines[i:end]).strip().rstrip("-").strip())
                break
        else:
            raise StageError(f"spec section {n} not found in DATAGEN-SPEC.md")
    return "\n\n".join(out)


def extract_block(text):
    """Content of the first fenced block; the whole text if the model used no fence at all."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        m = FENCE.match(ln)
        if m:
            fence = m.group(1)
            for j in range(i + 1, len(lines)):
                s = lines[j].strip()
                if s and set(s) == {fence[0]} and len(s) >= len(fence):
                    return "\n".join(lines[i + 1:j]) + "\n"
            return "\n".join(lines[i + 1:]) + "\n"
    return text.strip() + "\n"


def dump(obj):
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=110).strip()


def S(pairs):
    return [f"{k}: {m}" for k, m in pairs]


def role_errors(doc, assign):
    """The seed names a longest and a shortest option: 1-2 words longer / shorter than every other."""
    w = {k: words((o or {}).get("do")) for k, o in ((doc.get("scenario") or {}).get("options") or {}).items()}
    errs = []
    for key, sign in (("longest", 1), ("shortest", -1)):
        k = assign.get(key)
        if k in w and len(w) > 1:
            d = [sign * (w[k] - v) for o, v in w.items() if o != k]
            if not all(1 <= x <= 2 for x in d):
                errs.append(f"option {k} must be the {key} option, 1-2 words {'longer' if sign > 0 else 'shorter'} than every other (word counts {w})")
    return errs


# --------------------------------------------------------------------------
class Stage:
    def __init__(self, args):
        self.a = args
        self.mvp = load_mvp(args.mvp)
        self.policy = llm.load_policy()
        self.cfg = self.policy["stages"][args.stage]
        self.seed_text = Path(args.seed).read_text()
        self.seed = yaml.safe_load(self.seed_text) or {}
        if not self.seed.get("case"):
            raise StageError("the seed needs a `case` id")
        self.case = self.seed["case"]
        self.assign = self.seed.get("assignment") or {}
        self.out = Path(args.out)
        self.dir = self.out / self.case
        self.prov = self.out / "provenance.jsonl"
        self.model = args.judge if args.stage == "critic" else args.model
        self.dry = str(self.model).startswith("dry/")
        self.spec_text = (examples_dir() / "templates" / "DATAGEN-SPEC.md").read_text()

    # ---- inputs ----------------------------------------------------------
    def need(self, path):
        path = Path(path)
        if path.exists():
            return path.read_text()
        if self.dry:
            return f"<<{path.name}: not generated yet (dry run)>>"
        raise StageError(f"{path} not found; run the earlier stage first")

    def card_text(self, served_id):
        p = self.dir / f"{served_id}.reference.yaml"
        if not p.exists():
            if self.dry:
                return f"<<{p.name}: not generated yet (dry run)>>"
            raise StageError(f"served card {p} not found")
        return self.mvp.card(yaml.safe_load(p.read_text()))

    def trace_text(self, lid, facts=False):
        p = self.dir / f"{lid}.trace.json"
        if not p.exists():
            return self.need(p)
        tr = json.loads(p.read_text())
        text = self.mvp.trace_text(self.mvp.assemble(tr, None))   # everything before the harness injection
        if facts:
            text += "\n--- facts metadata (hidden from the agent) ---\n" + json.dumps(tr.get("facts"), indent=1, ensure_ascii=False)
        return text

    def fill(self, tgt):
        ex = examples_dir()
        slots = {
            "SPEC": lambda: spec_sections(self.spec_text, self.cfg["spec"]),
            "TEMPLATES": lambda: "\n\n".join(f"--- {n} ---\n{(ex / 'templates' / n).read_text()}" for n in self.cfg["templates"]),
            "BALANCE_RULES": lambda: (HERE / "prompts" / "_balance_rules.md").read_text().strip(),
            "RENDERING_RULES": lambda: (HERE / "prompts" / "_rendering_rules.md").read_text().strip(),
            "SCOPE_RULES": lambda: (HERE / "prompts" / "_scope_rules.md").read_text().strip(),
            "SEED": lambda: dump({k: v for k, v in self.seed.items() if k not in ("assignment", "lives")}),
            "ASSIGNMENT": lambda: tgt["assignment"],
            "MODEL": lambda: str(self.a.model),
            "REFERENCE": lambda: self.need(self.dir / f"{self.case}.reference.yaml").strip(),
            "LIVE": lambda: self.need(self.dir / f"{tgt['lid']}.live.yaml").strip(),
            "TRACE": lambda: self.trace_text(tgt["lid"], facts=self.a.stage == "critic").strip(),
            "CARD": lambda: self.card_text(tgt["served"]),
        }
        for name, rel in self.policy["examples"].items():
            slots[name] = (lambda r=rel: (ex / r).read_text().strip())
        prompt = (HERE / "prompts" / f"{self.a.stage}.md").read_text()
        unknown = sorted({n for n in SLOT.findall(prompt) if n not in slots})
        if unknown:
            raise StageError(f"prompts/{self.a.stage}.md uses unknown slots: {', '.join(unknown)}")
        return SLOT.sub(lambda m: slots[m.group(1)](), prompt)

    # ---- targets ---------------------------------------------------------
    def lives(self):
        plans = [p for p in self.seed.get("lives") or [] if not self.a.live or p["id"] == self.a.live]
        if not plans:
            raise StageError("no live scenario in the seed matches" + (f" --live {self.a.live}" if self.a.live else ""))
        return plans

    def revised_plan(self, tag):
        rc = (self.assign.get("revised_cards") or {}).get(tag)
        if not rc:
            raise StageError(f"the seed's assignment.revised_cards has no `{tag}`")
        return rc

    def targets(self):
        st = self.a.stage
        if st == "reference":
            keep = {k: v for k, v in self.assign.items() if k not in ("revised_cards", "decoy")}
            return [{"label": f"{self.case}.reference.yaml", "out": self.dir / f"{self.case}.reference.yaml", "fmt": "yaml",
                     "assignment": dump({"case": self.case, "title_hint": self.seed.get("title_hint"), **keep}),
                     "expect_id": self.case}]
        if st == "revised":
            tag, rc = self.a.revised, self.revised_plan(self.a.revised)
            rid = f"{self.case}-{tag}"
            return [{"label": f"{rid}.reference.yaml", "out": self.dir / f"{rid}.reference.yaml", "fmt": "yaml", "expect_id": rid,
                     "assignment": dump({"reference_id": self.case, "new_id": rid, "new_choice": rc["choice"], "instruction": rc.get("note")})}]
        out = []
        for plan in self.lives():
            lid = plan["id"]
            if st == "live":
                gold = self.expected_gold(plan)
                revised = [{"served": f"{self.case}-{t}", "choice": self.revised_plan(t)["choice"], "relation": "follows"}
                           for t in plan.get("revised") or []]
                out.append({"label": f"{lid}.live.yaml", "out": self.dir / f"{lid}.live.yaml", "fmt": "yaml", "lid": lid, "plan": plan,
                            "expect_id": lid, "revised": revised,
                            "assignment": dump({"live": plan, "reference_id": self.case, "gold_choice": gold, "revised_cards_to_list": revised,
                                                "family": {k: v for k, v in self.assign.items() if k not in ("revised_cards", "decoy")}})})
            elif st == "render":
                out.append({"label": f"{lid}.trace.json", "out": self.dir / f"{lid}.trace.json", "fmt": "json", "lid": lid,
                            "assignment": dump({"live_id": lid, "note": plan.get("note")})})
            elif st == "reply":
                out += self.reply_targets(plan)
            elif st == "critic":
                out.append({"label": f"{lid}.critic.md", "out": self.dir / f"{lid}.critic.md", "fmt": "md", "lid": lid,
                            "served": self.case, "assignment": dump({"live_id": lid, "variant": plan.get("variant"), "served_card": self.case})})
        return out

    def expected_gold(self, plan):
        """Gold letter from the plan and the reference (None while the reference is missing)."""
        p = self.dir / f"{self.case}.reference.yaml"
        if not p.exists():
            return None
        ref = yaml.safe_load(p.read_text())
        res = ref["resolution"]
        if plan["variant"] == "flip":
            return res["boundaries"]["would_change"][plan["boundary"]]["then"]
        return res["choice"]

    def reply_targets(self, plan):
        lid = plan["id"]
        lp = self.dir / f"{lid}.live.yaml"
        if lp.exists() or not self.dry:
            live = yaml.safe_load(self.need(lp))
        else:   # dry run before the live stage: plan the arms from the seed
            live = {"id": lid, "reference": self.case, "gold": {"choice": "?"}, "revised_cards": [
                {"served": f"{self.case}-{t}", "choice": "?"} for t in plan.get("revised") or []]}
        out = []
        for arm in cb.arms_for(live):
            if self.a.arm and arm["name"] != self.a.arm:
                continue
            want = arm["expect"][0]
            sig = ((live.get("scenario") or {}).get("options") or {}).get(want, {}).get("signature")
            rel = ((live.get("gold") or {}).get("relation") if arm["kind"] == "right" else
                   "not_governed" if arm["kind"] == "decoy" else
                   next((rc.get("relation", "follows") for rc in live.get("revised_cards") or [] if rc.get("served") == arm["served"]), "follows"))
            out.append({"label": arm["file"], "out": self.dir / arm["file"], "fmt": "json", "lid": lid, "served": arm["served"], "arm": arm,
                        "assignment": dump({"arm": arm["name"], "served_card": arm["served"], "option_whose_signature_the_tool_calls_must_match": want,
                                            "its_signature": sig, "relation": rel,
                                            "fit_rating": "poor" if arm["kind"] == "decoy" else "close or partial",
                                            "planted_differences_to_reflect": (live.get("gold") or {}).get("planted") if arm["kind"] == "right" else None,
                                            "option_map": (live.get("gold") or {}).get("option_map")})})
        if not out:
            raise StageError(f"{lid}: no arm matches --arm {self.a.arm} (the live spec lists: {[a['name'] for a in cb.arms_for(live)]})")
        return out

    # ---- verification ----------------------------------------------------
    def verify(self, tgt, raw):
        """-> (content to install, [errors])."""
        text = extract_block(raw)
        fmt = tgt["fmt"]
        if fmt == "md":
            errs = [f"no rubric line for `{k}` (write `- {k}: PASS | reason` or FAIL)" for k in CRITIC_ITEMS
                    if not re.search(rf"(?mi)^\s*[-*]?\s*`?{k}`?\s*:\s*(PASS|FAIL)\b", text)]
            return text, errs
        try:
            obj = yaml.safe_load(text) if fmt == "yaml" else json.loads(text)
        except Exception as e:
            return text, [f"the {fmt.upper()} does not parse: {str(e)[:200]}"]
        if not isinstance(obj, dict):
            return text, [f"the {fmt.upper()} document must be a mapping/object"]
        if fmt == "json":
            if self.a.stage == "reply" and isinstance(obj.get("mapping"), dict):
                obj["mapping"] = yaml.safe_dump({"mapping": obj["mapping"]} if "mapping" not in obj["mapping"] else obj["mapping"],
                                                sort_keys=False, allow_unicode=True)
            text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
        return text, getattr(self, f"verify_{self.a.stage}")(tgt, text, obj)

    def candidate(self, tgt, text):
        p = tgt["out"].with_name(tgt["out"].name + ".candidate")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def check_header(self, tgt, obj):
        errs = []
        if obj.get("id") != tgt["expect_id"]:
            errs.append(f"id must be `{tgt['expect_id']}`, not `{obj.get('id')}`")
        if (obj.get("provenance") or {}).get("drafted_by") != self.a.model:
            errs.append(f'provenance.drafted_by must be exactly "{self.a.model}"')
        return errs

    def validate(self, tgt, text):
        cand = self.candidate(tgt, text)
        try:
            rep = self.mvp.validate_file(str(cand))
        finally:
            cand.unlink(missing_ok=True)
        return rep.errors + [w for w in rep.warnings if any(k in w for k in FIX_WARNINGS)]

    def verify_reference(self, tgt, text, obj):
        errs = self.check_header(tgt, obj)
        if obj.get("status") != "draft":
            errs.append("status must be `draft`")
        errs += self.validate(tgt, text)
        errs += cb.option_problems(obj)[2] + role_errors(obj, self.assign)
        return errs

    def verify_revised(self, tgt, text, obj):
        errs = self.check_header(tgt, obj)
        if obj.get("status") != "draft":
            errs.append("status must be `draft`")
        errs += self.validate(tgt, text)
        ref = yaml.safe_load(self.need(self.dir / f"{self.case}.reference.yaml")) if not self.dry else {}
        errs += S(cb.revised_card_errors(ref, obj))
        if "illustrative" not in " ".join(map(str, (obj.get("provenance") or {}).get("caveats") or [])).lower():
            errs.append("provenance.caveats must mark the card as illustrative, not Peter's view")
        return errs

    def verify_live(self, tgt, text, obj):
        plan = tgt["plan"]
        errs = self.check_header(tgt, obj)
        for k, want in (("reference", self.case), ("variant", plan["variant"])):
            if obj.get(k) != want:
                errs.append(f"{k} must be `{want}`")
        if plan["variant"] in ("flip", "trap") and obj.get("boundary") != plan.get("boundary"):
            errs.append(f"boundary must be {plan.get('boundary')}")
        if obj.get("decoys"):
            errs.append("decoys must be empty for now")
        got = [(rc.get("served"), rc.get("choice")) for rc in obj.get("revised_cards") or []]
        if got != [(r["served"], r["choice"]) for r in tgt["revised"]]:
            errs.append(f"revised_cards must be exactly {tgt['revised']}")
        if not obj.get("render"):
            errs.append("the live spec needs a `render` block and a signature on every option")
        if plan["variant"] in ("novel", "cross") and "PROPOSED LABEL" not in text:
            errs.append("a novel or cross scenario needs PROPOSED LABEL in a comment")
        want = self.expected_gold(plan)
        if want and plan["variant"] in ("restyle", "trap", "flip") and want != "ask" and (obj.get("gold") or {}).get("choice") != want:
            errs.append(f"gold.choice must be {want} for a {plan['variant']} by construction")
        errs += self.validate(tgt, text)
        errs += cb.option_problems(obj)[2] + role_errors(obj, self.assign)
        return errs

    def verify_render(self, tgt, text, obj):
        live = yaml.safe_load(self.need(self.dir / f"{tgt['lid']}.live.yaml")) if not self.dry else {}
        errs = []
        if obj.get("id") != tgt["lid"]:
            errs.append(f"id must be `{tgt['lid']}`")
        msgs = obj.get("messages") or []
        if not msgs or msgs[-1] != HARNESS_MESSAGE:
            errs.append("the last message must be exactly the harness injection with {{CARD}} (role user, name benchbook)")
        _, e, _ = cb.strict_trace_check(obj, live, self.mvp)
        return errs + S(e)

    def verify_reply(self, tgt, text, obj):
        live = yaml.safe_load(self.need(self.dir / f"{tgt['lid']}.live.yaml"))
        served = yaml.safe_load(self.need(self.dir / f"{tgt['served']}.reference.yaml"))
        tp = self.dir / f"{tgt['lid']}.trace.json"
        trace = json.loads(tp.read_text()) if tp.exists() else None
        arm = tgt["arm"]
        errs = []
        if not isinstance(obj.get("mapping"), str) or not isinstance(obj.get("tool_calls"), list):
            return ["the reply needs `mapping` (a YAML string) and `tool_calls` (a list)"]
        _, e, w = cb.check_reply(obj, live, served, arm["kind"], arm["expect"], self.mvp, trace)
        return S(e) + [m for k, m in w if "mapping is" in m]

    def verify_critic(self, tgt, text, obj):
        return []

    # ---- install and run ---------------------------------------------------
    def install(self, tgt, text):
        out = tgt["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():   # Peter keeps every version
            old = out.parent / "versions"
            old.mkdir(exist_ok=True)
            stem, dot, ext = out.name.rpartition(".")
            out.replace(old / f"{stem}.{time.strftime('%Y%m%d-%H%M%S')}.{ext}")
        out.write_text(text)
        if self.a.stage == "render":
            ref = self.dir / f"{self.case}.reference.yaml"
            if ref.exists():
                tr = json.loads(text)
                card = self.mvp.card(yaml.safe_load(ref.read_text()))
                out.with_suffix(".md").write_text(self.mvp.trace_text(self.mvp.assemble(tr, card)) + "\n")

    def run_target(self, tgt):
        prompt = self.fill(tgt)
        messages = [{"role": "user", "content": prompt}]
        raw, text, errs = "", "", []
        for attempt in range(1, MAX_REPAIRS + 2):
            raw = llm.complete(self.model, messages, self.a.temperature if self.a.temperature is not None else self.cfg["temperature"],
                               self.a.max_tokens or self.cfg["max_tokens"], stage=self.a.stage, out_path=tgt["out"],
                               training_bound=self.cfg["training_bound"], provenance=self.prov, attempt=attempt)
            if self.dry:
                tgt["out"].parent.mkdir(parents=True, exist_ok=True)
                dry_out = tgt["out"].with_name(tgt["out"].name + ".dry")
                dry_out.write_text(raw)
                return "dry", f"prompt written under {self.out / '_dry'}; placeholder at {dry_out}"
            text, errs = self.verify(tgt, raw)
            if not errs:
                self.install(tgt, text)
                note = f"attempt {attempt}"
                if self.a.stage == "critic":
                    fails = re.findall(r"(?mi)^\s*[-*]?\s*`?(\w+)`?\s*:\s*FAIL", text)
                    note += f"; FAIL items: {', '.join(fails) or 'none'}"
                return "ok", note
            print(f"  {tgt['label']} attempt {attempt}: {len(errs)} problems", file=sys.stderr)
            messages += [{"role": "assistant", "content": raw},
                         {"role": "user", "content": "The file failed these checks:\n" + "\n".join(f"- {e}" for e in errs[:40]) +
                          "\n\nFix every one of them and write the whole corrected file. Output only the file content in one fenced block."}]
        rej = tgt["out"].with_name(tgt["out"].name + ".rejected")
        rej.parent.mkdir(parents=True, exist_ok=True)
        rej.write_text(text or raw)
        rej.with_name(rej.name + ".errors.txt").write_text("\n".join(errs) + "\n")
        return "failed", f"gave up after {MAX_REPAIRS} repairs; last attempt saved as {rej}; remaining: " + "; ".join(errs[:5])


def preflight(a):
    """Model policy, checked before any work: allowlist for training-bound stages, critic family."""
    cfg = llm.load_policy()["stages"][a.stage]
    if a.stage == "critic":
        if not a.judge:
            raise StageError("stage critic needs --judge (the reviewing model); --model names the drafter whose family is excluded")
        llm.check_allowed(a.judge, False)
        drafters = [a.model] if a.model else []
        prov = Path(a.out) / "provenance.jsonl"
        if prov.exists():
            for ln in prov.read_text().splitlines():
                r = json.loads(ln)
                if r.get("stage") not in (None, "critic", "cli") and not r.get("error"):
                    drafters.append(r["model"])
        if not drafters:
            raise StageError("cannot tell which model drafted the work: pass --model, or run where DIR/provenance.jsonl exists")
        llm.check_critic(a.judge, sorted(set(drafters)))
    else:
        if not a.model:
            raise StageError("--model is required")
        llm.check_allowed(a.model, cfg["training_bound"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=STAGES)
    ap.add_argument("--seed", required=True, metavar="SEED.yaml", help="the seed (see seeds/INT-301.seed.yaml)")
    ap.add_argument("--out", required=True, metavar="DIR", help="batch folder; files go to DIR/<CASE>/, provenance to DIR/provenance.jsonl")
    ap.add_argument("--model", help="drafting model: openrouter/<id> | bedrock/<modelId> | dry/<anything>; for critic, the drafter whose family is excluded")
    ap.add_argument("--judge", help="the critic model (stage critic only); must be a different family from the drafter")
    ap.add_argument("--live", metavar="ID", help="only this live scenario (stages live, render, reply, critic)")
    ap.add_argument("--arm", metavar="ARM", help="reply stage: only this arm (right, r1, decoy, ...)")
    ap.add_argument("--revised", default="r1", metavar="TAG", help="revised stage: which revised card to write (default r1)")
    ap.add_argument("--temperature", type=float, help="override the stage default in models.yaml")
    ap.add_argument("--max-tokens", type=int, help="override the stage default in models.yaml")
    ap.add_argument("--mvp", help="path to mvp.py (default: env BENCHBOOK_MVP, then $BENCHBOOK_LABS/ideas/...)")
    a = ap.parse_args(argv)
    try:
        preflight(a)
        st = Stage(a)
        results = []
        for tgt in st.targets():
            status, note = st.run_target(tgt)
            print(f"[{status}] {tgt['label']}: {note}")
            results.append(status)
    except (StageError, llm.LLMError, ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 1 if "failed" in results else 0


if __name__ == "__main__":
    sys.exit(main())
