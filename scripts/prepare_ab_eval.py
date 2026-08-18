#!/usr/bin/env python3
"""Prepare a reproducible multi-run generative A/B evaluation workspace.

This script does not invoke an LLM. It materializes the run plan that an agent
runtime should execute in clean contexts, keeping prompts/arms/output locations
stable and machine-readable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVALS = ROOT / "evals/evals.json"
DEFAULT_ARMS = ("current_skill", "previous_skill", "without_skill")


def safe_id(value: str) -> str:
    out = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value).strip("-")
    if not out:
        raise ValueError(f"invalid empty-safe id from {value!r}")
    return out


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_eval_input(ref: str, evals_path: Path) -> Path:
    raw = Path(ref)
    candidates = [raw] if raw.is_absolute() else [ROOT / raw, evals_path.parent / raw]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    raise SystemExit(f"eval input file not found: {ref}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare clean-context A/B eval run directories and run-manifest.json")
    ap.add_argument("--evals", type=Path, default=DEFAULT_EVALS)
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--iteration", type=int, default=1)
    ap.add_argument("--runs-per-case", type=int, default=0, help="0 = use evaluation_policy.runs_per_case_recommended")
    ap.add_argument("--arms", nargs="+", default=list(DEFAULT_ARMS), choices=DEFAULT_ARMS)
    ap.add_argument("--current-skill-id", default=None, help="Immutable/versioned identifier for current_skill; default: human-writing-ru@VERSION")
    ap.add_argument("--previous-skill-id", default=None, help="Immutable/versioned identifier for previous_skill; otherwise evaluation_policy.previous_skill_id")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    if args.iteration < 1: ap.error("--iteration must be >= 1")
    if len(set(args.arms)) != len(args.arms): ap.error("--arms must not contain duplicates")

    data = json.loads(args.evals.read_text(encoding="utf-8"))
    cases = data.get("evals", [])
    if not isinstance(cases, list) or not cases:
        raise SystemExit("evals file has no eval cases")
    policy = data.get("evaluation_policy", {})
    runs = args.runs_per_case or int(policy.get("runs_per_case_recommended", 1))
    if runs < 1: ap.error("--runs-per-case must be >= 1")
    package_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "unknown"
    current_skill_id = args.current_skill_id or f"human-writing-ru@{package_version}"
    previous_skill_id = args.previous_skill_id or policy.get("previous_skill_id")
    if "previous_skill" in args.arms and not previous_skill_id:
        ap.error("previous_skill arm requires --previous-skill-id or evaluation_policy.previous_skill_id")

    iteration_dir = args.workspace.resolve() / f"iteration-{args.iteration}"
    if iteration_dir.exists():
        if not args.overwrite:
            raise SystemExit(f"iteration directory already exists: {iteration_dir}; use --overwrite to recreate")
        shutil.rmtree(iteration_dir)
    iteration_dir.mkdir(parents=True)

    manifest = {
        "schema_version": 1,
        "skill_name": data.get("skill_name"),
        "iteration": args.iteration,
        "runs_per_case": runs,
        "arms": args.arms,
        "clean_context_required": bool(policy.get("clean_context_required", True)),
        "source_evals": str(args.evals.resolve()),
        "source_evals_sha256": sha256_file(args.evals.resolve()),
        "path_base": "iteration_dir",
        "arm_provenance": {
            "current_skill": {"id": current_skill_id},
            "previous_skill": {"id": previous_skill_id} if previous_skill_id else None,
            "without_skill": {"id": "without_skill"},
        },
        "input_artifacts": {},
        "runs": [],
    }
    seen = set()
    for case in cases:
        cid = safe_id(str(case.get("id", "")))
        if cid in seen: raise SystemExit(f"duplicate eval id after path normalization: {cid}")
        seen.add(cid)
        copied_inputs = []
        input_meta = []
        for index, ref in enumerate(case.get("files", []) or [], start=1):
            src = resolve_eval_input(str(ref), args.evals.resolve())
            input_dir = iteration_dir / "_inputs" / cid
            input_dir.mkdir(parents=True, exist_ok=True)
            dest = input_dir / f"{index:02d}-{src.name}"
            shutil.copy2(src, dest)
            rel = dest.relative_to(iteration_dir).as_posix()
            copied_inputs.append(rel)
            input_meta.append({"original_ref": str(ref), "path": rel, "sha256": sha256_file(dest), "bytes": dest.stat().st_size})
        manifest["input_artifacts"][cid] = input_meta
        for arm in args.arms:
            for run_index in range(1, runs + 1):
                run_dir = iteration_dir / cid / arm / f"run-{run_index:02d}"
                outputs = run_dir / "outputs"; outputs.mkdir(parents=True)
                run_record = {
                    "case_id": cid,
                    "arm": arm,
                    "run_index": run_index,
                    "prompt": case.get("prompt", ""),
                    "expected_output": case.get("expected_output", ""),
                    "assertions": case.get("assertions", []),
                    "input_files": copied_inputs,
                    "dimensions": case.get("dimensions", {}),
                    "path_base": "iteration_dir",
                    "output_dir": outputs.relative_to(iteration_dir).as_posix(),
                    "grading_path": (run_dir / "grading.json").relative_to(iteration_dir).as_posix(),
                    "timing_path": (run_dir / "timing.json").relative_to(iteration_dir).as_posix(),
                }
                (run_dir / "run.json").write_text(json.dumps(run_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                manifest["runs"].append(run_record)

    manifest_path = iteration_dir / "run-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"iteration_dir": str(iteration_dir), "cases": len(cases), "arms": len(args.arms), "runs": len(manifest["runs"]), "manifest": str(manifest_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
