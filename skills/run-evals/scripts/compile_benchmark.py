#!/usr/bin/env python3
"""
Benchmark Compiler

Reads timing.json and grading.json from each eval subfolder in an iteration
directory and produces a fully-computed benchmark.json — with FILL placeholders
for prose fields (note, prompt_summary, insights) that the agent fills in.

Usage:
    python compile_benchmark.py [path/to/iteration-dir]
    python compile_benchmark.py --check [path/to/iteration-dir]

If no iteration-dir is given, the most recently modified iteration-* folder
under the current working directory is used (searched recursively).

Use --check to report how many FILL prose fields remain in benchmark.json
without recompiling.

Directory structure expected:
    iteration-1/
        eval-1-<name>/
            with_skill/
                timing.json
                grading.json
            without_skill/
                timing.json
                grading.json
        eval-2-<name>/
            ...

Output:
    iteration-1/benchmark.json   (overwrites if exists)
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure Unicode output works on Windows consoles (cp1252 by default).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

REQUIRED_TIMING = {"tokens"}
REQUIRED_GRADING = {"assertion_results", "summary"}


def _num(value, default=0):
    """Treat None/missing as `default`; coerce to int/float as-is."""
    return default if value is None else value


def _find_latest_iteration(search_root: Path) -> Path | None:
    candidates = [p for p in search_root.rglob("iteration-*") if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


# ── File I/O ──────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_keys(data: dict, required: set, path: Path) -> None:
    missing = required - set(data.keys())
    if missing:
        print(f"Error: {path} is missing keys: {', '.join(sorted(missing))}", file=sys.stderr)
        sys.exit(1)


# ── Eval discovery ────────────────────────────────────────────────────────────

def discover_evals(iteration_dir: Path) -> list[Path]:
    """Return eval-* subdirs sorted by the numeric id in the folder name."""
    evals = [d for d in iteration_dir.iterdir() if d.is_dir() and d.name.startswith("eval-")]
    if not evals:
        print(f"Error: no eval-* directories found in {iteration_dir}", file=sys.stderr)
        sys.exit(1)

    def sort_key(p: Path):
        m = re.match(r"eval-(\d+)", p.name)
        return int(m.group(1)) if m else 0

    return sorted(evals, key=sort_key)


def extract_eval_id(folder_name: str) -> int:
    m = re.match(r"eval-(\d+)", folder_name)
    return int(m.group(1)) if m else 0


def extract_iteration(dir_name: str) -> int:
    m = re.search(r"(\d+)", dir_name)
    return int(m.group(1)) if m else 0


# ── Per-run stats ─────────────────────────────────────────────────────────────

def process_run(timing_path: Path, grading_path: Path) -> dict:
    """Extract and derive stats for a single (condition, eval) run."""
    timing = load_json(timing_path)
    grading = load_json(grading_path)
    validate_keys(timing, REQUIRED_TIMING, timing_path)
    validate_keys(grading, REQUIRED_GRADING, grading_path)

    t = timing["tokens"] or {}
    t_input      = _num(t.get("input"))
    t_output     = _num(t.get("output"))
    t_total      = _num(t.get("total"), t_input + t_output)
    t_cache_read = _num(t.get("cache_read"))
    effective_input = t_input - t_cache_read
    cache_eff_pct = round(t_cache_read / t_input * 100, 1) if t_input else 0.0

    # api_calls from model_breakdown (sum all model entries)
    api_calls = 0
    primary_model = timing.get("model") or "unknown"
    for model_data in (timing.get("model_breakdown") or {}).values():
        api_calls += _num((model_data or {}).get("api_calls"))

    return {
        "model": primary_model,
        "host_agent": timing.get("host_agent") or "unknown",
        "host_agent_version": timing.get("host_agent_version"),
        "passed":      grading["summary"]["passed"],
        "failed":      grading["summary"]["failed"],
        "pass_rate":   grading["summary"]["pass_rate"],
        "time_seconds":         round(_num(timing.get("duration_seconds"), 0.0), 3),
        "api_duration_seconds": round(_num(timing.get("api_duration_ms"), 0) / 1000, 3),
        "tokens": {
            "total":              t_total,
            "input":              t_input,
            "output":             t_output,
            "cache_read":         t_cache_read,
            "effective_input":    effective_input,
            "cache_efficiency_pct": cache_eff_pct,
        },
        "api_calls":          api_calls,
        "premium_requests":   _num(timing.get("premium_requests")),
        "context_window_used_pct": _num(t.get("context_window_used_pct"), 0.0),
        "assertion_results":  grading["assertion_results"],
    }


# ── Aggregation helpers ───────────────────────────────────────────────────────

def _mean(values: list) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


def build_run_summary_side(runs: list[dict]) -> dict:
    """Aggregate stats across all eval runs for one condition (with/without skill)."""
    total_passed     = sum(r["passed"] for r in runs)
    total_failed     = sum(r["failed"] for r in runs)
    total_assertions = total_passed + total_failed

    return {
        "pass_rate": {
            "mean":              _mean([r["pass_rate"] for r in runs]),
            "combined":          round(total_passed / total_assertions, 3) if total_assertions else 0.0,
            "total_passed":      total_passed,
            "total_failed":      total_failed,
            "total_assertions":  total_assertions,
        },
        "time_seconds": {
            "mean":              _mean([r["time_seconds"] for r in runs]),
            "api_duration_mean": _mean([r["api_duration_seconds"] for r in runs]),
        },
        "tokens": {
            "total_mean":                  int(_mean([r["tokens"]["total"] for r in runs])),
            "effective_input_mean":        int(_mean([r["tokens"]["effective_input"] for r in runs])),
            "cache_efficiency_mean_pct":   round(_mean([r["tokens"]["cache_efficiency_pct"] for r in runs]), 1),
        },
        "api_calls_mean": _mean([r["api_calls"] for r in runs]),
    }


def build_delta(ws: dict, wos: dict) -> dict:
    def d(a, b): return round(a - b, 3)

    return {
        "pass_rate_mean":              d(ws["pass_rate"]["mean"],     wos["pass_rate"]["mean"]),
        "pass_rate_combined":          d(ws["pass_rate"]["combined"], wos["pass_rate"]["combined"]),
        "time_seconds_mean":           d(ws["time_seconds"]["mean"],  wos["time_seconds"]["mean"]),
        "total_tokens_mean":           int(d(ws["tokens"]["total_mean"],          wos["tokens"]["total_mean"])),
        "effective_input_tokens_mean": int(d(ws["tokens"]["effective_input_mean"],wos["tokens"]["effective_input_mean"])),
        "api_calls_mean":              d(ws["api_calls_mean"],        wos["api_calls_mean"]),
        "note":                        "FILL: one sentence summarising the most important delta (pass rate, time, tokens).",
    }


# ── Assertion comparison ──────────────────────────────────────────────────────

def build_assertion_comparison(eval_id: int, ws_assertions: list, wos_assertions: list) -> list:
    """Match assertions by text across conditions; fall back to index."""
    # Build lookup: text → passed for without_skill
    wos_lookup = {a["text"]: a["passed"] for a in wos_assertions}

    rows = []
    for a in ws_assertions:
        rows.append({
            "eval":          eval_id,
            "assertion":     a["text"],
            "with_skill":    a["passed"],
            "without_skill": wos_lookup.get(a["text"], None),
        })

    # If any without_skill entries didn't match by text, append them
    ws_texts = {a["text"] for a in ws_assertions}
    for a in wos_assertions:
        if a["text"] not in ws_texts:
            rows.append({
                "eval":          eval_id,
                "assertion":     a["text"],
                "with_skill":    None,
                "without_skill": a["passed"],
            })

    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile timing.json + grading.json into benchmark.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("iteration_dir", metavar="iteration-dir", nargs="?", default=None,
                        help="Path to iteration directory (defaults to latest iteration-* under CWD)")
    parser.add_argument("--check", action="store_true",
                        help="Report remaining FILL prose fields without recompiling")
    args = parser.parse_args()

    if args.iteration_dir:
        iteration_dir = Path(args.iteration_dir)
    else:
        iteration_dir = _find_latest_iteration(Path.cwd())
        if not iteration_dir:
            print("Error: no iteration-* directory found under CWD; pass one explicitly.", file=sys.stderr)
            sys.exit(1)
        print(f"Using latest iteration: {iteration_dir}")

    if not iteration_dir.is_dir():
        print(f"Error: {iteration_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.check:
        bench_path = iteration_dir / "benchmark.json"
        if not bench_path.exists():
            print(f"Error: {bench_path} not found. Run compile first.", file=sys.stderr)
            sys.exit(1)
        raw = bench_path.read_text(encoding="utf-8")
        fill_count = raw.count('"FILL:') + raw.count("'FILL:")
        print(f"{bench_path}: {fill_count} FILL placeholder(s) remaining")
        sys.exit(0 if fill_count == 0 else 1)

    iteration_num = extract_iteration(iteration_dir.name)
    eval_dirs     = discover_evals(iteration_dir)

    print(f"Found {len(eval_dirs)} eval(s): {', '.join(d.name for d in eval_dirs)}")

    evals_out         = []
    ws_runs_all       = []
    wos_runs_all      = []
    assertion_comparison = []
    model             = "unknown"
    host_agent        = "unknown"
    host_agent_version: str | None = None

    for eval_dir in eval_dirs:
        eval_id   = extract_eval_id(eval_dir.name)
        eval_name = eval_dir.name  # full folder name is the canonical eval name

        ws_timing_path  = eval_dir / "with_skill"    / "timing.json"
        ws_grading_path = eval_dir / "with_skill"    / "grading.json"
        wos_timing_path = eval_dir / "without_skill" / "timing.json"
        wos_grading_path= eval_dir / "without_skill" / "grading.json"

        for p in (ws_timing_path, ws_grading_path, wos_timing_path, wos_grading_path):
            if not p.exists():
                print(f"Error: expected file not found: {p}", file=sys.stderr)
                sys.exit(1)

        ws  = process_run(ws_timing_path,  ws_grading_path)
        wos = process_run(wos_timing_path, wos_grading_path)

        model = ws["model"]  # use last non-unknown
        if ws.get("host_agent") and ws["host_agent"] != "unknown":
            host_agent = ws["host_agent"]
        if ws.get("host_agent_version"):
            host_agent_version = ws["host_agent_version"]

        evals_out.append({
            "id":             eval_id,
            "name":           eval_name,
            "prompt_summary": f"FILL: one sentence describing the eval prompt scenario for {eval_name}.",
            "assertions_total": ws["passed"] + ws["failed"],
            "with_skill": {
                "passed":               ws["passed"],
                "failed":               ws["failed"],
                "pass_rate":            ws["pass_rate"],
                "time_seconds":         ws["time_seconds"],
                "api_duration_seconds": ws["api_duration_seconds"],
                "tokens":               ws["tokens"],
                "api_calls":            ws["api_calls"],
                "premium_requests":     ws["premium_requests"],
                "context_window_used_pct": ws["context_window_used_pct"],
            },
            "without_skill": {
                "passed":               wos["passed"],
                "failed":               wos["failed"],
                "pass_rate":            wos["pass_rate"],
                "time_seconds":         wos["time_seconds"],
                "api_duration_seconds": wos["api_duration_seconds"],
                "tokens":               wos["tokens"],
                "api_calls":            wos["api_calls"],
                "premium_requests":     wos["premium_requests"],
                "context_window_used_pct": wos["context_window_used_pct"],
            },
        })

        ws_runs_all.append(ws)
        wos_runs_all.append(wos)

        assertion_comparison.extend(
            build_assertion_comparison(eval_id, ws["assertion_results"], wos["assertion_results"])
        )

    ws_summary  = build_run_summary_side(ws_runs_all)
    wos_summary = build_run_summary_side(wos_runs_all)
    delta       = build_delta(ws_summary, wos_summary)

    benchmark = {
        "iteration":    iteration_num,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "host_agent":         host_agent,
        "host_agent_version": host_agent_version,
        "model":        model,
        "note":         "FILL: 1–2 sentences of context about this benchmark run (eval set, intent, anything notable).",
        "evals":        evals_out,
        "run_summary": {
            "with_skill":    ws_summary,
            "without_skill": wos_summary,
            "delta":         delta,
        },
        "assertion_comparison": assertion_comparison,
        "insights": {
            "skill_improvement":  "FILL: overall quality improvement with_skill vs baseline (pass rate delta, patterns).",
            "shared_failure":     "FILL: assertions that failed in ALL runs (both conditions, all evals). Identify root cause.",
            "token_tradeoff":     "FILL: token usage comparison — effective input, cache efficiency, total.",
            "wall_clock_tradeoff":"FILL: wall-clock and API duration comparison — why the gap exists.",
            "cache_efficiency":   "FILL: cache hit rate observations across runs.",
        },
    }

    out_path = iteration_dir / "benchmark.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(benchmark, f, indent=4, ensure_ascii=False)

    # ── Summary for agent ──────────────────────────────────────────────────────
    fill_count = 2 + len(evals_out) + 5  # note + delta.note + prompt_summaries + insights
    print(f"\n✔ benchmark.json written to: {out_path.resolve()}")
    print(f"\nAgent needs to fill in {fill_count} prose fields:")
    print(f"  • note                          — 1-2 sentences of run context")
    print(f"  • run_summary.delta.note        — 1 sentence on most important delta")
    for e in evals_out:
        print(f"  • evals[{e['id']}].prompt_summary  — 1 sentence describing {e['name']}")
    print(f"  • insights.skill_improvement    — pass rate patterns")
    print(f"  • insights.shared_failure       — assertions that failed everywhere")
    print(f"  • insights.token_tradeoff       — token usage comparison")
    print(f"  • insights.wall_clock_tradeoff  — timing comparison")
    print(f"  • insights.cache_efficiency     — cache hit observations")
    print()
    print("Run generate_dashboard.py after filling in prose fields.")


if __name__ == "__main__":
    main()
