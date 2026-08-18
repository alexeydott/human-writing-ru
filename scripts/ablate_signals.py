#!/usr/bin/env python3
"""Ablation old -> candidate -> off for five editorial signals.

Natural held-out documents estimate alert burden and feature distributions.
Synthetic controls estimate sensitivity only. The script never treats quantiles
as Russian-language norms and refuses to recommend activation when the
pre-registered sample gate is not met.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_prose_ru as cp

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "benchmark/ablation/spec.json"
DEFAULT_PROFILE = ROOT / "profiles/editorial-baseline.json"
DEFAULT_CONTROLS = ROOT / "benchmark/ablation/controls"

CONTROL_FILES = {
    "road-sign-density": "road.txt",
    "sentence-uniformity": "uniform.txt",
    "long-sentence": "long.txt",
    "one-sentence-paragraphs": "one-paragraph.txt",
    "context-jargon-density": "jargon.txt",
}


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return float(values[lo])
    return float(values[lo] + (values[hi] - values[lo]) * (k - lo))


def truthy(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def load_manifest(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "path" not in reader.fieldnames or "profile" not in reader.fieldnames:
            raise SystemExit("Manifest must contain path and profile columns")
        for row in reader:
            raw_path = (row.get("path") or "").strip()
            if not raw_path:
                continue
            p = Path(raw_path)
            if not p.is_absolute():
                p = (path.parent / p).resolve()
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8", errors="strict")
            features = cp.compute_features(text, include_quotes=False)
            rows.append({
                **row,
                "_path": str(p),
                "_features": features,
                "_calibration_eligible": truthy(row.get("calibration_eligible"), True),
                "_lexical_only": truthy(row.get("lexical_only"), False),
            })
    return rows


def feature_value(row: dict, signal_spec: dict) -> float:
    return float(row["_features"][signal_spec["feature"]])


def signal_eligible(row: dict, signal: str, signal_spec: dict, profile: dict) -> bool:
    if not row["_calibration_eligible"]:
        return False
    if signal in {"sentence-uniformity", "long-sentence", "one-sentence-paragraphs"} and row["_lexical_only"]:
        return False
    if signal_spec.get("requires_rhythm_checks") and not profile.get("rhythm_checks", True):
        return False
    size_key = signal_spec.get("minimum_size_key")
    size_feature = signal_spec.get("minimum_size_feature")
    if size_key and size_feature:
        if row["_features"][size_feature] < profile.get(size_key, 0):
            return False
    return True


def fires(row: dict, signal: str, signal_spec: dict, profile: dict, threshold: float | None) -> bool:
    if threshold is None:  # off arm
        return False
    if not signal_eligible(row, signal, signal_spec, profile):
        return False
    min_hit_key = signal_spec.get("minimum_hit_key")
    if min_hit_key:
        count_name = {
            "road-sign-density": "road",
            "context-jargon-density": "jargon",
        }[signal]
        if row["_features"]["_counts"][count_name] < profile.get(min_hit_key, 0):
            return False
    value = feature_value(row, signal_spec)
    return value >= threshold if signal_spec["direction"] == "high" else value < threshold


def candidate_threshold(old: float, values: list[float], signal_spec: dict) -> float:
    if not values:
        return old
    qv = percentile(values, float(signal_spec["candidate_quantile"]))
    # Conservative candidate: never makes the detector more sensitive merely
    # because of a small corpus. High-tail signals can only move upward; a
    # low-tail threshold such as CV can only move downward.
    if signal_spec["direction"] == "high":
        return max(old, qv)
    return min(old, qv)


def control_row(signal: str, profile_name: str, controls: Path) -> dict:
    p = controls / CONTROL_FILES[signal]
    text = p.read_text(encoding="utf-8")
    return {
        "id": f"control-{signal}",
        "profile": profile_name,
        "calibration_eligible": "1",
        "lexical_only": "0",
        "_path": str(p),
        "_calibration_eligible": True,
        "_lexical_only": False,
        "_features": cp.compute_features(text, include_quotes=False),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ablate five editorial signals: old -> candidate -> off")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--profile-file", default=str(DEFAULT_PROFILE))
    parser.add_argument("--controls", default=str(DEFAULT_CONTROLS))
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    profiles = cp.load_profiles(args.profile_file)
    rows = load_manifest(Path(args.manifest))
    if not rows:
        raise SystemExit("No readable held-out documents")

    freeze_docs = int(spec["freeze_gate"]["minimum_independent_documents_per_profile"])
    freeze_words = int(spec["freeze_gate"]["minimum_words_per_profile"])
    controls = Path(args.controls)
    result = {
        "schema_version": 1,
        "status": "ablation_complete_threshold_freeze_conditional",
        "manifest": str(Path(args.manifest)),
        "documents_loaded": len(rows),
        "freeze_gate": spec["freeze_gate"],
        "signals": {},
    }

    by_profile = defaultdict(list)
    for row in rows:
        by_profile[row["profile"]].append(row)

    for signal, ss in spec["signals"].items():
        signal_out = {"profiles": {}, "overall_decision": "keep_old_pending_larger_heldout"}
        any_candidate_change = False
        all_changed_profiles_frozen = True

        for profile_name, pcfg in sorted(profiles.items()):
            prow = by_profile.get(profile_name, [])
            old = float(pcfg[ss["threshold_key"]])
            eligible = [r for r in prow if signal_eligible(r, signal, ss, pcfg)]
            values = [feature_value(r, ss) for r in eligible]
            cand = candidate_threshold(old, values, ss)
            if ss["threshold_key"].endswith("words_info"):
                cand = float(math.ceil(cand))
            old_alerts = [r for r in eligible if fires(r, signal, ss, pcfg, old)]
            cand_alerts = [r for r in eligible if fires(r, signal, ss, pcfg, cand)]
            words = sum(int(r["_features"]["words"]) for r in eligible)
            gate = len(eligible) >= freeze_docs and words >= freeze_words

            ctrl = control_row(signal, profile_name, controls)
            old_control = fires(ctrl, signal, ss, pcfg, old)
            cand_control = fires(ctrl, signal, ss, pcfg, cand)
            off_control = False

            if cand != old:
                any_candidate_change = True
                all_changed_profiles_frozen = all_changed_profiles_frozen and gate

            if not eligible:
                decision = "no_data_keep_old"
            elif not gate:
                decision = "keep_old_freeze_gate_not_met"
            elif len(cand_alerts) < len(old_alerts) and cand_control:
                decision = "candidate_eligible_for_activation"
            elif not old_alerts and old_control:
                decision = "keep_old_no_clean_noise_observed"
            elif not cand_control:
                decision = "keep_old_candidate_loses_positive_control"
            else:
                decision = "keep_old_no_measured_gain"

            signal_out["profiles"][profile_name] = {
                "eligible_documents": len(eligible),
                "eligible_words": words,
                "freeze_gate_met": gate,
                "old_threshold": old,
                "candidate_threshold": round(cand, 4),
                "observed_feature_quantile": round(percentile(values, float(ss["candidate_quantile"])), 4) if values else None,
                "old_clean_alert_documents": len(old_alerts),
                "candidate_clean_alert_documents": len(cand_alerts),
                "off_clean_alert_documents": 0,
                "positive_control": {
                    "old": old_control,
                    "candidate": cand_control,
                    "off": off_control,
                },
                "decision": decision,
            }

        if any_candidate_change and all_changed_profiles_frozen:
            signal_out["overall_decision"] = "review_candidate_for_activation"
        elif any_candidate_change:
            signal_out["overall_decision"] = "do_not_activate_candidate_freeze_gate_not_met"
        else:
            signal_out["overall_decision"] = "keep_old_no_evidence_for_threshold_change"
        result["signals"][signal] = signal_out

    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"documents={len(rows)} output={args.output}")
    for signal, data in result["signals"].items():
        print(signal, data["overall_decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
