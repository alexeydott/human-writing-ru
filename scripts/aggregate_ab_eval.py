#!/usr/bin/env python3
"""Aggregate completed A/B eval grading/timing files into benchmark.json."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def grade_pass_rate(data: dict) -> float:
    summary = data.get("summary", {})
    if isinstance(summary, dict) and "pass_rate" in summary:
        return float(summary["pass_rate"])
    results = data.get("assertion_results", [])
    if not results: raise ValueError("grading.json lacks summary.pass_rate and assertion_results")
    return sum(bool(x.get("passed")) for x in results) / len(results)


def stats(values: list[float]) -> dict:
    if not values: return {"count": 0, "mean": None, "stddev": None}
    return {"count": len(values), "mean": round(statistics.fmean(values), 6), "stddev": round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate A/B eval grading.json and timing.json files")
    ap.add_argument("--iteration-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--allow-incomplete", action="store_true")
    args = ap.parse_args()
    iteration = args.iteration_dir.resolve()
    manifest_path = iteration / "run-manifest.json"
    if not manifest_path.exists(): raise SystemExit(f"missing run-manifest.json: {manifest_path}")
    manifest = load_json(manifest_path)

    arms_declared = manifest.get("arms", [])
    if not isinstance(arms_declared, list) or len(set(arms_declared)) != len(arms_declared):
        raise SystemExit("run-manifest arms must be a unique list")
    arm_values = defaultdict(lambda: {"pass_rate": [], "tokens": [], "duration_ms": []})
    case_arm = defaultdict(list)
    run_pass: dict[tuple[str, str, int], float] = {}
    seen_run_keys: set[tuple[str, str, int]] = set()
    missing = []
    errors = []
    completed = 0
    for run in manifest.get("runs", []):
        run_key = (str(run["case_id"]), str(run["arm"]), int(run["run_index"]))
        if run_key in seen_run_keys:
            raise SystemExit(f"duplicate run key in run-manifest: {run_key}")
        seen_run_keys.add(run_key)
        if run_key[1] not in arms_declared:
            raise SystemExit(f"run references undeclared arm: {run_key[1]}")
        grade_path = Path(run["grading_path"]); timing_path = Path(run["timing_path"])
        if not grade_path.is_absolute(): grade_path = iteration / grade_path
        if not timing_path.is_absolute(): timing_path = iteration / timing_path
        key = (run["case_id"], run["arm"])
        if not grade_path.exists() or not timing_path.exists():
            missing.append({"case_id": run["case_id"], "arm": run["arm"], "run_index": run["run_index"], "grading_missing": not grade_path.exists(), "timing_missing": not timing_path.exists()})
            continue
        try:
            g = load_json(grade_path); t = load_json(timing_path)
            pr = grade_pass_rate(g)
            tokens = float(t["total_tokens"]); duration = float(t["duration_ms"])
            if not all(math.isfinite(x) for x in (pr, tokens, duration)):
                raise ValueError("non-finite grading/timing value")
            if not (0.0 <= pr <= 1.0) or tokens < 0 or duration < 0: raise ValueError("out-of-range grading/timing value")
        except Exception as exc:
            errors.append({"case_id": run["case_id"], "arm": run["arm"], "run_index": run["run_index"], "error": str(exc)})
            continue
        arm_values[run["arm"]]["pass_rate"].append(pr)
        arm_values[run["arm"]]["tokens"].append(tokens)
        arm_values[run["arm"]]["duration_ms"].append(duration)
        case_arm[key].append(pr)
        run_pass[run_key] = pr
        completed += 1

    if (missing or errors) and not args.allow_incomplete:
        raise SystemExit(f"evaluation incomplete: missing={len(missing)} errors={len(errors)}; rerun with --allow-incomplete only for diagnostic aggregation")

    arms = {}
    for arm in arms_declared:
        vals = arm_values[arm]
        arms[arm] = {name: stats(vals[name]) for name in ("pass_rate", "tokens", "duration_ms")}

    case_summary = {}
    for (case, arm), vals in sorted(case_arm.items()):
        case_summary.setdefault(case, {})[arm] = stats(vals)

    # Differences are paired by case/run index. Comparing unpaired arm means in
    # an incomplete run can manufacture an apparent improvement if missingness is
    # concentrated on hard cases.
    paired_delta_details = {}
    pass_rate_deltas = {}
    current_keys = {(case, idx) for case, arm, idx in run_pass if arm == "current_skill"}
    for baseline_arm in ("previous_skill", "without_skill"):
        if baseline_arm not in arms_declared or "current_skill" not in arms_declared:
            continue
        baseline_keys = {(case, idx) for case, arm, idx in run_pass if arm == baseline_arm}
        paired = sorted(current_keys & baseline_keys)
        deltas = [run_pass[(case, "current_skill", idx)] - run_pass[(case, baseline_arm, idx)] for case, idx in paired]
        planned_pair_keys = {
            (str(run["case_id"]), int(run["run_index"]))
            for run in manifest.get("runs", []) if run.get("arm") == "current_skill"
        } & {
            (str(run["case_id"]), int(run["run_index"]))
            for run in manifest.get("runs", []) if run.get("arm") == baseline_arm
        }
        detail = stats(deltas)
        detail.update({"paired_runs": len(paired), "planned_pairs": len(planned_pair_keys), "complete_pairs": len(paired) == len(planned_pair_keys)})
        paired_delta_details[f"current_minus_{baseline_arm}"] = detail
        if detail["complete_pairs"] and detail["mean"] is not None:
            pass_rate_deltas[f"current_minus_{baseline_arm}"] = detail["mean"]

    complete = not missing and not errors
    report = {
        "schema_version": 1,
        "iteration": manifest.get("iteration"),
        "planned_runs": len(manifest.get("runs", [])),
        "completed_runs": completed,
        "missing_runs": missing,
        "errors": errors,
        "complete": complete,
        "diagnostic_only": not complete,
        "arms": arms,
        "pass_rate_deltas": pass_rate_deltas,
        "paired_pass_rate_deltas": paired_delta_details,
        "cases": case_summary,
        "scope_note": "Mechanical aggregation only. Deltas are paired by case/run index and are omitted from pass_rate_deltas when pairing is incomplete. Blind pairwise/human judgments remain separate evidence and must not be inferred from assertion pass rate.",
    }
    out = args.output or (iteration / "benchmark.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "planned": report["planned_runs"], "completed": completed, "missing": len(missing), "errors": len(errors)}, ensure_ascii=False))
    return 0 if not errors and (args.allow_incomplete or not missing) else 2


if __name__ == "__main__":
    raise SystemExit(main())
