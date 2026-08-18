#!/usr/bin/env python3
"""Acquire and validate external held-out data, then run decision protocol v3.

The historical `ablate_signals.py` remains byte-identical for reproducibility but
is not used for current threshold decisions.  This orchestrator has two gates:

1. materialization + dedup + all-profile 50/10k size stage;
2. v3 signal/diversity/grouped-split evidence stage.

No path edits profiles/editorial-baseline.json automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER = ROOT / "scripts/materialize_external_heldout.py"
VALIDATOR = ROOT / "scripts/validate_external_heldout.py"
DECISION_RUNNER = ROOT / "scripts/ablate_signals_v3.py"
REGISTRY = ROOT / "benchmark/external-heldout/SOURCE_REGISTRY.json"
DECISION_SPEC = ROOT / "benchmark/ablation/spec-v3.json"
PROFILE_SPEC = DECISION_SPEC
PROFILE_FILE = ROOT / "profiles/editorial-baseline.json"
FROZEN = ROOT / "benchmark/external-heldout/FROZEN_INPUT_SHA256.json"
DEFAULT_LOCAL_CORPUS_ROOT = Path(
    os.environ.get("HUMAN_WRITING_RU_EXAMPLES_DIR", str(ROOT / "examples"))
)

DEFAULT_SOURCES = (
    # prose
    "factrueval_2016", "ljsearch_saved_copies", "taiga_social",
    # oral
    "rub_corpus_russia", "putin_corpus_github_v1", "duma_speeches_1994_2021",
    # product
    "rbc_company_cases", "ruward_cases", "rurebus_business_documents",
    # technical / official
    "yandex_cloud_docs_ru", "kubernetes_docs_ru", "ruslawod_v3", "pravo_open_data",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_state() -> dict:
    expected = json.loads(FROZEN.read_text(encoding="utf-8"))["sha256"]
    actual = {rel: sha256_file(ROOT / rel) for rel in expected}
    mismatches = {rel: {"expected": expected[rel], "actual": actual[rel]} for rel in expected if actual[rel] != expected[rel]}
    return {"expected": expected, "actual": actual, "ok": not mismatches, "mismatches": mismatches}


def run(cmd: list[str], *, timeout: float | None = None) -> dict:
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {"command": cmd, "returncode": p.returncode, "stdout": p.stdout[-12000:], "stderr": p.stderr[-12000:], "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {"command": cmd, "returncode": 124, "stdout": stdout[-12000:], "stderr": stderr[-12000:], "timed_out": True, "timeout_seconds": timeout}


def registry_sources(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {s["id"]: s for s in data["sources"]}


def profiles_covered(ids: Iterable[str], sources: dict[str, dict]) -> dict[str, list[str]]:
    covered: dict[str, list[str]] = {}
    for sid in ids:
        for profile in sources[sid].get("profiles", []):
            covered.setdefault(profile, []).append(sid)
    return covered


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_local_sources(
    items: list[str], local_root: Path, selected_ids: list[str], sources: dict[str, dict], auto: bool
) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise ValueError("--local-source must be SOURCE_ID=PATH")
        source_id, value = item.split("=", 1)
        if source_id in resolved:
            raise ValueError(f"duplicate --local-source for {source_id}")
        resolved[source_id] = Path(value).expanduser().resolve()
    if auto:
        local_root = local_root.expanduser().resolve()
        for source_id in selected_ids:
            source = sources[source_id]
            candidate = local_root / source_id
            if (
                source.get("adapter") == "manual_or_local_tree"
                and source_id not in resolved
                and (candidate / "manifest.csv").is_file()
            ):
                resolved[source_id] = candidate
    return resolved


def main() -> int:
    ap = argparse.ArgumentParser(description="Materialize held-out data and run leak-resistant decision protocol v3")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--sources", nargs="+", default=list(DEFAULT_SOURCES))
    ap.add_argument("--annotations", type=Path, default=None, help="Optional completed natural-alert adjudication CSV for protocol v3")
    ap.add_argument("--local-source", action="append", default=[], metavar="SOURCE_ID=PATH",
                    help="Pass a local corpus tree to a manual_or_local_tree source; may be repeated")
    ap.add_argument("--local-corpus-root", type=Path, default=DEFAULT_LOCAL_CORPUS_ROOT,
                    help="Auto-discover SOURCE_ID/manifest.csv trees here (default: examples or HUMAN_WRITING_RU_EXAMPLES_DIR)")
    ap.add_argument("--no-auto-local-sources", action="store_true",
                    help="Disable local corpus auto-discovery; only explicit --local-source values are used")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--delay", type=float, default=0.35)
    ap.add_argument("--max-index-pages", type=int, default=12)
    ap.add_argument("--source-process-timeout", type=float, default=300.0)
    ap.add_argument("--near-duplicate-threshold", type=float, default=0.92)
    ap.add_argument("--resume", action="store_true",
                    help="Resume a prior workspace only when its manifest contains no source IDs outside --sources; default is a fresh manifest")
    args = ap.parse_args()

    if args.timeout <= 0: ap.error("--timeout must be > 0")
    if args.delay < 0: ap.error("--delay must be >= 0")
    if args.source_process_timeout <= 0: ap.error("--source-process-timeout must be > 0")
    if args.annotations is not None and not args.annotations.exists(): ap.error(f"--annotations does not exist: {args.annotations}")

    sources = registry_sources(args.registry)
    unknown = [sid for sid in args.sources if sid not in sources]
    if unknown: ap.error("unknown source ids: " + ", ".join(unknown))
    format_unverified = [sid for sid in args.sources if "format_unverified" in str(sources[sid].get("status", ""))]
    if format_unverified:
        ap.error("decision runs refuse format-unverified source ids: " + ", ".join(format_unverified))
    try:
        local_sources = resolve_local_sources(
            args.local_source, args.local_corpus_root, args.sources, sources, not args.no_auto_local_sources
        )
    except ValueError as exc:
        ap.error(str(exc))
    invalid_local = [f"{sid}={path}" for sid, path in local_sources.items() if not (path / "manifest.csv").is_file()]
    if invalid_local:
        ap.error("local corpus path must contain manifest.csv: " + ", ".join(invalid_local))

    out = args.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    gate_report_path = out / "NETWORK_GATE_RUN_REPORT.json"
    manifest = out / "manifest.csv"
    validated_manifest = out / "manifest.validated.csv"
    validation_report = out / "VALIDATION_REPORT.json"
    decision_output = out / "ABLATION_DECISION_V3.json"
    annotation_template = out / "alert-adjudication.csv"
    decision_not_run = out / "DECISION_NOT_RUN.json"
    decision_not_ready = out / "DECISION_NOT_READY.json"

    # A benchmark rerun must not silently inherit rows from a previous source
    # selection. Fresh is the safe default. Resume is explicit and validates
    # provenance before acquisition continues. Raw files may remain on disk, but
    # only rows in the freshly built/validated manifest participate in decisions.
    if args.resume and manifest.exists():
        import csv
        with manifest.open(encoding="utf-8", newline="") as fh:
            old_source_ids = {
                (row.get("source_id") or "").strip()
                for row in csv.DictReader(fh)
                if (row.get("source_id") or "").strip()
            }
        stale = sorted(old_source_ids - set(args.sources))
        if stale:
            ap.error("--resume manifest contains source ids outside --sources: " + ", ".join(stale))
    elif not args.resume:
        for generated in (manifest, validated_manifest, validation_report, decision_output, annotation_template, decision_not_run, decision_not_ready, out / "MATERIALIZATION_REPORT.json", out / "NETWORK_GATE_RUN_REPORT.json"):
            if generated.exists():
                generated.unlink()
        source_reports = out / "source-reports"
        if source_reports.exists():
            shutil.rmtree(source_reports)

    pre = frozen_state()
    report: dict = {
        "schema_version": 2,
        "protocol": "network-materialization-plus-decision-v3",
        "status": "starting",
        "sources": list(args.sources),
        "workspace_mode": "resume" if args.resume else "fresh",
        "local_corpus_root": str(args.local_corpus_root.expanduser().resolve()),
        "local_sources": {source_id: str(path) for source_id, path in sorted(local_sources.items())},
        "selected_source_profile_coverage": profiles_covered(args.sources, sources),
        "frozen_inputs_pre": pre,
        "decision_runner": str(DECISION_RUNNER.relative_to(ROOT)),
        "decision_runner_sha256": sha256_file(DECISION_RUNNER),
        "decision_spec": str(DECISION_SPEC.relative_to(ROOT)),
        "decision_spec_sha256": sha256_file(DECISION_SPEC),
        "acquisition_runs": [],
    }
    if not pre["ok"]:
        report["status"] = "blocked_frozen_input_mismatch_before_acquisition"
        write_json(gate_report_path, report); return 4

    source_reports_dir = out / "source-reports"; source_reports_dir.mkdir(parents=True, exist_ok=True)
    materialization_report_path = out / "MATERIALIZATION_REPORT.json"
    for sid in args.sources:
        if materialization_report_path.exists(): materialization_report_path.unlink()
        cmd = [sys.executable, str(MATERIALIZER), "--registry", str(args.registry), "--sources", sid, "--output-dir", str(out), "--timeout", str(args.timeout), "--delay", str(args.delay), "--max-index-pages", str(args.max_index_pages)]
        cmd.append("--no-auto-local-sources")
        if sid in local_sources:
            cmd.extend(["--local-source", f"{sid}={local_sources[sid]}"])
        one = run(cmd, timeout=args.source_process_timeout); one["source_id"] = sid
        if materialization_report_path.exists():
            try:
                materialization_report = json.loads(materialization_report_path.read_text(encoding="utf-8"))
                one["materialization_report"] = materialization_report
                write_json(source_reports_dir / f"{sid}.json", materialization_report)
            except Exception as exc:
                one["materialization_report_error"] = str(exc)
        report["acquisition_runs"].append(one)

    if not manifest.exists():
        report["status"] = "blocked_no_manifest"; report["frozen_inputs_post_acquisition"] = frozen_state()
        write_json(gate_report_path, report); return 2

    validation_cmd = [sys.executable, str(VALIDATOR), "--manifest", str(manifest), "--output", str(validation_report), "--spec", str(PROFILE_SPEC), "--profile-file", str(PROFILE_FILE), "--near-duplicate-threshold", str(args.near_duplicate_threshold), "--validated-manifest", str(validated_manifest)]
    report["validation_run"] = run(validation_cmd)
    if not validation_report.exists():
        report["status"] = "blocked_validator_no_report"; report["frozen_inputs_post_acquisition"] = frozen_state()
        write_json(gate_report_path, report); return 2

    validation = json.loads(validation_report.read_text(encoding="utf-8"))
    validator_clean = report["validation_run"].get("returncode") == 0 and bool(validation.get("validation_clean", True))
    profile_stage_ready = validator_clean and bool(validation.get("ready_for_profile_freeze_stage", validation.get("ready_for_unchanged_ablation", False)))
    report["validation_summary"] = {
        "validated_representative_rows": validation.get("validated_representative_rows", 0),
        "required_profiles_for_freeze": validation.get("required_profiles_for_freeze", []),
        "profiles": validation.get("profiles", {}),
        "validation_clean": validator_clean,
        "ready_for_profile_freeze_stage": profile_stage_ready,
        "validated_manifest_sha256": validation.get("validated_representative_manifest_sha256"),
    }

    post_acq = frozen_state(); report["frozen_inputs_post_acquisition"] = post_acq
    if not validator_clean:
        report["status"] = "blocked_validator_errors"
        write_json(gate_report_path, report)
        return 2
    if not post_acq["ok"]:
        report["status"] = "blocked_frozen_input_mismatch_after_acquisition"; write_json(gate_report_path, report); return 4

    if not profile_stage_ready:
        reason = {
            "schema_version": 2, "status": "decision_not_run", "reason": "all_profile_50_10000_stage_not_met",
            "validated_manifest": str(validated_manifest), "validated_representative_rows": validation.get("validated_representative_rows", 0),
            "required_profiles_for_freeze": validation.get("required_profiles_for_freeze", []), "profiles": validation.get("profiles", {}),
            "next_protocol": str(DECISION_RUNNER.relative_to(ROOT)),
        }
        write_json(decision_not_run, reason)
        if decision_output.exists(): decision_output.unlink()
        if decision_not_ready.exists(): decision_not_ready.unlink()
        report["status"] = "profile_freeze_stage_not_met_decision_v3_blocked"; write_json(gate_report_path, report); return 3

    decision_cmd = [sys.executable, str(DECISION_RUNNER), "--manifest", str(validated_manifest), "--output", str(decision_output), "--spec", str(DECISION_SPEC), "--profile-file", str(PROFILE_FILE), "--annotation-template", str(annotation_template)]
    if args.annotations is not None:
        decision_cmd.extend(["--annotations", str(args.annotations.resolve())])
    report["decision_run"] = run(decision_cmd)
    post_decision = frozen_state(); report["frozen_inputs_post_decision"] = post_decision
    if not post_decision["ok"]:
        report["status"] = "failed_frozen_input_mismatch_after_decision"; write_json(gate_report_path, report); return 4
    if report["decision_run"]["returncode"] != 0 or not decision_output.exists():
        report["status"] = "decision_v3_subprocess_failed"; write_json(gate_report_path, report); return 5

    decision = json.loads(decision_output.read_text(encoding="utf-8"))
    global_state = decision.get("global", {})
    evidence_ready = bool(global_state.get("ready_for_decision_evaluation"))
    adjudication_pending = list(global_state.get("natural_alert_adjudication_pending", []))
    report["decision_summary"] = {
        "ready_for_decision_evaluation": evidence_ready,
        "natural_alert_adjudication_pending": adjudication_pending,
        "automatic_policy_update_allowed": bool(global_state.get("automatic_policy_update_allowed", False)),
    }
    if decision_not_run.exists(): decision_not_run.unlink()

    if not evidence_ready:
        payload = {
            "schema_version": 1, "status": "decision_not_ready", "reason": "v3_diversity_signal_or_split_evidence_gate_not_met",
            "decision_output": str(decision_output), "global": global_state,
        }
        write_json(decision_not_ready, payload)
        report["status"] = "profile_freeze_met_v3_evidence_incomplete"; write_json(gate_report_path, report); return 6

    if decision_not_ready.exists(): decision_not_ready.unlink()
    if adjudication_pending:
        report["status"] = "v3_evidence_ready_natural_alert_adjudication_pending"; write_json(gate_report_path, report); return 7

    report["status"] = "v3_decision_evidence_complete_pending_explicit_policy_review"
    write_json(gate_report_path, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
