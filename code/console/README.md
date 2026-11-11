# Benchbook research console

A local web app over the repo's files, for Peter: observability over the whole research effort (data readiness,
scenarios, traces, answer keys, runs, measurements, prompts, operators, outstanding work), the human solver and
review queue, and sign-off. Built 2026-11-11.

## Start

```bash
scripts/console.sh                 # or: PYTHONPATH=code .venv/bin/python -m console --port 8765
```

It binds to **127.0.0.1:8765 only** (port 8000 is vLLM). Nothing is exposed to the internet and no security group
changes are needed. The page makes no external network requests.

## Open it from your laptop

- **VS Code / Cursor (Remote-SSH):** the editor usually offers "Port 8765 is available" when the server starts. If
  not, open the **Ports** tab next to the terminal, **Forward a Port**, enter `8765`. Then open
  <http://localhost:8765> in your normal browser.
- **Plain SSH:** `ssh -L 8765:localhost:8765 ubuntu@18.211.62.112`, then <http://localhost:8765>.

## Pages

| Page | URL | What |
|---|---|---|
| Home | `/` | Readiness funnel, recent runs (live progress), latest measurements, queue size |
| Data readiness | `/funnel`, `/eligibility` | Corpus docs → anchors → eligible → option-matched → derived pair cases → traces → pair cells → runs → exports, with what blocks each stage |
| Scenarios | `/scenarios?family=…&op=…&bucket=…` | Filter by family, domain, split, held-out, status, tier, role, operator/mode, bucket, tag, trace; any filter opens as a batch |
| Scenario | `/scenario/<id>` | Frame, options (gold marked), facts with source excerpts, considerations, reasoning, flip conditions, before/after vs parent, lineage steps (gates, annotations, delta), derived scenarios, eval runs that used it, sign-off |
| Trace | `/scenario/<id>/trace?key=1` | Chat view with fact and option spans highlighted, and the answer key the eval scores against |
| Runs | `/runs`, `/run?run=results/transfer/<run>` | Per run: results per arm, data used (dataset manifest hash check), how the served cases were derived, prompts used, and what changed since the previous run (config diff, pipeline commits, data files modified) |
| Samples | `/run/samples?run=…&arm=flip&wrong=1`, `/run/sample?run=…&sid=…&prompt=1` | Each reply: verdict, raw reply, scores, judge details, and the exact prompt rebuilt with the current code |
| Measurements | `/measurements`, `/doc?path=…` | M-files and generated views, rendered |
| Prompts | `/prompts`, `/prompt?path=…`, `/prompt/diff?a=…&b=…` | Every prompt file, the code that loads it, runs that used it, diffs against saved versions |
| Operators | `/operators`, `/operators/analytics` | The five operators, built modes, gates, annotations, recipes, store counts, live analytics |
| Outstanding work | `/outstanding` | `docs/OUTSTANDING.md` |
| Notes | `/notes?which=observations|risks|priorities` | Observations log, risk register, V2 priorities |
| Sign-off | `/signoff` | What awaits sign-off (batches, completed runs, pending reviews) and what has been signed |
| Batches | `/batches`, `/batch/<id>` | Operator runs, dataset versions, or `filter:<query>`: bucket counts, gate failures, shortcut-cue table, random spot-check sample with full context, sign-off |
| Queue | `/queue`, `/queue/<task>` | Human solver tasks (blind `verdict`, `condition_holds`) and `review` spot-checks; keyboard: a/r/e, 1-9, y/n, c, → |

Global search: the box at top left (`/` focuses it) finds scenario ids, families, titles, runs and measurements.

## Where answers go

- Tasks: `data/store/queue/<task_id>.yaml` (`pipeline.ops.queue.enqueue`; the solver's `human` backend writes them).
  Queue spot-checks: `python -m pipeline.ops enqueue-review --inputs ids.txt`.
- Answers and sign-offs: append-only `data/labels/labels.jsonl`. The last line for a task or target counts; earlier
  lines stay as the record. Source data is never edited. Both paths are in `.gitignore`.

## Code

`app.py` (routes), `data.py` (read-only views over the files; indexes cached, refreshed every 2 min or via
`/refresh`), `templates/`, `static/`, `tests/test_console_offline.py`.
