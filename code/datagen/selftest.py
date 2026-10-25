#!/usr/bin/env python3
"""Offline self-test for the datagen package: python3 selftest.py [--mvp PATH]

Covers the model allowlist and critic-family rule, spec-section extraction, dry runs of all six stages
(every prompt slot resolves), the repair loop and install path with a scripted fake backend, the
OpenRouter request shape against a local server, and check_batch on a copy of the worked examples.
Needs the examples under $BENCHBOOK_LABS (default /home/claude/bb/benchbook-labs); skips what it cannot find.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_batch  # noqa: E402
import llm  # noqa: E402
import run_stage  # noqa: E402
from bbcommon import HERE, examples_dir  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    print(("ok    " if cond else "FAIL  ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAILED.append(name)


def refused(model, tb=True):
    try:
        llm.check_allowed(model, tb)
        return False
    except llm.ModelRefused:
        return True


def test_policy():
    check("gpt-oss allowed", not refused("openrouter/openai/gpt-oss-120b"))
    check("bedrock gpt-oss allowed", not refused("bedrock/openai.gpt-oss-120b-1:0"))
    check("gemma-4, mistral, olmo allowed", not any(refused(m) for m in (
        "openrouter/google/gemma-4-27b-it", "openrouter/mistralai/mistral-small-3.2", "openrouter/allenai/olmo-3-32b")))
    check("claude, closed gpt, llama refused", all(refused(m) for m in (
        "openrouter/anthropic/claude-sonnet-4", "bedrock/anthropic.claude-3-haiku-20240307-v1:0",
        "openrouter/openai/gpt-4o", "openrouter/openai/o3", "openrouter/meta-llama/llama-3.3-70b")))
    check("non-training-bound stage may use claude", not refused("openrouter/anthropic/claude-sonnet-4", tb=False))
    try:
        llm.check_critic("openrouter/openai/gpt-4o", ["openrouter/openai/gpt-oss-120b"])
        check("critic from the drafter's lineage refused", False)
    except llm.ModelRefused:
        check("critic from the drafter's lineage refused", True)
    llm.check_critic("openrouter/mistralai/mistral-large", ["openrouter/openai/gpt-oss-120b"])
    check("critic from another family accepted", True)


def test_text_helpers():
    spec = (examples_dir() / "templates" / "DATAGEN-SPEC.md").read_text()
    s3 = run_stage.spec_sections(spec, ["3"])
    check("section 3 includes 3.1-3.4", all(x in s3 for x in ("3.1 Variant types", "3.4 Gold and controls")) and "## 4." not in s3)
    s34 = run_stage.spec_sections(spec, ["3.4"])
    check("section 3.4 alone", s34.startswith("### 3.4") and "3.1" not in s34)
    check("fence extraction", run_stage.extract_block("note\n```yaml\na: 1\n```\ntrailing") == "a: 1\n"
          and run_stage.extract_block("````\n```\nx\n```\n````") == "```\nx\n```\n")
    check("unfenced text falls back to the whole text", run_stage.extract_block("a: 1") == "a: 1\n")


def stage_args(tmp, stage, seed, model, **kw):
    a = ["python", stage, "--seed", str(seed), "--out", str(tmp), "--model", model]
    for k, v in kw.items():
        a += [f"--{k}", str(v)]
    return a[1:]


def test_dry_all_stages(tmp):
    seed = HERE / "seeds" / "INT-301.seed.yaml"
    with contextlib.redirect_stdout(io.StringIO()):
        codes = [run_stage.main(stage_args(tmp, st, seed, "dry/gpt-oss-120b")) for st in run_stage.STAGES[:-1]]
        codes.append(run_stage.main(stage_args(tmp, "critic", seed, "dry/gpt-oss-120b", judge="dry/mistral-large")))
    check("dry run of all six stages exits 0", codes == [0] * 6, codes)
    prompts = list((tmp / "_dry").glob("*.prompt.md"))
    import re
    left = [p.name for p in prompts if re.search(r"(?<!\{)\{[A-Z][A-Z0-9_]*\}(?!\})", p.read_text())]
    check("no unresolved slots in any prompt", prompts and not left, left)
    check("every prompt ends with the one-block instruction",
          all(p.read_text().rstrip().endswith("Output only the file content in one fenced block.") for p in prompts))
    check("critic stage refuses a same-family judge",
          run_stage.main(stage_args(tmp, "critic", seed, "dry/gpt-oss-120b", judge="dry/gpt-oss-20b")) == 2)
    check("training-bound stage refuses claude", run_stage.main(stage_args(tmp, "reference", seed, "openrouter/anthropic/claude-x")) == 2)
    crit = (HERE / "prompts" / "critic.md").read_text()
    check("critic prompt lists every rubric item", all(f"`{k}`" in crit for k in run_stage.CRITIC_ITEMS if k != "overall"))
    prov = [json.loads(x) for x in (tmp / "provenance.jsonl").read_text().splitlines()]
    check("provenance records carry model, family, stage, hash", all(r["model"] and r["family"] and r["stage"] and r["prompt_sha256"] for r in prov))


def test_repair_and_install(tmp):
    ex = examples_dir()
    lab = ex / "AUT-001"
    if not lab.exists():
        print("skip  repair loop (examples not found)")
        return
    case = tmp / "AUT-001"
    case.mkdir(parents=True)
    ref_text = (lab / "AUT-001.reference.yaml").read_text()
    shutil.copy(lab / "AUT-001.reference.yaml", case)
    shutil.copy(lab / "AUT-101.live.yaml", case)
    seed = tmp / "seed.yaml"
    seed.write_text(yaml.safe_dump({"case": "AUT-001", "assignment": {}, "lives": [{"id": "AUT-101", "variant": "cross"}]}))
    model = "fake/gpt-oss-test"
    script = []
    llm.BACKENDS["fake"] = lambda bare, messages, temperature, max_tokens, ctx: (script.pop(0) if script else "", {})
    trace = (lab / "AUT-101.trace.json").read_text()
    reply = (lab / "AUT-101.reply.json").read_text()
    # render: first answer is broken JSON, second is the worked example's trace
    script[:] = ["```json\n{not json\n```", f"```json\n{trace}\n```"]
    code = run_stage.main(stage_args(tmp, "render", seed, model, live="AUT-101"))
    check("render: repair loop recovers and installs", code == 0 and (case / "AUT-101.trace.json").exists() and (case / "AUT-101.trace.md").exists())
    msgs = [json.loads(x) for x in (tmp / "provenance.jsonl").read_text().splitlines() if '"fake/gpt-oss-test"' in x]
    check("two model calls were logged for the repair", len(msgs) == 2 and msgs[1]["attempt"] == 2)
    # reply: right arm
    script[:] = [f"```json\n{reply}\n```"]
    code = run_stage.main(stage_args(tmp, "reply", seed, model, live="AUT-101"))
    check("reply: passes the acceptance checks and installs", code == 0 and (case / "AUT-101.reply.json").exists())
    # a second install archives the first
    script[:] = [f"```json\n{reply}\n```"]
    run_stage.main(stage_args(tmp, "reply", seed, model, live="AUT-101"))
    check("a replaced file goes to versions/", len(list((case / "versions").glob("AUT-101.reply.*.json"))) == 1)
    # a reply that never passes is rejected, not installed
    bad = json.loads(reply)
    bad["tool_calls"] = [{"name": "vessel.depart", "arguments": {"waypoint": "x"}}]
    script[:] = [f"```json\n{json.dumps(bad)}\n```"] * 3
    before = (case / "AUT-101.reply.json").read_text()
    code = run_stage.main(stage_args(tmp, "reply", seed, model, live="AUT-101"))
    check("a failing reply is saved as .rejected and never installed",
          code == 1 and (case / "AUT-101.reply.json.rejected").exists() and (case / "AUT-101.reply.json").read_text() == before)
    check("a failing reply stops after two repairs", not script)
    # reference with an unfixable option set (8-9 word options) fails on balance
    script[:] = [f"```yaml\n{ref_text.replace('id: AUT-001', 'id: AUT-001', 1)}\n```"] * 3
    seed2 = tmp / "seed2.yaml"
    seed2.write_text(yaml.safe_dump({"case": "AUT-001", "assignment": {"longest": "B", "shortest": "A"}}))
    check("reference stage rejects wrong drafted_by, balance and caps",
          run_stage.main(stage_args(tmp, "reference", seed2, model)) == 1)
    errs = (case / "AUT-001.reference.yaml.rejected.errors.txt").read_text()
    check("the error list names the balance and drafted_by problems", "drafted_by" in errs and "option lengths outside" in errs, errs[:200])


def test_openrouter_shape(tmp):
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen["auth"] = self.headers.get("Authorization")
            out = json.dumps({"choices": [{"message": {"content": "hello"}}], "usage": {"total_tokens": 3}}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    old = (llm.OPENROUTER_URL, dict(os.environ))
    llm.OPENROUTER_URL = f"http://127.0.0.1:{srv.server_port}/api/v1/chat/completions"
    os.environ.update({"OPENROUTER_API_KEY": "test-key", "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"})
    try:
        out = llm.complete("openrouter/openai/gpt-oss-120b", [{"role": "user", "content": "hi"}], 0.2, 50, stage="t",
                           training_bound=True, provenance=tmp / "p.jsonl")
    finally:
        llm.OPENROUTER_URL = old[0]
        os.environ.clear()
        os.environ.update(old[1])
        srv.shutdown()
    check("openrouter: reply text returned", out == "hello")
    check("openrouter: data_collection deny, model id and bearer key sent",
          seen["body"].get("provider") == {"data_collection": "deny"} and seen["body"]["model"] == "openai/gpt-oss-120b"
          and seen["auth"] == "Bearer test-key")
    check("openrouter: the key is not written to provenance", "test-key" not in (tmp / "p.jsonl").read_text())
    for var in ("BENCHBOOK_AWS_REGION", "BENCHBOOK_AWS_PROFILE"):
        os.environ.pop(var, None)
    try:
        llm.complete("bedrock/openai.gpt-oss-120b-1:0", [{"role": "user", "content": "hi"}], provenance=tmp / "p.jsonl")
        check("bedrock: refuses without region and profile", False)
    except llm.LLMError as e:
        check("bedrock: refuses without region and profile (no default credential chain)", "never used" in str(e))


def test_check_batch(tmp, mvp):
    ex = examples_dir()
    if not (ex / "AGT-201").exists():
        print("skip  check_batch (examples not found)")
        return
    shutil.copytree(ex / "AGT-201", tmp / "AGT-201")
    res = check_batch.run(str(tmp), [], mvp)
    row = {r["id"]: r for r in res["lives"]}["AGT-201-v01"]
    check("check_batch scores the right-card and decoy arms of AGT-201-v01",
          row["arms"]["right"]["ok"] and row["arms"]["decoy"]["ok"] and row["words"] and 0.10 <= row["fact_share"] <= 0.25, row)
    kinds = {i["kind"] for i in res["issues"] if i["level"] == "error"}
    check("check_batch flags the missing revised card", "revised-card" in kinds)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mvp", help="path to mvp.py")
    a = ap.parse_args()
    test_policy()
    test_text_helpers()
    for fn in (test_dry_all_stages, test_repair_and_install, test_openrouter_shape):
        with tempfile.TemporaryDirectory() as d:
            fn(Path(d))
    with tempfile.TemporaryDirectory() as d:
        test_check_batch(Path(d), a.mvp)
    print("\nALL PASSED" if not FAILED else f"\n{len(FAILED)} FAILED: {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
