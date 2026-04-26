"""
eval_ci.py — Offline RAGAS Evaluation Script for CI/CD Integration
===================================================================

Purpose
-------
Runs every test case in eval_ground_truth.json through the live RAG pipeline
and scores each answer using the RAGAS evaluation framework.  Exits with a
non-zero code when any metric falls below its configured threshold, causing
pull-request CI checks to fail.

Usage
-----
    # Run all cases (default):
    python eval_ci.py

    # Run a specific category only:
    python eval_ci.py --category credit-card

    # Run a single case by ID:
    python eval_ci.py --id cc-001

    # Override metric thresholds (comma-separated key=value pairs):
    python eval_ci.py --thresholds faithfulness=0.8,answer_relevancy=0.75

    # Save a detailed JSON report to a custom path:
    python eval_ci.py --report ci_report.json

    # Dry-run: show cases that would run without calling the LLM:
    python eval_ci.py --dry-run

Exit Codes
----------
    0  All cases passed all metric thresholds.
    1  One or more cases failed at least one metric threshold.
    2  Script-level error (bad config, missing dependency, etc.).

CI Integration
--------------
GitHub Actions: see .github/workflows/rag_eval.yml
Outputs: eval_ci_report.json (JSON artifact), stdout summary table.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Bootstrap — add project root to path so imports work whether the script is
# invoked from the repo root or from a sub-directory.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from config import LOG_LEVEL
from prompts import REGISTRY_VERSION

# ---------------------------------------------------------------------------
# Logging — quiet during CI unless DEBUG is requested
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, os.getenv("CI_LOG_LEVEL", "WARNING"), logging.WARNING),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("eval_ci")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GROUND_TRUTH_FILE = PROJECT_ROOT / "eval_ground_truth.json"
DEFAULT_REPORT_FILE = PROJECT_ROOT / "eval_ci_report.json"

# Metric display names → key used in RAGAS scores dict
_METRIC_KEYS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]

# ANSI colour helpers (suppressed in non-TTY / CI environments)
_USE_COLOUR = sys.stdout.isatty()

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text

_GREEN  = lambda t: _c(t, "32")
_RED    = lambda t: _c(t, "31")
_YELLOW = lambda t: _c(t, "33")
_BOLD   = lambda t: _c(t, "1")


# ---------------------------------------------------------------------------
# Lazy pipeline import — keeps the CI script importable even if optional
# dependencies are missing (useful for --dry-run and unit testing).
# ---------------------------------------------------------------------------
def _load_pipeline():
    """Import and return a singleton RAGPipeline instance."""
    from rag_pipeline import RAGPipeline
    logger.info("Initialising RAGPipeline …")
    return RAGPipeline()


def _load_evaluator(pipeline):
    """Return the RAGASEvaluator from an already-initialised pipeline."""
    if pipeline.evaluator is None:
        raise RuntimeError(
            "RAGAS evaluator is not available. "
            "Check that ragas is installed and all API keys are set."
        )
    return pipeline.evaluator


# ---------------------------------------------------------------------------
# Ground truth loading
# ---------------------------------------------------------------------------

def load_ground_truth(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Ground truth file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Basic schema validation
    for case in data.get("cases", []):
        for key in ("id", "role", "question", "ground_truth"):
            if key not in case:
                raise ValueError(f"Test case missing required field '{key}': {case}")
    return data


def filter_cases(cases: list[dict], category: Optional[str], case_id: Optional[str]) -> list[dict]:
    if case_id:
        filtered = [c for c in cases if c["id"] == case_id]
        if not filtered:
            raise ValueError(f"No test case with id='{case_id}' found in ground truth file.")
        return filtered
    if category:
        filtered = [c for c in cases if c.get("category") == category or c.get("role") == category]
        if not filtered:
            raise ValueError(f"No test cases with category='{category}' found.")
        return filtered
    return cases


# ---------------------------------------------------------------------------
# Core evaluation runner
# ---------------------------------------------------------------------------

def run_case(
    case: dict,
    pipeline,
    evaluator,
    thresholds: dict[str, float],
) -> dict:
    """
    Run one test case end-to-end:
      1. Query the RAG pipeline.
      2. Score with RAGAS (full 6-metric suite because ground_truth is present).
      3. Compare scores against thresholds.

    Returns a result dict with keys:
        id, role, question, answer, scores, passed, failures, latency_s, error
    """
    case_id  = case["id"]
    role     = case["role"]
    question = case["question"]
    gt       = case["ground_truth"]

    result: dict = {
        "id": case_id,
        "category": case.get("category", role),
        "role": role,
        "question": question,
        "ground_truth": gt,
        "answer": None,
        "scores": {},
        "passed": False,
        "failures": [],
        "latency_s": None,
        "error": None,
    }

    t0 = time.monotonic()
    try:
        # --- RAG query -------------------------------------------------------
        rag_response = pipeline.query(
            question=question,
            username="__ci__",
            user_roles=[role],
            ground_truth=gt,
            run_eval=True,          # trigger RAGAS inside pipeline
        )
        result["latency_s"] = round(time.monotonic() - t0, 2)

        if not rag_response.get("success"):
            err = rag_response.get("answer", "RAG pipeline returned success=False")
            result["error"] = err
            result["failures"].append(f"Pipeline error: {err}")
            return result

        result["answer"] = rag_response.get("primary_answer", "")

        # --- extract RAGAS scores from pipeline response ---------------------
        eval_result = rag_response.get("primary_evaluation") or {}
        scores: dict[str, float] = eval_result.get("scores", {})
        result["scores"] = scores
        result["eval_success"] = eval_result.get("success", False)
        result["eval_error"]   = eval_result.get("error")

        if not result["eval_success"]:
            result["error"] = f"RAGAS evaluation failed: {result['eval_error']}"
            result["failures"].append(result["error"])
            return result

        # --- threshold checks ------------------------------------------------
        failures: list[str] = []
        for metric, threshold in thresholds.items():
            score = scores.get(metric)
            if score is None:
                # Metric was not computed (e.g., no ground_truth for recall).
                # We already have ground_truth here, so log a warning.
                logger.warning(
                    "Case %s: metric '%s' not present in scores (may not be "
                    "supported by current RAGAS version).",
                    case_id, metric,
                )
                continue
            if score < threshold:
                failures.append(
                    f"{metric}={score:.4f} < threshold {threshold:.4f}"
                )

        result["failures"] = failures
        result["passed"]   = len(failures) == 0

    except Exception as exc:
        result["latency_s"] = round(time.monotonic() - t0, 2)
        result["error"]     = str(exc)
        result["failures"].append(f"Unhandled exception: {exc}")
        logger.exception("Case %s raised an exception.", case_id)

    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_report(
    results: list[dict],
    thresholds: dict[str, float],
    gt_meta: dict,
    cli_args: argparse.Namespace,
) -> dict:
    total    = len(results)
    passed   = sum(1 for r in results if r["passed"])
    failed   = total - passed
    pass_pct = (passed / total * 100) if total else 0.0

    # Per-metric averages (over cases where the metric was computed)
    metric_sums:   dict[str, float] = {}
    metric_counts: dict[str, int]   = {}
    for r in results:
        for m, v in r.get("scores", {}).items():
            metric_sums[m]   = metric_sums.get(m, 0.0) + v
            metric_counts[m] = metric_counts.get(m, 0) + 1
    avg_scores = {
        m: round(metric_sums[m] / metric_counts[m], 4)
        for m in metric_sums
    }

    return {
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
        "prompt_registry_version": REGISTRY_VERSION,
        "ground_truth_version": gt_meta.get("_meta", {}).get("version", "unknown"),
        "ground_truth_file": str(GROUND_TRUTH_FILE),
        "thresholds_applied": thresholds,
        "summary": {
            "total_cases": total,
            "passed": passed,
            "failed": failed,
            "pass_rate_pct": round(pass_pct, 1),
        },
        "average_scores": avg_scores,
        "results": results,
        "cli": vars(cli_args),
    }


def save_report(report: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved → {path}")


def print_summary(report: dict) -> None:
    """Print a human-readable table to stdout."""
    summary = report["summary"]
    avgs    = report["average_scores"]
    results = report["results"]

    print()
    print(_BOLD("=" * 72))
    print(_BOLD("  RAG CI Evaluation Report"))
    print(f"  Generated : {report['report_generated_at']}")
    print(f"  Prompt registry v{report['prompt_registry_version']} | "
          f"Ground truth v{report['ground_truth_version']}")
    print(_BOLD("=" * 72))

    # Summary line
    status_str = _GREEN("PASSED") if summary["failed"] == 0 else _RED("FAILED")
    print(
        f"\n  Overall : {status_str}  "
        f"{summary['passed']}/{summary['total_cases']} cases passed "
        f"({summary['pass_rate_pct']:.1f}%)"
    )

    # Average scores
    if avgs:
        print("\n  Average RAGAS Scores:")
        for metric, val in avgs.items():
            threshold = report["thresholds_applied"].get(metric)
            below = threshold is not None and val < threshold
            val_str = f"{val:.4f}"
            if below:
                val_str = _RED(val_str + f" < {threshold}")
            else:
                val_str = _GREEN(val_str)
            print(f"    {metric:<30} {val_str}")

    # Per-case table
    print()
    col = "{:<12} {:<15} {:<8} {:<8} {:<8} {:<8} {:<10} {}"
    header = col.format(
        "ID", "Category", "Faith.", "Relev.", "Prec.", "Recall", "Latency", "Status"
    )
    print(_BOLD(header))
    print("-" * 80)

    for r in results:
        sc = r.get("scores", {})
        faith   = f"{sc.get('faithfulness', float('nan')):.3f}"
        relev   = f"{sc.get('answer_relevancy', float('nan')):.3f}"
        prec    = f"{sc.get('context_precision', float('nan')):.3f}"
        recall  = f"{sc.get('context_recall', float('nan')):.3f}"
        latency = f"{r.get('latency_s', '?')}s"
        if r["passed"]:
            status = _GREEN("PASS")
        elif r.get("error"):
            status = _RED("ERROR")
        else:
            status = _RED("FAIL")

        row = col.format(
            r["id"], r.get("category", r["role"])[:14],
            faith, relev, prec, recall, latency, status
        )
        print(row)

        if not r["passed"] and r.get("failures"):
            for msg in r["failures"]:
                print(f"    {_RED('✗')} {msg}")
        if r.get("error") and not r.get("failures"):
            print(f"    {_RED('!')} {r['error']}")

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--category",
        metavar="CATEGORY",
        help="Run only cases with this category (e.g. credit-card, banking, auto-loan).",
    )
    p.add_argument(
        "--id",
        metavar="CASE_ID",
        help="Run a single case by its ID (e.g. cc-001).",
    )
    p.add_argument(
        "--thresholds",
        metavar="KEY=VAL,...",
        help=(
            "Override metric thresholds from the ground-truth file. "
            "Example: faithfulness=0.8,answer_relevancy=0.75"
        ),
    )
    p.add_argument(
        "--report",
        metavar="PATH",
        default=str(DEFAULT_REPORT_FILE),
        help=f"Path for the JSON report output (default: {DEFAULT_REPORT_FILE}).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List cases that would run without invoking the pipeline.",
    )
    p.add_argument(
        "--ground-truth",
        metavar="PATH",
        default=str(GROUND_TRUTH_FILE),
        help=f"Path to ground truth JSON file (default: {GROUND_TRUTH_FILE}).",
    )
    return p.parse_args()


def parse_threshold_overrides(raw: Optional[str], defaults: dict) -> dict[str, float]:
    """Merge CLI threshold overrides into the defaults from the GT file."""
    result = dict(defaults)
    if raw:
        for pair in raw.split(","):
            pair = pair.strip()
            if "=" not in pair:
                raise ValueError(f"Invalid threshold override '{pair}' (expected key=value).")
            k, v = pair.split("=", 1)
            result[k.strip()] = float(v.strip())
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    # --- Load ground truth ---------------------------------------------------
    gt_path = Path(args.ground_truth)
    try:
        gt_data = load_ground_truth(gt_path)
    except (FileNotFoundError, ValueError) as exc:
        print(_RED(f"ERROR: {exc}"), file=sys.stderr)
        return 2

    all_cases  = gt_data.get("cases", [])
    gt_meta    = gt_data
    thresholds = parse_threshold_overrides(
        args.thresholds,
        gt_data.get("_meta", {}).get("thresholds", {
            "faithfulness": 0.7,
            "answer_relevancy": 0.7,
        }),
    )

    # --- Filter cases --------------------------------------------------------
    try:
        cases = filter_cases(all_cases, args.category, args.id)
    except ValueError as exc:
        print(_RED(f"ERROR: {exc}"), file=sys.stderr)
        return 2

    print(f"\n{_BOLD('RAG CI Evaluator')} — {len(cases)} case(s) selected")
    print(f"Ground truth : {gt_path}")
    print(f"Thresholds   : {thresholds}")

    # --- Dry run -------------------------------------------------------------
    if args.dry_run:
        print("\nDry-run mode — no LLM calls will be made.\n")
        for c in cases:
            print(f"  [{c['id']}] ({c.get('category', c['role'])}) {c['question'][:80]}")
        print(f"\n{len(cases)} case(s) would run.")
        return 0

    # --- Load pipeline -------------------------------------------------------
    try:
        print("\nInitialising pipeline … (this may take a few seconds)\n")
        pipeline  = _load_pipeline()
        evaluator = _load_evaluator(pipeline)
    except Exception as exc:
        print(_RED(f"ERROR initialising pipeline: {exc}"), file=sys.stderr)
        logger.exception("Pipeline init failed.")
        return 2

    # --- Run cases -----------------------------------------------------------
    results: list[dict] = []
    for i, case in enumerate(cases, 1):
        print(
            f"  [{i}/{len(cases)}] {case['id']} "
            f"({case.get('category', case['role'])}) … ",
            end="",
            flush=True,
        )
        result = run_case(case, pipeline, evaluator, thresholds)
        results.append(result)

        if result["passed"]:
            print(_GREEN("PASS"))
        elif result.get("error"):
            print(_RED(f"ERROR: {result['error'][:60]}"))
        else:
            print(_RED(f"FAIL — {'; '.join(result['failures'])[:80]}"))

    # --- Build and save report -----------------------------------------------
    report      = build_report(results, thresholds, gt_meta, args)
    report_path = Path(args.report)
    save_report(report, report_path)
    print_summary(report)

    # --- Exit code -----------------------------------------------------------
    failed = report["summary"]["failed"]
    if failed > 0:
        print(_RED(f"  {failed} case(s) failed. CI check FAILED.\n"))
        return 1

    print(_GREEN("  All cases passed. CI check PASSED.\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
