#!/usr/bin/env python3
"""Leak-resistant decision protocol for the five frozen editorial signals (decision protocol v3).

This does not modify check_prose_ru.py, ablate_signals.py, or the active profile.
It derives candidate thresholds only on grouped calibration data and evaluates
old/candidate/off on untouched validation groups. Decisions remain blocked
without manual natural-alert adjudication where alert usefulness matters.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_prose_ru as cp

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "benchmark/ablation/spec-v3.json"
DEFAULT_PROFILE = ROOT / "profiles/editorial-baseline.json"
DEFAULT_CONTROLS = ROOT / "benchmark/ablation/controls"
CONTROL_FILES = {
    "road-sign-density": "road.txt",
    "sentence-uniformity": "uniform.txt",
    "long-sentence": "long.txt",
    "one-sentence-paragraphs": "one-paragraph.txt",
    "context-jargon-density": "jargon.txt",
}


def truthy(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("percentile requires non-empty values")
    values = sorted(values)
    k = (len(values) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return float(values[lo])
    return float(values[lo] + (values[hi] - values[lo]) * (k - lo))


def candidate_threshold(old: float, values: list[float], signal_spec: dict) -> float:
    qv = percentile(values, float(signal_spec["candidate_quantile"]))
    return max(old, qv) if signal_spec["direction"] == "high" else min(old, qv)


def load_rows(manifest: Path) -> list[dict]:
    out = []
    with manifest.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"id", "path", "profile"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise SystemExit(f"manifest must contain {sorted(required)}")
        seen_ids: set[str] = set()
        seen_digests: dict[str, str] = {}
        for line_no, row in enumerate(reader, start=2):
            doc_id = (row.get("id") or "").strip()
            if not doc_id:
                raise SystemExit(f"manifest row {line_no}: id is required")
            if doc_id in seen_ids:
                raise SystemExit(f"duplicate document id in decision manifest: {doc_id}")
            seen_ids.add(doc_id)
            row = dict(row)
            row["id"] = doc_id
            p = Path((row.get("path") or "").strip())
            if not p.is_absolute():
                p = (manifest.parent / p).resolve()
            if not p.exists():
                raise SystemExit(f"missing manifest file: {p}")
            text = p.read_text(encoding="utf-8", errors="strict")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            expected_digest = (row.get("sha256") or "").strip()
            if expected_digest and expected_digest != digest:
                raise SystemExit(f"manifest sha256 mismatch for {doc_id}: file changed after validation")
            if digest in seen_digests:
                raise SystemExit(
                    f"decision manifest contains exact duplicate text: {seen_digests[digest]} and {doc_id}; "
                    "run validate_external_heldout.py first"
                )
            seen_digests[digest] = doc_id
            row["sha256"] = digest
            row["_path"] = str(p)
            row["_features"] = cp.compute_features(text, include_quotes=False)
            row["_calibration_eligible"] = truthy(row.get("calibration_eligible"), True)
            row["_lexical_only"] = truthy(row.get("lexical_only"), False)
            out.append(row)
    return out


def signal_eligible(row: dict, signal: str, ss: dict, profile: dict) -> bool:
    if not row["_calibration_eligible"]:
        return False
    if signal in {"sentence-uniformity", "long-sentence", "one-sentence-paragraphs"} and row["_lexical_only"]:
        return False
    if ss.get("requires_rhythm_checks") and not profile.get("rhythm_checks", True):
        return False
    size_key, size_feature = ss.get("minimum_size_key"), ss.get("minimum_size_feature")
    if size_key and size_feature and row["_features"].get(size_feature, 0) < profile.get(size_key, 0):
        return False
    return True


def fires(row: dict, signal: str, ss: dict, profile: dict, threshold: float | None) -> bool:
    if threshold is None or not signal_eligible(row, signal, ss, profile):
        return False
    min_hit_key = ss.get("minimum_hit_key")
    if min_hit_key:
        count_name = {"road-sign-density": "road", "context-jargon-density": "jargon"}[signal]
        if row["_features"]["_counts"][count_name] < profile.get(min_hit_key, 0):
            return False
    value = float(row["_features"][ss["feature"]])
    return value >= threshold if ss["direction"] == "high" else value < threshold


UNKNOWN_PROVENANCE = {"unknown", "unknown-source", "n/a", "na", "none", "null", "?"}


def _normalized_label(value: str) -> str:
    return " ".join(value.split()).casefold()


def _known_provenance(value: str) -> str | None:
    normalized = _normalized_label(value)
    return None if not normalized or normalized in UNKNOWN_PROVENANCE else normalized


def _group_value(row: dict, field: str, split_spec: dict) -> str | None:
    raw_value = (row.get(field) or "").strip()
    if not raw_value:
        return None
    if field == "author_or_group":
        value = _known_provenance(raw_value)
        if value is None:
            return None
    else:
        value = raw_value
        if _normalized_label(value) in UNKNOWN_PROVENANCE:
            return None
    if field in set(split_spec.get("source_scoped_group_fields", [])):
        source = (row.get("source_id") or row.get("corpus") or "unknown-source").strip()
        return f"{field}:{source}:{value}"
    return f"{field}:{value}"


def split_components(rows: list[dict], split_spec: dict) -> list[list[dict]]:
    """Return connected components across *all* known leakage constraints.

    Using the first available key is unsafe: an explicit split_group could mask a
    shared author and allow that author to cross arms.  We therefore union rows
    that share any configured group token.  Unknown/missing values never create
    a component.  Rows with no known grouping metadata remain singleton groups.
    """
    n = len(rows)
    parent = list(range(n))
    rank = [0] * n

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    owners: dict[str, int] = {}
    fields = list(split_spec.get("group_fields", []))
    if not fields:
        fields = list(split_spec.get("group_precedence", []))
    for i, row in enumerate(rows):
        tokens = [_group_value(row, field, split_spec) for field in fields]
        for token in (t for t in tokens if t):
            if token in owners:
                union(i, owners[token])
            else:
                owners[token] = i

    groups: dict[int, list[dict]] = defaultdict(list)
    for i, row in enumerate(rows):
        groups[find(i)].append(row)
    return list(groups.values())


def split_rows(rows: list[dict], profile: str, split_spec: dict) -> tuple[list[dict], list[dict]]:
    """Deterministic component-preserving split with bounded size imbalance.

    Split assignment uses only group identity, document count and word count —
    never signal values or alert outcomes.  This prevents threshold leakage while
    keeping every connected provenance/author component wholly in one arm.
    """
    fraction = float(split_spec["calibration_fraction"])
    seed = str(split_spec["seed"])
    components = split_components(rows, split_spec)
    groups = []
    for group in components:
        ids = sorted(str(r.get("id") or r.get("_path") or "") for r in group)
        identity = "|".join(ids)
        digest = hashlib.blake2b(f"{seed}|{profile}|{identity}".encode(), digest_size=8).hexdigest()
        groups.append((digest, identity, group))
    groups.sort()

    total_docs, total_words = len(rows), words(rows)
    target_docs, target_words = total_docs * fraction, total_words * fraction
    cal: list[dict] = []
    val: list[dict] = []
    cal_docs = cal_words = 0
    for _, _, group in groups:
        gd, gw = len(group), words(group)

        def cost(new_docs: int, new_words: int) -> float:
            d = abs(new_docs - target_docs) / max(total_docs, 1)
            w = abs(new_words - target_words) / max(total_words, 1)
            return d + w

        put_cal = cost(cal_docs + gd, cal_words + gw) <= cost(cal_docs, cal_words)
        if put_cal:
            cal.extend(group)
            cal_docs += gd
            cal_words += gw
        else:
            val.extend(group)

    # Avoid an empty arm only by moving a whole component.
    if groups and not val and len(groups) > 1:
        move = groups[-1][2]
        move_ids = {id(x) for x in move}
        cal = [x for x in cal if id(x) not in move_ids]
        val.extend(move)
    if groups and not cal and len(groups) > 1:
        move = groups[0][2]
        move_ids = {id(x) for x in move}
        val = [x for x in val if id(x) not in move_ids]
        cal.extend(move)
    return cal, val

def words(rows: list[dict]) -> int:
    return sum(int(r["_features"].get("words", 0)) for r in rows)


def diversity(rows: list[dict], cfg: dict) -> dict:
    """Measure provenance concentration by document count *and* word mass.

    Source/channel provenance is required for benchmark evidence. Unknown values
    do not count as categories, do not dilute concentration, and reduce explicit
    metadata coverage. Author/speaker coverage is blocking only for profiles
    that declare author concentration required.
    """
    n = len(rows)
    total_words = words(rows)
    source_docs: Counter[str] = Counter()
    source_words: Counter[str] = Counter()
    channel_docs: Counter[str] = Counter()
    channel_words: Counter[str] = Counter()
    author_docs: Counter[str] = Counter()
    author_words: Counter[str] = Counter()
    known_source_docs = known_source_words = 0
    known_channel_docs = known_channel_words = 0
    known_author_docs = known_author_words = 0

    for r in rows:
        source = _known_provenance(str(r.get("source_id") or r.get("corpus") or ""))
        channel = _known_provenance(str(r.get("channel") or ""))
        author = _known_provenance(str(r.get("author_or_group") or ""))
        w = int(r["_features"].get("words", 0))
        if source is not None:
            source_docs[source] += 1
            source_words[source] += w
            known_source_docs += 1
            known_source_words += w
        if channel is not None:
            channel_docs[channel] += 1
            channel_words[channel] += w
            known_channel_docs += 1
            known_channel_words += w
        if author is not None:
            author_docs[author] += 1
            author_words[author] += w
            known_author_docs += 1
            known_author_words += w

    source_doc_coverage = known_source_docs / n if n else 0.0
    source_word_coverage = known_source_words / total_words if total_words else 0.0
    channel_doc_coverage = known_channel_docs / n if n else 0.0
    channel_word_coverage = known_channel_words / total_words if total_words else 0.0
    max_source_doc_share = max(source_docs.values(), default=0) / known_source_docs if known_source_docs else 0.0
    max_source_word_share = max(source_words.values(), default=0) / known_source_words if known_source_words else 0.0
    author_doc_coverage = known_author_docs / n if n else 0.0
    author_word_coverage = known_author_words / total_words if total_words else 0.0
    max_author_doc_share = max(author_docs.values(), default=0) / known_author_docs if known_author_docs else 0.0
    max_author_word_share = max(author_words.values(), default=0) / known_author_words if known_author_words else 0.0

    source_coverage_floor = float(cfg.get("minimum_known_source_coverage", 1.0))
    channel_coverage_floor = float(cfg.get("minimum_known_channel_coverage", 1.0))
    author_required = bool(cfg.get("author_concentration_required", False))
    min_author_coverage = float(cfg.get("minimum_known_author_coverage", 0.0))
    author_coverage_ok = (not author_required) or (
        author_doc_coverage >= min_author_coverage and author_word_coverage >= min_author_coverage
    )
    author_concentration_ok = (not author_required) or (
        max_author_doc_share <= float(cfg["maximum_known_author_document_share"])
        and max_author_word_share <= float(cfg["maximum_known_author_word_share"])
    )

    checks = {
        "source_metadata_coverage": source_doc_coverage >= source_coverage_floor and source_word_coverage >= source_coverage_floor,
        "channel_metadata_coverage": channel_doc_coverage >= channel_coverage_floor and channel_word_coverage >= channel_coverage_floor,
        "minimum_sources": len(source_docs) >= int(cfg["minimum_sources"]),
        "minimum_channels": len(channel_docs) >= int(cfg["minimum_channels"]),
        "maximum_source_document_share": max_source_doc_share <= float(cfg["maximum_source_document_share"]),
        "maximum_source_word_share": max_source_word_share <= float(cfg["maximum_source_word_share"]),
        "author_metadata_coverage": author_coverage_ok,
        "maximum_known_author_concentration": author_concentration_ok,
    }
    return {
        "sources_documents": dict(source_docs),
        "sources_words": dict(source_words),
        "channels_documents": dict(channel_docs),
        "channels_words": dict(channel_words),
        "known_source_count": len(source_docs),
        "known_channel_count": len(channel_docs),
        "known_source_document_coverage": round(source_doc_coverage, 4),
        "known_source_word_coverage": round(source_word_coverage, 4),
        "known_channel_document_coverage": round(channel_doc_coverage, 4),
        "known_channel_word_coverage": round(channel_word_coverage, 4),
        "maximum_source_document_share_observed": round(max_source_doc_share, 4),
        "maximum_source_word_share_observed": round(max_source_word_share, 4),
        "author_concentration_required": author_required,
        "known_author_document_coverage": round(author_doc_coverage, 4),
        "known_author_word_coverage": round(author_word_coverage, 4),
        "maximum_known_author_document_share_observed": round(max_author_doc_share, 4) if author_docs else None,
        "maximum_known_author_word_share_observed": round(max_author_word_share, 4) if author_words else None,
        "checks": checks,
        "gate_met": all(checks.values()),
    }

def load_annotations(path: Path | None) -> dict[tuple[str, str], str]:
    if path is None:
        return {}
    labels: dict[tuple[str, str], str] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"document_id", "signal", "label"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise SystemExit("annotations CSV must contain document_id,signal,label")
        for line_no, row in enumerate(reader, start=2):
            document_id = (row.get("document_id") or "").strip()
            signal = (row.get("signal") or "").strip()
            label = (row.get("label") or "").strip()
            if not document_id or not signal:
                raise SystemExit(f"annotations row {line_no}: document_id and signal are required")
            if not label:
                continue  # blank template rows are intentionally unannotated
            key = (document_id, signal)
            if key in labels and labels[key] != label:
                raise SystemExit(f"conflicting duplicate annotation for {document_id}/{signal}: {labels[key]!r} vs {label!r}")
            labels[key] = label
    return labels


def annotation_summary(alert_rows: list[dict], signal: str, annotations: dict[tuple[str, str], str]) -> dict:
    labels = [annotations.get((r.get("id", ""), signal)) for r in alert_rows]
    c = Counter(x for x in labels if x)
    annotated = sum(c.values())
    decisive = c.get("actionable", 0) + c.get("non_actionable", 0)
    return {
        "alerts": len(alert_rows),
        "annotated": annotated,
        "decisive": decisive,
        "actionable": c.get("actionable", 0),
        "non_actionable": c.get("non_actionable", 0),
        "uncertain": c.get("uncertain", 0),
        "actionable_precision": round(c.get("actionable", 0) / decisive, 4) if decisive else None,
    }


def bootstrap_alert_reduction(old_flags: list[int], cand_flags: list[int], seed: str, n_boot: int = 2000) -> dict:
    if not old_flags:
        return {"mean": None, "ci95": [None, None]}
    rng = random.Random(seed)
    n = len(old_flags)
    diffs = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        old = sum(old_flags[i] for i in idx) / n
        cand = sum(cand_flags[i] for i in idx) / n
        diffs.append(old - cand)
    diffs.sort()
    lo = diffs[int(0.025 * (n_boot - 1))]
    hi = diffs[int(0.975 * (n_boot - 1))]
    return {"mean": round(sum(diffs) / n_boot, 4), "ci95": [round(lo, 4), round(hi, 4)]}


def control_fires(signal: str, profile_name: str, ss: dict, profile: dict, threshold: float, controls: Path) -> bool:
    text = (controls / CONTROL_FILES[signal]).read_text(encoding="utf-8")
    row = {
        "id": f"control-{signal}", "profile": profile_name,
        "_calibration_eligible": True, "_lexical_only": False,
        "_features": cp.compute_features(text, include_quotes=False),
    }
    return fires(row, signal, ss, profile, threshold)


def main() -> int:
    ap = argparse.ArgumentParser(description="Leak-resistant old -> candidate -> off evaluation")
    ap.add_argument("--manifest", type=Path, required=True, help="Deduplicated manifest.validated.csv")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--profile-file", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--controls", type=Path, default=DEFAULT_CONTROLS)
    ap.add_argument("--annotations", type=Path, default=None, help="Optional natural-alert adjudication CSV")
    ap.add_argument("--annotation-template", type=Path, default=None, help="Write CSV rows for natural validation alerts that need adjudication")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    profiles = cp.load_profiles(args.profile_file)
    rows = load_rows(args.manifest)
    annotations = load_annotations(args.annotations)
    allowed_labels = set(spec["adjudication"]["labels"])
    bad_labels = sorted(set(annotations.values()) - allowed_labels)
    if bad_labels:
        raise SystemExit(f"unsupported annotation labels: {bad_labels}")
    valid_document_ids = {r["id"] for r in rows}
    valid_signals = set(spec["signals"])
    unknown_annotation_refs = sorted(
        (document_id, signal)
        for document_id, signal in annotations
        if document_id not in valid_document_ids or signal not in valid_signals
    )
    if unknown_annotation_refs:
        sample = ", ".join(f"{d}/{s}" for d, s in unknown_annotation_refs[:8])
        extra = " ..." if len(unknown_annotation_refs) > 8 else ""
        raise SystemExit(f"annotations reference unknown document/signal pairs: {sample}{extra}")

    annotation_template_rows: list[dict] = []
    result = {
        "schema_version": 3,
        "status": "ablation_v3_complete_no_automatic_policy_change",
        "manifest": str(args.manifest),
        "documents_loaded": len(rows),
        "spec": spec,
        "profiles": {},
        "signals": {},
    }
    by_profile = defaultdict(list)
    for r in rows:
        if r["profile"] not in profiles:
            raise SystemExit(f"unknown profile {r['profile']!r}")
        if r["_calibration_eligible"]:
            by_profile[r["profile"]].append(r)

    pg = spec["profile_gate"]
    profile_ready = {}
    for name in sorted(profiles):
        pr = by_profile.get(name, [])
        div = diversity(pr, spec["diversity_gate"][name])
        size_ok = len(pr) >= int(pg["minimum_independent_documents"]) and words(pr) >= int(pg["minimum_words"])
        profile_ready[name] = size_ok and div["gate_met"]
        result["profiles"][name] = {
            "documents": len(pr), "words": words(pr),
            "size_gate_met": size_ok, "diversity": div,
            "profile_gate_met": profile_ready[name],
        }

    sg = spec["signal_gate"]
    adj_cfg = spec["adjudication"]
    all_applicable_evidence_gates: list[bool] = []
    for signal, ss in spec["signals"].items():
        sout = {"profiles": {}, "decision_status": "no_profile_eligible_for_decision"}
        decidable = 0
        for profile_name, pcfg in sorted(profiles.items()):
            if ss.get("requires_rhythm_checks") and not pcfg.get("rhythm_checks", True):
                sout["profiles"][profile_name] = {"applicable": False, "decision": "not_applicable_profile_rhythm_disabled"}
                continue
            base = by_profile.get(profile_name, [])
            eligible = [r for r in base if signal_eligible(r, signal, ss, pcfg)]
            signal_size_ok = len(eligible) >= int(sg["minimum_eligible_documents"]) and words(eligible) >= int(sg["minimum_eligible_words"])
            signal_diversity = diversity(eligible, spec["diversity_gate"][profile_name])
            cal, val = split_rows(eligible, profile_name, spec["split"])
            split_ok = (
                len(cal) >= int(sg["calibration_minimum_documents"]) and words(cal) >= int(sg["calibration_minimum_words"])
                and len(val) >= int(sg["validation_minimum_documents"]) and words(val) >= int(sg["validation_minimum_words"])
            )
            old = float(pcfg[ss["threshold_key"]])
            cand = old
            observed_q = None
            if cal:
                vals = [float(r["_features"][ss["feature"]]) for r in cal]
                observed_q = percentile(vals, float(ss["candidate_quantile"]))
                cand = candidate_threshold(old, vals, ss)
                if ss["threshold_key"].endswith("words_info"):
                    cand = float(math.ceil(cand))
            evidence_gate = profile_ready.get(profile_name, False) and signal_size_ok and signal_diversity["gate_met"] and split_ok
            all_applicable_evidence_gates.append(evidence_gate)
            old_alerts = [r for r in val if fires(r, signal, ss, pcfg, old)]
            cand_alerts = [r for r in val if fires(r, signal, ss, pcfg, cand)]
            old_only = [r for r in old_alerts if not fires(r, signal, ss, pcfg, cand)]
            old_sum = annotation_summary(old_alerts, signal, annotations)
            cand_sum = annotation_summary(cand_alerts, signal, annotations)
            removed_sum = annotation_summary(old_only, signal, annotations)
            cand_ids = {r.get("id", "") for r in cand_alerts}
            # Do not create annotation work for evidence that is already blocked
            # by profile/signal/diversity/split gates. Those labels could never
            # affect a decision and would create a misleading review burden.
            if evidence_gate:
                for alert_row in old_alerts:
                    did = alert_row.get("id", "")
                    annotation_template_rows.append({
                        "document_id": did,
                        "signal": signal,
                        "profile": profile_name,
                        "source_id": alert_row.get("source_id", ""),
                        "channel": alert_row.get("channel", ""),
                        "old_fires": "1",
                        "candidate_fires": "1" if did in cand_ids else "0",
                        "removed_by_candidate": "0" if did in cand_ids else "1",
                        "label": annotations.get((did, signal), ""),
                        "notes": "",
                    })
            old_flags = [1 if fires(r, signal, ss, pcfg, old) else 0 for r in val]
            cand_flags = [1 if fires(r, signal, ss, pcfg, cand) else 0 for r in val]
            positive_old = control_fires(signal, profile_name, ss, pcfg, old, args.controls)
            positive_cand = control_fires(signal, profile_name, ss, pcfg, cand, args.controls)

            if not evidence_gate:
                decision = "blocked_evidence_gate_not_met"
            elif cand == old:
                decision = "keep_old_candidate_equals_old"
                decidable += 1
            elif not positive_cand:
                decision = "keep_old_candidate_loses_positive_control"
                decidable += 1
            elif len(old_only) < int(adj_cfg["minimum_old_only_annotations_for_candidate"]):
                decision = "keep_old_candidate_effect_sample_too_small"
                decidable += 1
            elif removed_sum["decisive"] < int(adj_cfg["minimum_old_only_annotations_for_candidate"]):
                decision = "candidate_blocked_needs_removed_alert_adjudication"
            else:
                non_actionable = removed_sum["non_actionable"] / removed_sum["decisive"] if removed_sum["decisive"] else 0.0
                if non_actionable >= float(adj_cfg["minimum_non_actionable_share_removed_for_candidate"]):
                    decision = "candidate_supported_on_validation_pending_human_review"
                else:
                    decision = "keep_old_removed_alerts_include_too_many_actionable_cases"
                decidable += 1

            off_decision = "off_blocked_evidence_gate_not_met" if not evidence_gate else "off_blocked_needs_alert_adjudication"
            if evidence_gate and len(old_alerts) < int(adj_cfg["minimum_alert_annotations_for_off"]):
                off_decision = "off_not_evaluable_insufficient_natural_alert_sample"
            elif evidence_gate and old_sum["decisive"] >= int(adj_cfg["minimum_alert_annotations_for_off"]):
                precision = old_sum["actionable_precision"]
                if precision is not None and precision <= float(adj_cfg["maximum_actionable_precision_for_off"]):
                    off_decision = "off_supported_by_low_actionable_precision_pending_human_review"
                else:
                    off_decision = "off_not_supported_signal_has_actionable_natural_alerts"

            sout["profiles"][profile_name] = {
                "applicable": True,
                "eligible_documents": len(eligible), "eligible_words": words(eligible),
                "signal_gate_met": signal_size_ok,
                "signal_diversity": signal_diversity,
                "calibration": {"documents": len(cal), "words": words(cal)},
                "validation": {"documents": len(val), "words": words(val)},
                "split_gate_met": split_ok,
                "evidence_gate_met": evidence_gate,
                "old_threshold": old,
                "candidate_threshold": round(cand, 4),
                "calibration_quantile": round(observed_q, 4) if observed_q is not None else None,
                "validation_alerts": {"old": len(old_alerts), "candidate": len(cand_alerts), "off": 0},
                "validation_alert_reduction_bootstrap": bootstrap_alert_reduction(old_flags, cand_flags, f"{signal}|{profile_name}"),
                "positive_control": {"old": positive_old, "candidate": positive_cand, "off": False},
                "adjudication": {"old": old_sum, "candidate": cand_sum, "removed_by_candidate": removed_sum},
                "candidate_decision": decision,
                "off_decision": off_decision,
            }
        sout["decision_status"] = "some_profiles_decidable" if decidable else "no_profile_decidable"
        result["signals"][signal] = sout

    pending_annotation = []
    for signal, signal_out in result["signals"].items():
        for profile_name, pout in signal_out["profiles"].items():
            if not pout.get("applicable"):
                continue
            if pout.get("candidate_decision") == "candidate_blocked_needs_removed_alert_adjudication" or pout.get("off_decision") == "off_blocked_needs_alert_adjudication":
                pending_annotation.append({"signal": signal, "profile": profile_name})
    evidence_ready = all(profile_ready.values()) and bool(all_applicable_evidence_gates) and all(all_applicable_evidence_gates)
    result["global"] = {
        "all_profile_gates_met": all(profile_ready.values()),
        "all_applicable_signal_evidence_gates_met": bool(all_applicable_evidence_gates) and all(all_applicable_evidence_gates),
        "ready_for_decision_evaluation": evidence_ready,
        "natural_alert_adjudication_pending": pending_annotation,
        "natural_alert_adjudication_complete_where_required": evidence_ready and not pending_annotation,
        "automatic_policy_update_allowed": False,
        "note": "Even supported candidates/off require explicit review; this script never edits editorial-baseline.json."
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.annotation_template:
        args.annotation_template.parent.mkdir(parents=True, exist_ok=True)
        fields = ["document_id","signal","profile","source_id","channel","old_fires","candidate_fires","removed_by_candidate","label","notes"]
        unique = {}
        for row in annotation_template_rows:
            unique[(row["document_id"], row["signal"])] = row
        with args.annotation_template.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(unique[k] for k in sorted(unique))
        result["annotation_template"] = str(args.annotation_template)
        # Re-write so output records the template location as provenance.
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"documents={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
